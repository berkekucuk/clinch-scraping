import os
from urllib.parse import urlencode, urljoin

import scrapy
from ..utils.date_parser import DateParser
from ..utils.record_parser import RecordParser
from ..utils.url_parser import UrlParser
from ..utils.measurement_parser import MeasurementParser
from ..utils.weight_class_mapper import WeightClassMapper
from ..items import FighterItem

class FighterSpider(scrapy.Spider):
    name = "fighter"
    allowed_domains = ["tapology.com", "api.scraperapi.com"]

    SCRAPER_API_KEY = os.getenv('SCRAPER_API_KEY')

    def __init__(self, *args, **kwargs):
        super(FighterSpider, self).__init__(*args, **kwargs)
        self.fighter_id = kwargs.get('fighter_id')
        self.target_url = kwargs.get('profile_url')


    def get_scraperapi_url(self, target_url):
        if not self.SCRAPER_API_KEY:
            self.logger.error("API key for ScraperAPI not found! Please set the SCRAPER_API_KEY environment variable.")
            return target_url

        payload = {'api_key': self.SCRAPER_API_KEY, 'url': target_url}
        return 'https://api.scraperapi.com/?' + urlencode(payload)


    async def start(self):
        if self.target_url and self.fighter_id:
            self.logger.info(f"Starting scrape for Fighter ID: {self.fighter_id}")
            yield scrapy.Request(
                url=self.get_scraperapi_url(self.target_url),
                callback=self.parse,
                dont_filter=True
            )
        else:
            self.logger.error("Missing required arguments! Usage: scrapy crawl fighter -a url=... -a fighter_id=...")

    async def parse(self, response):
        header = response.css("div#fighterPageHeader")
        container = response.css("div#standardDetails")

        nickname = self._extract_detail(container, "Nickname:")

        record_str = self._extract_detail(container, "Pro MMA Record:")
        record = RecordParser.parse(record_str)

        date_of_birth_str = self._extract_detail(container, "Date of Birth:")
        date_of_birth = DateParser.parse_date_to_iso(date_of_birth_str)

        height_str = self._extract_detail(container, "Height:")
        height = MeasurementParser.parse_measurement(height_str)

        reach_str = self._extract_reach(container)
        reach = MeasurementParser.parse_measurement(reach_str)

        weight_class_name = self._extract_detail(container, "Weight Class:")
        weight_class_id = WeightClassMapper.map_weight_class(weight_class_name)

        born = self._extract_detail(container, "Born:")
        fighting_out_of = self._extract_detail(container, "Fighting out of:")
        style = self._extract_detail(container, "Foundation Style:")

        country_flag_relative_url = header.css("img::attr(src)").get(default="").strip() or None
        country_flag_url = urljoin("https://www.tapology.com", country_flag_relative_url) if country_flag_relative_url else None
        country_code = UrlParser.extract_country_code(country_flag_url) if country_flag_url else None

        fighter_item = FighterItem()
        fighter_item['item_type'] = "fighter_update"
        fighter_item['fighter_id'] = self.fighter_id
        fighter_item['nickname'] = nickname
        fighter_item['record'] = record
        fighter_item['date_of_birth'] = date_of_birth
        fighter_item['height'] = height
        fighter_item['reach'] = reach
        fighter_item['weight_class_id'] = weight_class_id
        fighter_item['born'] = born
        fighter_item['fighting_out_of'] = fighting_out_of
        fighter_item['style'] = style
        fighter_item['country_code'] = country_code
        yield fighter_item

    def _extract_detail(self, container, label):
        val = container.xpath(f'.//strong[contains(text(), "{label}")]/following-sibling::span[1]/text()').get(default="").strip()
        return val if (val and val != 'N/A') else None

    def _extract_reach(self, container):
        val = container.xpath('.//strong[contains(text(), "Reach")]/ancestor::div/following-sibling::div[1]/span/text()').get(default="").strip()
        return val if val else None
