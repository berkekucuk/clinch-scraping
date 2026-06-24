import scrapy
from ..services.supabase_manager import SupabaseManager
from ..utils.ranking_mappings import WEIGHT_CLASS_MAPPING, NAME_EXCEPTIONS

class RankingSpider(scrapy.Spider):
    name = "ranking"
    allowed_domains = ['ufc.com']

    def __init__(self, *args, **kwargs):
        super(RankingSpider, self).__init__(*args, **kwargs)
        self.supabase = SupabaseManager()
        self.fighter_cache = {}


    async def start(self):
        self.fighter_cache = await self.supabase.load_fighter_cache()

        if not self.fighter_cache:
            self.logger.error("⚠️ Fighter Cache is empty! Rankings might not link correctly.")

        yield scrapy.Request(url='https://www.ufc.com/rankings', callback=self.parse)


    async def parse(self, response):
        groupings = response.css('.block-views-blockathlete-rankings-block-1 .view-grouping')

        for group in groupings:
            raw_title = group.css('.view-grouping-header::text').get()
            if not raw_title:
                continue

            title = raw_title.strip()
            db_weight_class_id = WEIGHT_CLASS_MAPPING.get(title)

            if not db_weight_class_id:
                self.logger.warning(f"Weight class not matched: {title}")
                continue

            champion_name = group.css('.info h5 a::text').get()
            if champion_name:
                item = self.process_fighter(champion_name, db_weight_class_id, 0, 0)
                if item:
                    yield item

            rows = group.css('tbody tr')
            current_rank = 1

            for row in rows:
                fighter_name = row.css('.views-field-title a::text').get()
                
                rank_change = 0
                rank_change_td = row.css('.views-field-weight-class-rank-change')
                if rank_change_td:
                    change_texts = rank_change_td.xpath('./text()').getall()
                    change_text = "".join(change_texts).strip().replace('"', '')
                    change_span_class = rank_change_td.css('span::attr(class)').get()

                    if change_span_class and 'not-ranked' in change_span_class:
                        rank_change = None
                    elif change_text and change_span_class:
                        try:
                            change_val = int(change_text)
                            if 'increase' in change_span_class:
                                rank_change = change_val
                            elif 'decrease' in change_span_class:
                                rank_change = -change_val
                        except ValueError:
                            pass

                if fighter_name:
                    item = self.process_fighter(fighter_name, db_weight_class_id, current_rank, rank_change)
                    if item:
                        yield item
                    current_rank += 1


    def process_fighter(self, fighter_name, weight_class_id, rank, rank_change=0):
        if rank == 0 and weight_class_id in ["mens_p4p", "womens_p4p"]:
            return False

        fighter_name = fighter_name.strip()

        search_name = NAME_EXCEPTIONS.get(fighter_name, fighter_name)
        found_id = self.fighter_cache.get(search_name)

        if found_id:
            return {
                "item_type": "ranking",
                "weight_class_id": weight_class_id,
                "fighter_id": found_id,
                "rank_number": rank,
                "rank_change": rank_change,
            }
        else:
            self.logger.warning(f"Fighter not found in DB: {fighter_name}")
            return None
