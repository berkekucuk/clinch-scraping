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
        self.participation_buffer = {}

        self.has_fighter_updates = False


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
                self.fighter_buffer[fighter_id] = item_data

        elif item_type == "fighter_update":
            fighter_id = item_data.get("fighter_id")
            if fighter_id:
                self.fighter_buffer[fighter_id] = item_data
                self.has_fighter_updates = True

        elif item_type == "participation":
            fight_id = item_data.get("fight_id")
            fighter_id = item_data.get("fighter_id")
            if fight_id and fighter_id:
                self.participation_buffer[(fight_id, fighter_id)] = item_data

        return item


    async def close_spider(self):
        self.logger.info(f"[BATCH START] Processing buffered items: "
                         f"{len(self.event_buffer)} events, "
                         f"{len(self.fight_buffer)} fights, "
                         f"{len(self.fighter_buffer)} fighters, "
                         f"{len(self.participation_buffer)} participations")

        await self._flush_all()


    async def _flush_all(self):
        if self.event_buffer:
            await self.supabase.bulk_upsert("events", list(self.event_buffer.values()))
            self.event_buffer.clear()

        if self.fighter_buffer:
            should_ignore_duplicates = not self.has_fighter_updates
            mode_msg = "INSERT ONLY" if should_ignore_duplicates else "UPDATE"
            self.logger.info(f"[FIGHTERS] Processing {len(self.fighter_buffer)} fighters in {mode_msg} mode.")
            await self.supabase.bulk_upsert(
                "fighters",
                list(self.fighter_buffer.values()),
                ignore_duplicates=should_ignore_duplicates
            )
            self.fighter_buffer.clear()
            self.has_fighter_updates = False

        if self.fight_buffer:
            await self.supabase.bulk_upsert("fights", list(self.fight_buffer.values()))
            self.fight_buffer.clear()

        if self.participation_buffer:
            await self.supabase.bulk_upsert(
                "participants",
                list(self.participation_buffer.values()),
                on_conflict="fight_id, fighter_id"
            )
            self.participation_buffer.clear()

        self.logger.info("[BATCH END] All items processed successfully.")
