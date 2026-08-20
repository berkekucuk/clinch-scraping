import logging
from itemadapter import ItemAdapter
from .services.supabase_manager import SupabaseManager

class DatabasePipeline:

    def __init__(self):
        self.supabase = SupabaseManager()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Unified DatabasePipeline initialized.")

        self.event_buffer = {}
        self.fight_buffer = {}
        self.fighter_buffer = {}
        self.fighter_update_buffer = {}
        self.participation_buffer = {}
        self.ranking_buffer = {}


    async def process_item(self, item):
        adapter = ItemAdapter(item)
        item_type = adapter.get("item_type")

        if not item_type:
            return item

        item_data = adapter.asdict()
        item_data.pop("item_type", None)

        if item_type == "event":
            event_id = item_data.get("event_id")
            if event_id:
                self.event_buffer[event_id] = item_data

        elif item_type == "fight":
            fight_id = item_data.get("fight_id")
            if fight_id:
                self.fight_buffer[fight_id] = item_data

        elif item_type == "fighter":
            fighter_id = item_data.get("fighter_id")
            if fighter_id:
                # Filter out None values to prevent overwriting existing rich biography details in DB
                self.fighter_buffer[fighter_id] = {k: v for k, v in item_data.items() if v is not None}

        elif item_type == "fighter_update":
            fighter_id = item_data.get("fighter_id")
            if fighter_id:
                # Filter out None values to prevent overwriting existing rich biography details in DB
                self.fighter_update_buffer[fighter_id] = {k: v for k, v in item_data.items() if v is not None}

        elif item_type == "participation":
            fight_id = item_data.get("fight_id")
            fighter_id = item_data.get("fighter_id")
            if fight_id and fighter_id:
                self.participation_buffer[(fight_id, fighter_id)] = item_data

        elif item_type == "ranking":
            key = (item_data.get("weight_class_id"), item_data.get("rank_number"))
            if key[0] and key[1] is not None:
                self.ranking_buffer[key] = item_data

        return item


    async def close_spider(self):
        self.logger.info(f"[BATCH START] Processing buffered items: "
                         f"{len(self.event_buffer)} events, "
                         f"{len(self.fight_buffer)} fights, "
                         f"{len(self.fighter_buffer)} basic fighters, "
                         f"{len(self.fighter_update_buffer)} fighter updates, "
                         f"{len(self.participation_buffer)} participations")

        await self._flush_all()


    async def _flush_all(self):
        if self.event_buffer:
            await self.supabase.bulk_upsert(
                "events",
                list(self.event_buffer.values())
            )
            self.event_buffer.clear()

        if self.fighter_buffer:
            self.logger.info(f"[FIGHTERS] Inserting {len(self.fighter_buffer)} new fighters (ON CONFLICT DO NOTHING).")
            await self.supabase.bulk_upsert(
                "fighters",
                list(self.fighter_buffer.values()),
                ignore_duplicates=True
            )
            self.fighter_buffer.clear()

        if self.fighter_update_buffer:
            self.logger.info(f"[FIGHTER UPDATES] Updating {len(self.fighter_update_buffer)} biography details (ON CONFLICT DO UPDATE).")
            await self.supabase.bulk_upsert(
                "fighters",
                list(self.fighter_update_buffer.values()),
                ignore_duplicates=False
            )
            self.fighter_update_buffer.clear()

        if self.fight_buffer:
            await self.supabase.bulk_upsert(
                "fights",
                list(self.fight_buffer.values())
            )
            self.fight_buffer.clear()

        if self.participation_buffer:
            await self.supabase.bulk_upsert(
                "participants",
                list(self.participation_buffer.values()),
                on_conflict="fight_id, fighter_id"
            )
            self.participation_buffer.clear()

        if self.ranking_buffer:
            await self.supabase.bulk_upsert(
                "rankings",
                list(self.ranking_buffer.values()),
                on_conflict="weight_class_id,rank_number"
            )
            self.ranking_buffer.clear()

        self.logger.info("[BATCH END] All items processed successfully.")
