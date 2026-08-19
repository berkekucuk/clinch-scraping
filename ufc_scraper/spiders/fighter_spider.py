import scrapy
from ..parsers.fighter_parser import parse_fighter_profile

class FighterSpider(scrapy.Spider):
    name = "fighter"
    allowed_domains = ["tapology.com"]

    def __init__(self, *args, **kwargs):
        super(FighterSpider, self).__init__(*args, **kwargs)
        self.fighter_id: str | None = kwargs.get('fighter_id')
        self.target_url: str | None = kwargs.get('profile_url')

    async def start(self):
        if self.target_url and self.fighter_id:
            self.logger.info(f"Starting scrape for Fighter ID: {self.fighter_id}")
            yield scrapy.Request(
                url=self.target_url,
                callback=parse_fighter_profile,
                cb_kwargs={"fighter_id": self.fighter_id},
                dont_filter=True
            )
        else:
            self.logger.error("Missing required arguments! Usage: scrapy crawl fighter -a profile_url=... -a fighter_id=...")
