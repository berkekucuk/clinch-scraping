import json
import logging
from itemadapter import ItemAdapter


class RankingJsonPipeline:
    """
    Pipeline to export RankingItem outputs to rankings_output.json
    for testing and verification purposes.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.rankings: list[dict] = []
        self.spider_name: str | None = None

    def open_spider(self, spider=None):
        self.spider_name = spider.name if spider else "ranking"
        self.rankings.clear()
        self.logger.info(f"[RankingJsonPipeline] Initialized pipeline for spider: {self.spider_name}")

    def process_item(self, item, spider=None):
        adapter = ItemAdapter(item)
        item_type = adapter.get("item_type")

        if item_type == "ranking":
            data = adapter.asdict()
            data.pop("item_type", None)
            self.rankings.append(data)

        return item

    def close_spider(self, spider=None):
        filename = "rankings_output.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.rankings, f, ensure_ascii=False, indent=2, default=str)

        self.logger.info(
            f"[RankingJsonPipeline] ({self.spider_name}) Saved {len(self.rankings)} rankings to {filename}"
        )
