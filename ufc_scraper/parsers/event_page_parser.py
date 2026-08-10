import logging
from .cancelled_fight_parser import parse_cancelled_fight
from ..items import EventItem, FightItem, FighterItem, ParticipantItem
from ..utils.odds_parser import parse_odds
from ..utils.fighter_div_parser import parse_fighter_div
from ..utils.url_parser import extract_fight_id
from ..utils.method_parser import split_method
from ..utils.datetime_parser import parse_datetime
from ..utils.weight_class_mapper import map_weight_class
from ..utils.round_parser import standardize_round_summary

logger = logging.getLogger(__name__)


def parse_card(response, event_id, event_url, is_live_mode=False):

    logger.info(f"Parsing event: {event_id}")

    status_string = response.css("div#eventPageHeader span::text").get(default="").strip()
    status = status_string.split()[0] if status_string else None

    name = response.css("h2::text").get(default="").strip() or None

    container = response.css('ul[data-controller="unordered-list-background"]')

    date_time_str = container.xpath(".//span[contains(text(), 'Date/Time')]/following-sibling::span/text()").get(default="").strip()
    datetime_utc = parse_datetime(date_time_str)
    venue = container.xpath(".//span[contains(text(), 'Venue')]/following-sibling::span/text()").get(default="").strip() or None
    location = container.xpath(".//span[contains(text(), 'Location')]/following-sibling::span//text()").get(default="").strip() or None

    if not is_live_mode:
        yield EventItem(
            item_type="event",
            event_id=event_id,
            event_url=event_url,
            name=name,
            status=status,
            datetime_utc=datetime_utc,
            venue=venue,
            location=location,
        )

    fights = response.css('ul[data-event-view-toggle-target="list"] > li[data-controller="table-row-background"]')
    cancelled_fights = response.xpath('//div[starts-with(@id, "bout") and contains(@id, "Cancelled")]')
    total_fights = len(fights)

    for index, fight in enumerate(fights, start=1):
        fight_order_number = total_fights - index + 1
        yield from parse_single_fight(fight, response, event_id, fight_order_number, is_live_mode)

    if not is_live_mode:
        for cancelled_fight in cancelled_fights:
            yield from parse_cancelled_fight(cancelled_fight, response, event_id)


def parse_single_fight(fight, response, event_id, auto_index, is_live_mode=False):
    web_view = fight.xpath("./div[1]")

    ### Fight summary ###
    fight_summary_div = web_view.xpath(".//div[contains(@class, 'flex w-full mt-1 mb-0.5 px-1.5')]")
    method_str = fight_summary_div.css("span.uppercase::text").get(default="").strip()
    method_parsed = split_method(method_str)
    method_type = method_parsed["method_type"]
    method_detail = method_parsed["method_detail"]
    round_summary_str = fight_summary_div.css(r"span.text-xs11.md\:text-xs10.leading-relaxed::text").get(default="").strip()
    round_summary = standardize_round_summary(round_summary_str)

    ### Fighter infos ###
    fight_participants_div = web_view.xpath("./div[@class='div group flex items:start justify-center gap-0.5 md:gap-0']")
    fighter1_div = fight_participants_div.xpath("./div[1]")
    fighter2_div = fight_participants_div.xpath("./div[3]")

    fighter1_data = parse_fighter_div(fighter1_div, response, is_first_fighter=True)
    fighter2_data = parse_fighter_div(fighter2_div, response, is_first_fighter=False)

    ### Fight metadata ###
    middle_div = fight_participants_div.xpath("./div[2]")
    box_div = middle_div.xpath("./div[1]")
    bout_details_button_div = middle_div.xpath("./div[2]")

    fight_relative_url = box_div.xpath("./span[1]/a/@href").get(default="").strip()
    fight_id = extract_fight_id(fight_relative_url)
    if not fight_id:
        logger.error(f"Could not extract fight_id from URL: {fight_relative_url}")
        return

    bout_type = box_div.xpath("./span[1]/a/text()").get(default="").strip() or None
    if bout_type == "* Rumor *":
        bout_type = "Main Card"
    weight_class_lbs = box_div.xpath("./div[1]/span/text()").get(default="").strip() or None
    weight_class_id = map_weight_class(weight_class_lbs)
    rounds_format = box_div.xpath("./div[2]/text()").get(default="").strip() or None
    fight_order = bout_details_button_div.xpath(".//span[2]/text()").get(default="").strip() or str(auto_index)

    ### Odds data ###
    bout_details_div = web_view.xpath("./div[@data-event-bout-details-target='content']")
    odds_data = parse_odds(bout_details_div)

    ### yield items ###
    yield FightItem(
        item_type="fight",
        fight_id=fight_id,
        event_id=event_id,
        method_type=method_type,
        method_detail=method_detail,
        round_summary=round_summary,
        bout_type=bout_type,
        weight_class_lbs=weight_class_lbs,
        weight_class_id=weight_class_id,
        rounds_format=rounds_format,
        fight_order=fight_order,
    )

    if not is_live_mode:
        for fighter_data in [fighter1_data, fighter2_data]:
            yield FighterItem(
                item_type="fighter",
                fighter_id=fighter_data.get("fighter_id"),
                name=fighter_data.get("name"),
                profile_url=fighter_data.get("profile_url"),
                image_url=fighter_data.get("image_url"),
            )

    odds_data = odds_data or {}
    for fighter_data, odds_value, odds_label in [
        (
            fighter1_data,
            odds_data.get("fighter1_odds_value"),
            odds_data.get("fighter1_odds_label"),
        ),
        (
            fighter2_data,
            odds_data.get("fighter2_odds_value"),
            odds_data.get("fighter2_odds_label"),
        ),
    ]:
        yield ParticipantItem(
            item_type="participation",
            fight_id=fight_id,
            fighter_id=fighter_data.get("fighter_id"),
            odds_value=odds_value,
            odds_label=odds_label,
            result=fighter_data.get("result"),
            record_after_fight=fighter_data.get("record_after_fight"),
            is_red_corner=fighter_data.get("is_red_corner"),
        )
