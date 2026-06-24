import json
import logging
from itemadapter import ItemAdapter


class RankingJsonPipeline:

    def open_spider(self, spider):
        if spider.name != "ranking":
            return
        self.items = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def process_item(self, item, spider):
        if spider.name != "ranking":
            return item
        adapter = ItemAdapter(item)
        if adapter.get("item_type") == "ranking":
            data = adapter.asdict()
            data.pop("item_type", None)
            self.items.append(data)
        return item

    def close_spider(self, spider):
        if spider.name != "ranking":
            return
        with open("rankings_output.json", "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2, default=str)
        self.logger.info(f"[RankingJsonPipeline] Wrote {len(self.items)} rankings to rankings_output.json")
