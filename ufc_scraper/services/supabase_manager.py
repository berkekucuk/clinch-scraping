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
            self.logger.info("Supabase client initialized (Async)")
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


    def get_event_status(self, event_id: str) -> str:
        if not self.url or not self.key:
            self.logger.warning("Supabase credentials missing.")
            return "live"

        try:
            client = create_client(self.url, self.key)
            response = client.table("events") \
                .select("status") \
                .eq("event_id", event_id) \
                .limit(1) \
                .execute()

            if response.data:
                return response.data[0].get("status", "live").lower()
        except Exception as e:
            self.logger.error(f"Supabase status check failed: {e}")

        return "live"


    async def load_fighter_cache(self):
        fighter_cache = {}
        batch_size = 1000
        offset = 0

        try:
            self.logger.info("Loading fighter cache...")

            while True:
                response = await self.client.table('fighters')\
                    .select('fighter_id, name')\
                    .range(offset, offset + batch_size - 1)\
                    .execute()

                if not response.data:
                    break

                for f in response.data:
                    if f.get('name'):
                        fighter_cache[f['name'].strip()] = f['fighter_id']

                if len(response.data) < batch_size:
                    break

                offset += batch_size

            self.logger.info(f"Successfully loaded {len(fighter_cache)} fighters into cache.")
            return fighter_cache

        except Exception as e:
            self.logger.error(f"Failed to load fighter cache: {e}")
            return {}
