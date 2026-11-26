import scrapy
from twisted.python.failure import Failure
from ..services.supabase_manager import SupabaseManager
from ..parsers.ranking_parser import extract_ufc_slugs, parse_rankings


class RankingSpider(scrapy.Spider):
    name = "ranking"
    allowed_domains = ['ufc.com']

    def __init__(self, *args, **kwargs):
        super(RankingSpider, self).__init__(*args, **kwargs)
        self.supabase = SupabaseManager()

    async def start(self):
        yield scrapy.Request(
            url='https://www.ufc.com/rankings',
            callback=self.parse_rankings,
            errback=self.on_error,
            meta={"zyte_api_automap": False},
        )

    def on_error(self, failure: Failure) -> None:
        request = getattr(failure, "request", None)
        url = request.url if request else "unknown URL"
        self.logger.error(f"[RANKING SPIDER] Request failed for {url}: {failure.value!r}")

    async def parse_rankings(self, response):
        ufc_slugs = extract_ufc_slugs(response)
        fighter_ids = await self.supabase.get_fighter_ids_by_ufc_slugs(ufc_slugs)
        self.logger.info(f"[RANKING SPIDER] {len(fighter_ids)}/{len(ufc_slugs)} ranked fighters found by ufc_slug")

        for item in parse_rankings(response, fighter_ids):
            yield item
