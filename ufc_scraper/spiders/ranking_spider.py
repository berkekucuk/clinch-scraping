import os
import logging
from datetime import datetime
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
        self.rankings_buffer = []
        self._setup_file_logger()


    def _setup_file_logger(self):
        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(logs_dir, f"ranking_errors_{timestamp}.txt")

        self.file_logger = logging.getLogger(f"ranking_file_logger_{timestamp}")
        self.file_logger.setLevel(logging.WARNING)
        self.file_logger.handlers.clear()

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        self.file_logger.addHandler(file_handler)
        self.log_file_path = log_file


    async def start(self):
        self.fighter_cache = await self.supabase.load_fighter_cache()

        if not self.fighter_cache:
            self.logger.error("⚠️ Fighter Cache is empty! Rankings might not link correctly.")

        yield scrapy.Request(url='https://www.ufc.com/rankings', callback=self.parse)


    async def parse(self, response):
        groupings = response.css('.view-grouping')

        for group in groupings:
            raw_title = group.css('.view-grouping-header::text').get()
            if not raw_title:
                continue

            title = raw_title.strip()
            db_weight_class_id = WEIGHT_CLASS_MAPPING.get(title)

            if not db_weight_class_id:
                self.file_logger.warning(f"Weight class not matched: {title}")
                continue

            champion_name = group.css('.info h5 a::text').get()
            if champion_name:
                self.process_fighter(champion_name, db_weight_class_id, 0)

            rows = group.css('tbody tr')
            current_rank = 1

            for row in rows:
                fighter_name = row.css('.views-field-title a::text').get()

                if fighter_name:
                    self.process_fighter(fighter_name, db_weight_class_id, current_rank)
                    current_rank += 1

        if self.rankings_buffer:
            await self.supabase.bulk_upsert(
                "rankings",
                self.rankings_buffer,
                on_conflict="weight_class_id,rank_number"
            )


    def process_fighter(self, fighter_name, weight_class_id, rank):
        if rank == 0 and weight_class_id in ["mens_p4p", "womens_p4p"]:
            return False

        fighter_name = fighter_name.strip()

        search_name = NAME_EXCEPTIONS.get(fighter_name, fighter_name)
        found_id = self.fighter_cache.get(search_name)

        if found_id:
            data = {
                "weight_class_id": weight_class_id,
                "fighter_id": found_id,
                "rank_number": rank,
            }
            self.rankings_buffer.append(data)
            return True
        else:
            self.file_logger.warning(f"Fighter not found in DB: {fighter_name}")
            return False
