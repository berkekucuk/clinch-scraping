import json
import logging
from itemadapter import ItemAdapter


class OddsJsonPipeline:
    """
    Pipeline to export FightOddsItem outputs to odds_output.json, grouped by fight,
    for testing and verification purposes.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.fights: dict[str, dict] = {}
        self.spider_name: str | None = None

    def open_spider(self, spider=None):
        self.spider_name = spider.name if spider else "odds"
        self.fights.clear()
        self.logger.info(f"[OddsJsonPipeline] Initialized pipeline for spider: {self.spider_name}")

    def process_item(self, item, spider=None):
        adapter = ItemAdapter(item)

        if adapter.get("item_type") == "fight_odds":
            data = adapter.asdict()
            fight = self.fights.setdefault(data["fight_id"], {"fight_id": data["fight_id"], "odds": []})
            fight["odds"].append({
                key: data[key]
                for key in ("fighter_id", "method", "round", "odds_value", "sportsbook")
            })

        return item

    def close_spider(self, spider=None):
        filename = "odds_output.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(list(self.fights.values()), f, ensure_ascii=False, indent=2, default=str)

        odds_count = sum(len(fight["odds"]) for fight in self.fights.values())
        self.logger.info(
            f"[OddsJsonPipeline] ({self.spider_name}) Saved {odds_count} odds for {len(self.fights)} fights to {filename}"
        )
