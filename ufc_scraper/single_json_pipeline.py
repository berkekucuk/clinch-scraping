import json
import logging
from itemadapter import ItemAdapter


class SingleJsonPipeline:
    """
    Pipeline to export EventItem, FightItem, FighterItem, and ParticipantItem outputs
    to single_event_output.json for testing and verification purposes.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.events: list[dict] = []
        self.fights: list[dict] = []
        self.fighters: list[dict] = []
        self.participants: list[dict] = []
        self.spider_name: str | None = None

    def open_spider(self, spider=None):
        self.spider_name = spider.name if spider else "smart"
        self.events.clear()
        self.fights.clear()
        self.fighters.clear()
        self.participants.clear()
        self.logger.info(f"[SingleJsonPipeline] Initialized pipeline for spider: {self.spider_name}")

    def process_item(self, item, spider=None):
        adapter = ItemAdapter(item)
        item_type = adapter.get("item_type")

        if not item_type:
            return item

        data = adapter.asdict()
        data.pop("item_type", None)

        if item_type == "event":
            self.events.append(data)

        elif item_type == "fight":
            # Filter out None fields for clean JSON output
            self.fights.append({k: v for k, v in data.items() if v is not None})

        elif item_type == "fighter":
            # Filter out None fields for clean JSON output
            self.fighters.append({k: v for k, v in data.items() if v is not None})

        elif item_type == "participation":
            self.participants.append(data)

        return item

    def close_spider(self, spider=None):
        output = {
            "events": self.events,
            "fights": self.fights,
            "fighters": self.fighters,
            "participants": self.participants
        }

        filename = "single_event_output.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)

        self.logger.info(
            f"[SingleJsonPipeline] ({self.spider_name}) Saved {len(self.events)} events, "
            f"{len(self.fights)} fights, {len(self.fighters)} fighters, and "
            f"{len(self.participants)} participants to {filename}"
        )
