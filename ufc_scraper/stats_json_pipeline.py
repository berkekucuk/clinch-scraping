import json
import logging
from itemadapter import ItemAdapter


class StatsJsonPipeline:
    """
    Pipeline to export FightStatItem and FightItem outputs to stats_output.json
    for testing and verification purposes.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.fights: list[dict] = []
        self.fight_stats: list[dict] = []
        self.spider_name: str | None = None

    def open_spider(self, spider=None):
        self.spider_name = spider.name if spider else "stats"
        self.fights.clear()
        self.fight_stats.clear()
        self.logger.info(f"[StatsJsonPipeline] Initialized pipeline for spider: {self.spider_name}")

    def process_item(self, item, spider=None):
        adapter = ItemAdapter(item)
        item_type = adapter.get("item_type")

        if item_type == "fight_stat":
            data = adapter.asdict()
            data.pop("item_type", None)
            self.fight_stats.append(data)

        elif item_type == "fight":
            data = adapter.asdict()
            data.pop("item_type", None)
            # Filter out None fields for clean JSON output
            self.fights.append({k: v for k, v in data.items() if v is not None})

        return item

    def close_spider(self, spider=None):
        output = {
            "fights": self.fights,
            "fight_stats": self.fight_stats
        }

        filename = "stats_output.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)

        self.logger.info(
            f"[StatsJsonPipeline] ({self.spider_name}) Saved {len(self.fights)} fights and "
            f"{len(self.fight_stats)} fight stats to {filename}"
        )
