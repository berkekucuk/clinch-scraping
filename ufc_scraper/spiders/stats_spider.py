import scrapy
from ..services.supabase_manager import SupabaseManager
from ..parsers.fight_stats_parser import parse_live_fight_details


class StatsSpider(scrapy.Spider):
    name = "stats"
    allowed_domains = ["ufcstats.com"]

    def __init__(self, *args, **kwargs):
        super(StatsSpider, self).__init__(*args, **kwargs)
        self.supabase = SupabaseManager()
        self.mode = kwargs.get("mode", "live")
        self.event_id: str | None = kwargs.get("event_id")

    async def start(self):
        if self.mode == "live":
            if not self.event_id:
                self.logger.error("[STATS SPIDER] event_id parameter is required for live mode. Usage: -a mode=live -a event_id=...")
                return

            window_fights = await self.supabase.get_live_sliding_fights(self.event_id, window_size=3)
            if not window_fights:
                self.logger.warning(f"[STATS SPIDER] No active sliding fights found for event_id: {self.event_id}")
                return

            self.logger.info(f"[STATS SPIDER] Scraping {len(window_fights)} live fights for event_id: {self.event_id}")

            for fight in window_fights:
                fight_id = fight.get("fight_id")
                ufcstats_id = fight.get("ufcstats_id")

                if not fight_id or not ufcstats_id:
                    continue

                fight_url = f"http://ufcstats.com/fight-details/{ufcstats_id}"

                yield scrapy.Request(
                    url=fight_url,
                    callback=parse_live_fight_details,
                    meta={"zyte_api": False},
                    cb_kwargs={
                        "fight_id": fight_id,
                        "ufcstats_fight_id": ufcstats_id,
                        "supabase_fight": fight
                    }
                )

        elif self.mode == "event":
            if not self.event_id:
                self.logger.error("[STATS SPIDER] event_id parameter is required for event mode. Usage: -a mode=event -a event_id=...")
                return

            fights = await self.supabase.get_event_fights_with_participants(self.event_id)
            if not fights:
                self.logger.warning(f"[STATS SPIDER] No valid fights with ufcstats_id found in DB for event_id: {self.event_id}")
                return

            self.logger.info(f"[STATS SPIDER] Scraping {len(fights)} fights for event_id: {self.event_id}")

            for fight in fights:
                fight_id = fight.get("fight_id")
                ufcstats_id = fight.get("ufcstats_id")

                if not fight_id or not ufcstats_id:
                    continue

                fight_url = f"http://ufcstats.com/fight-details/{ufcstats_id}"
                yield scrapy.Request(
                    url=fight_url,
                    callback=parse_live_fight_details,
                    meta={"zyte_api": False},
                    cb_kwargs={
                        "fight_id": fight_id,
                        "ufcstats_fight_id": ufcstats_id,
                        "supabase_fight": fight
                    }
                )

        else:
            self.logger.error(f"[STATS SPIDER] Unsupported mode: {self.mode}. Supported modes: 'live', 'event'")
