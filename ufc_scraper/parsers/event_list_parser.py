import logging
from urllib.parse import urljoin
from ..utils.url_parser import extract_event_id

logger = logging.getLogger(__name__)


def parse_events_from_list(response):
    events = response.css('div[data-controller="bout-toggler"]')
    logger.info(f"Found {len(events)} events on page {response.url}")

    event_data_list = []
    for event in events:
        event_relative_url = event.css("div.promotion a::attr(href)").get(default="")
        if not event_relative_url:
            continue

        event_name = event.css("div.promotion a::text").get(default="").strip()

        if event_name.startswith("Road to UFC"):
            logger.info(f"Skipping Road to UFC event: {event_name}")
            continue

        event_url = urljoin("https://www.tapology.com", event_relative_url)
        event_id = extract_event_id(event_relative_url)

        if not event_id:
            logger.error(f"Could not extract event_id from: {event_relative_url}")
            continue

        event_data_list.append({"event_id": event_id, "event_url": event_url})

    return event_data_list
