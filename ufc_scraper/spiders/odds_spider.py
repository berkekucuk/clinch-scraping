import scrapy
from twisted.python.failure import Failure
from ..services.supabase_manager import SupabaseManager
from ..parsers.bfo_odds_parser import parse_event_odds


class OddsSpider(scrapy.Spider):
    name = "odds"
    allowed_domains = ["bestfightodds.com"]

    def __init__(self, *args, **kwargs):
        super(OddsSpider, self).__init__(*args, **kwargs)
        self.supabase = SupabaseManager()

    async def start(self):
        event = await self.supabase.get_next_event()
        if not event:
            self.logger.warning("[ODDS SPIDER] No upcoming event found")
            return

        self.logger.info(f"[ODDS SPIDER] Scraping odds for next event: {event['event_id']}")
        yield scrapy.Request(
            url="https://www.bestfightodds.com/",
            callback=parse_event_odds,
            errback=self.on_error,
            meta={"zyte_api_automap": False},
            cb_kwargs={"event": event},
        )

    def on_error(self, failure: Failure) -> None:
        request = getattr(failure, "request", None)
        url = request.url if request else "unknown URL"
        self.logger.error(f"[ODDS SPIDER] Request failed for {url}: {failure.value!r}")
