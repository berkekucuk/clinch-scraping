import logging

from .cancelled_fight_parser import CancelledFightParser
from ..utils.item_factory import ItemFactory
from ..utils.odds_parser import OddsParser
from ..utils.fighter_div_parser import FighterDivParser
from ..utils.url_parser import UrlParser
from ..utils.method_parser import MethodParser
from ..utils.datetime_parser import DatetimeParser
from ..utils.status_parser import StatusParser
from ..utils.weight_class_mapper import WeightClassMapper
from ..utils.round_parser import RoundParser


logger = logging.getLogger(__name__)


class EventPageParser:

    @staticmethod
    def parse_card(response, event_id, event_url, is_live_mode=False):

        logger.info(f"Parsing event: {event_id}")

        status_string = response.css("div#eventPageHeader span::text").get(default="").strip()
        status = StatusParser.parse(status_string)

        name = response.css("h2::text").get(default="").strip() or None

        container = response.css('ul[data-controller="unordered-list-background"]')

        date_time_str = container.xpath(".//span[contains(text(), 'Date/Time')]/following-sibling::span/text()").get(default="").strip()
        datetime_utc = DatetimeParser.parse(date_time_str)
        venue = container.xpath(".//span[contains(text(), 'Venue')]/following-sibling::span/text()").get(default="").strip() or None
        location = container.xpath(".//span[contains(text(), 'Location')]/following-sibling::span//text()").get(default="").strip() or None

        if not is_live_mode:
            yield ItemFactory.create_event_item(
                event_id,
                event_url,
                name,
                status,
                datetime_utc,
                venue,
                location,
            )

        fights = response.css('ul[data-event-view-toggle-target="list"] > li[data-controller="table-row-background"]')
        cancelled_fights = response.xpath('//div[starts-with(@id, "bout") and contains(@id, "Cancelled")]')
        total_fights = len(fights)

        for index, fight in enumerate(fights, start=1):
            fight_order_number = total_fights - index + 1
            yield from EventPageParser.parse_single_fight(fight, response, event_id, fight_order_number, is_live_mode)

        if not is_live_mode:
            for cancelled_fight in cancelled_fights:
                yield from CancelledFightParser.parse_cancelled_fight(cancelled_fight, response, event_id)

    @staticmethod
    def parse_single_fight(fight, response, event_id, auto_index, is_live_mode=False):
        web_view = fight.xpath("./div[1]")

        ### Fight summary ###
        fight_summary_div = web_view.xpath(".//div[contains(@class, 'flex w-full mt-1 mb-0.5 px-1.5')]")
        method_str = fight_summary_div.css("span.uppercase::text").get(default="").strip() or None
        method_parsed = MethodParser.split_method(method_str)
        round_summary_str = fight_summary_div.css(r"span.text-xs11.md\:text-xs10.leading-relaxed::text").get(default="").strip() or None
        round_summary = RoundParser.standardize_round_summary(round_summary_str)

        fight_summary = {
            "method_type": method_parsed["method_type"],
            "method_detail": method_parsed["method_detail"],
            "round_summary": round_summary,
        }

        ### Fighter infos ###
        fight_participants_div = web_view.xpath("./div[@class='div group flex items:start justify-center gap-0.5 md:gap-0']")
        fighter1_div = fight_participants_div.xpath("./div[1]")
        fighter2_div = fight_participants_div.xpath("./div[3]")

        fighter1_data = FighterDivParser.parse_fighter_div(fighter1_div, response, is_first_fighter=True)
        fighter2_data = FighterDivParser.parse_fighter_div(fighter2_div, response, is_first_fighter=False)

        ### Fight metadata ###
        middle_div = fight_participants_div.xpath("./div[2]")
        box_div = middle_div.xpath("./div[1]")
        bout_details_button_div = middle_div.xpath("./div[2]")

        fight_relative_url = box_div.xpath("./span[1]/a/@href").get(default="").strip() or None
        fight_id = UrlParser.extract_fight_id(fight_relative_url)
        if not fight_id:
            logger.error(f"Could not extract fight_id from URL: {fight_relative_url}")
            return

        bout_type = box_div.xpath("./span[1]/a/text()").get(default="").strip() or None
        if bout_type == "* Rumor *":
            bout_type = "Main Card"
        weight_class_lbs = box_div.xpath("./div[1]/span/text()").get(default="").strip() or None
        weight_class_id = WeightClassMapper.map_weight_class(weight_class_lbs)
        rounds_format = box_div.xpath("./div[2]/text()").get(default="").strip() or None
        fight_order = bout_details_button_div.xpath(".//span[2]/text()").get(default="").strip() or str(auto_index)

        fight_metadata = {
            "fight_id": fight_id,
            "bout_type": bout_type,
            "weight_class_lbs": weight_class_lbs,
            "weight_class_id": weight_class_id,
            "rounds_format": rounds_format,
            "fight_order": fight_order,
        }

        ### Odds and ages data ###
        bout_details_div = web_view.xpath("./div[@data-event-bout-details-target='content']")
        odds_data = OddsParser.parse_odds(bout_details_div)

        ### yield items ###
        yield ItemFactory.create_fight_item(
            fight_metadata,
            event_id,
            fight_summary,
        )

        if not is_live_mode:
            for fighter_item in ItemFactory.create_fighter_items(fighter1_data, fighter2_data):
                yield fighter_item

        for participation_item in ItemFactory.create_participation_items(
            fight_metadata["fight_id"],
            fighter1_data,
            fighter2_data,
            odds_data,
        ):
            yield participation_item
