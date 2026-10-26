import os
import logging
from supabase import AsyncClient, create_client
from dotenv import load_dotenv

load_dotenv()

class SupabaseManager:

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.url = os.getenv("SUPABASE_PROD_URL")
        self.key = os.getenv("SUPABASE_PROD_KEY")

        if not all([self.url, self.key]):
            self.logger.error("Supabase credentials are missing in .env")
            raise ValueError("Missing Supabase credentials")

        try:
            self.client = AsyncClient(self.url, self.key)
            self.sync_client = create_client(self.url, self.key)
            self.logger.info("Supabase clients initialized (Async + Sync)")

        except Exception as e:
            self.logger.error(f"Failed to initialize Supabase client: {e}")
            raise e


    async def bulk_upsert(self, table_name: str, data: list, ignore_duplicates=False, on_conflict=None):
        if not data:
            return None

        try:
            response = await self.client.table(table_name).upsert(
                data,
                ignore_duplicates=ignore_duplicates,
                on_conflict=on_conflict
            ).execute()

            self.logger.debug(f"[{table_name.upper()}] Successfully upserted {len(data)} rows.")
            return response

        except Exception as e:
            self.logger.error(f"Error in bulk upsert for table '{table_name}': {e}")
            raise e


    async def get_events_by_ids(self, event_ids: list):
        if not event_ids:
            return {}

        try:
            response = await self.client.table("events")\
                .select("*")\
                .in_("event_id", event_ids)\
                .execute()

            events_dict = {event["event_id"]: event for event in response.data}

            self.logger.info(f"Fetched {len(events_dict)} events from {len(event_ids)} requested IDs")
            return events_dict

        except Exception as e:
            self.logger.error(f"Failed to get events: {e}")
            raise e


    async def get_upcoming_events(self, limit: int = 4):
        try:
            response = await self.client.table("events")\
                .select("event_id, event_url, updated_at")\
                .eq("status", "Upcoming")\
                .order("updated_at", nullsfirst=True)\
                .limit(limit)\
                .execute()
            
            self.logger.info(f"Fetched {len(response.data)} upcoming events from DB")
            return response.data

        except Exception as e:
            self.logger.error(f"Failed to get upcoming events: {e}")
            return []


    def has_unfinished_fights(self, event_id: str) -> bool:
        try:
            response = self.sync_client.rpc("has_unfinished_fights", {"p_event_id": event_id}).execute()
            return response.data is not False

        except Exception as e:
            self.logger.error(f"Supabase unfinished fights check failed: {e}")
            return True


    def mark_event_completed(self, event_id: str) -> bool:
        try:
            response = self.sync_client.table("events") \
                .update({"status": "Completed"}) \
                .eq("event_id", event_id) \
                .execute()

            if not response.data:
                self.logger.error(f"No event row updated for {event_id}.")
                return False

            self.logger.info(f"Marked event {event_id} as Completed.")
            return True

        except Exception as e:
            self.logger.error(f"Failed to mark event {event_id} as Completed: {e}")
            return False


    async def load_fighter_cache(self):
        fighter_cache = {}

        try:
            self.logger.info("Loading fighter cache...")

            response = await self.client.table('fighters')\
                .select('fighter_id, name')\
                .execute()

            for f in response.data:
                if f.get('name'):
                    fighter_cache[f['name'].strip()] = f['fighter_id']

            self.logger.info(f"Successfully loaded {len(fighter_cache)} fighters into cache.")
            return fighter_cache

        except Exception as e:
            self.logger.error(f"Failed to load fighter cache: {e}")
            return {}


    async def get_live_sliding_fights(self, event_id: str, window_size: int = 3) -> list[dict]:
        try:
            response = await self.client.rpc(
                "get_live_sliding_fights",
                {"p_event_id": event_id, "p_window_size": window_size}
            ).execute()
            return response.data or []

        except Exception as e:
            self.logger.error(f"[LIVE RPC] Failed to get sliding fights for event {event_id}: {e}")
            return []


    async def get_event_fights_with_participants(self, event_id: str) -> list[dict]:
        try:
            res = await self.client.table("fights")\
                .select("fight_id, fight_order, ufcstats_id, participants(fighter_id, fighters(name, ufcstats_id))")\
                .eq("event_id", event_id)\
                .not_.is_("ufcstats_id", "null")\
                .not_.in_("bout_type", ["cancelled", "fizzled", "Cancelled", "Fizzled"])\
                .order("fight_order", desc=False)\
                .execute()
            return res.data or []

        except Exception as e:
            self.logger.error(f"Failed to get fights for event {event_id}: {e}")
            return []


    def recalculate_event_fighters_stats(self, event_id: str) -> None:
        try:
            self.sync_client.rpc("recalculate_event_fighters_stats", {"p_event_id": event_id}).execute()
            self.logger.info(f"Successfully recalculated career stats for all fighters in event: {event_id}")

        except Exception as e:
            self.logger.error(f"Failed to recalculate career stats for event {event_id}: {e}")
