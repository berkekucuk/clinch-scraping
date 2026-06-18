import scrapy
from urllib.parse import urljoin
from ..utils.url_parser import UrlParser
from ..services.supabase_manager import SupabaseManager
from ..parsers.event_page_parser import EventPageParser

class SmartSpider(scrapy.Spider):
    name = "smart"
    allowed_domains = ["tapology.com"]

    def __init__(self, *args, **kwargs):
        super(SmartSpider, self).__init__(*args, **kwargs)
        self.supabase = SupabaseManager()
        self.mode = kwargs.get('mode', 'upcoming')
        self.event_url = kwargs.get('event_url')

    async def start(self):
        if self.mode == 'single':
            if not self.event_url:
                self.logger.error("[SINGLE MODE] event_url parameter is required. Usage: -a mode=single -a event_url=...")
                return

            event_id = UrlParser.extract_event_id(self.event_url)
            if not event_id:
                self.logger.error(f"[SINGLE MODE] Could not extract event_id from URL: {self.event_url}")
                return

            self.logger.info(f"[SINGLE MODE] Scraping single event: {event_id}")
            yield scrapy.Request(
                url=self.event_url,
                callback=EventPageParser.parse_card,
                cb_kwargs={"event_id": event_id, "event_url": self.event_url, "is_live_mode": True},
            )

        else:
            self.logger.info("[UPCOMING MODE] Starting event pagination scrape...")
            url = "https://www.tapology.com/fightcenter/promotions/1-ultimate-fighting-championship-ufc?page=1"
            yield scrapy.Request(
                url=url,
                callback=self.parse_upcoming_events
            )

    async def parse_upcoming_events(self, response):
        events = response.css('div[data-controller="bout-toggler"]')
        self.logger.info(f"Found {len(events)} events on page {response.url}")

        event_data_list = []
        for event in events:
            event_relative_url = event.css("div.promotion a::attr(href)").get(default="")
            if not event_relative_url:
                continue

            event_name = event.css("div.promotion a::text").get(default="").strip()

            if event_name.startswith("Road to UFC"):
                self.logger.info(f"Skipping Road to UFC event: {event_name}")
                continue

            event_url = urljoin("https://www.tapology.com", event_relative_url)
            event_id = UrlParser.extract_event_id(event_relative_url)

            if not event_id:
                self.logger.error(f"Could not extract event_id from: {event_relative_url}")
                continue

            event_data_list.append({"event_id": event_id, "event_url": event_url})

        if event_data_list:
            event_ids = [item["event_id"] for item in event_data_list]
            existing_events = await self.supabase.get_events_by_ids(event_ids)

            new_events = []
            upcoming_events = []

            for event_data in event_data_list:
                event_id = event_data["event_id"]
                event_url = event_data["event_url"]

                existing_event = existing_events.get(event_id)

                if not existing_event:
                    new_events.append((event_id, event_url))
                elif existing_event.get("status") == "Upcoming":
                    updated_at = existing_event.get("updated_at")
                    upcoming_events.append((event_id, event_url, updated_at))
                else:
                    self.logger.debug(f"Event {event_id} is already completed. Skipping.")

            max_pages = 4
            selected_events = []

            for event_id, event_url in new_events:
                if len(selected_events) < max_pages:
                    self.logger.info(f"Event {event_id} is NEW. Prioritizing full page scrape.")
                    selected_events.append((event_id, event_url))
                else:
                    self.logger.debug(f"Event {event_id} is NEW but skipped due to quota limit.")

            remaining_quota = max_pages - len(selected_events)

            if remaining_quota > 0 and upcoming_events:
                upcoming_events.sort(key=lambda x: x[2] if x[2] else "")
                
                for event_id, event_url, _ in upcoming_events[:remaining_quota]:
                    self.logger.info(f"Event {event_id} is UPCOMING (Oldest). Scheduling full page scrape.")
                    selected_events.append((event_id, event_url))
                
                for event_id, event_url, _ in upcoming_events[remaining_quota:]:
                    self.logger.debug(f"Event {event_id} is UPCOMING but skipped due to quota limit.")
            else:
                for event_id, event_url, _ in upcoming_events:
                    self.logger.debug(f"Event {event_id} is UPCOMING but skipped due to quota limit.")

            for event_id, event_url in selected_events:
                yield scrapy.Request(
                    url=event_url,
                    callback=EventPageParser.parse_card,
                    cb_kwargs={"event_id": event_id, "event_url": event_url},
                )
