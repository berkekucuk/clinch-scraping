from ..utils.item_factory import create_fight_item, create_fighter_items, create_participation_items
from ..utils.url_parser import extract_fight_id, extract_fighter_id


def parse_cancelled_fight(cancelled_fight_div, response, event_id):

    ### Fight metadata ###
    middle_div = cancelled_fight_div.xpath('.//div[@data-controller="tooltip"]')
    status_text = middle_div.xpath(".//a/text()").get(default="").strip()
    fight_relative_url = middle_div.xpath(".//a/@href").get(default="").strip()
    fight_id = extract_fight_id(fight_relative_url) if fight_relative_url else None

    fight_summary = {
        "method_type": None,
        "method_detail": None,
        "round_summary": None,
    }

    fight_metadata = {
        "fight_id": fight_id,
        "bout_type": status_text,
        "weight_class_lbs": None,
        "weight_class_id": None,
        "rounds_format": None,
        "fight_order": None,
    }

    # Sol dövüşçü
    fighter1_name = cancelled_fight_div.xpath('.//div[@id="leftNdesktop"]//a/text()').get(default="").strip()
    fighter1_relative_url = cancelled_fight_div.xpath('.//div[@id="leftNdesktop"]//a/@href').get(default="").strip()
    fighter1_profile_url = response.urljoin(fighter1_relative_url) if fighter1_relative_url else ""
    fighter1_id = extract_fighter_id(fighter1_relative_url) if fighter1_relative_url else None
    fighter1_img = cancelled_fight_div.xpath(".//div[1]//img/@src").get(default="").strip()

    # Sağ dövüşçü
    fighter2_name = cancelled_fight_div.xpath('.//div[@id="rightNdesktop"]//a/text()').get(default="").strip()
    fighter2_relative_url = cancelled_fight_div.xpath('.//div[@id="rightNdesktop"]//a/@href').get(default="").strip()
    fighter2_profile_url = response.urljoin(fighter2_relative_url) if fighter2_relative_url else ""
    fighter2_id = extract_fighter_id(fighter2_relative_url) if fighter2_relative_url else None
    fighter2_img = cancelled_fight_div.xpath('.//div[@id="rightNdesktop"]/following-sibling::div//img/@src').get(default="").strip()

    fighter1_data = {
        "fighter_id": fighter1_id,
        "name": fighter1_name,
        "profile_url": fighter1_profile_url,
        "image_url": fighter1_img,
        "record_after_fight": None,
        "is_red_corner": True,
    }

    fighter2_data = {
        "fighter_id": fighter2_id,
        "name": fighter2_name,
        "profile_url": fighter2_profile_url,
        "image_url": fighter2_img,
        "record_after_fight": None,
        "is_red_corner": False,
    }

    # Yield FightItem
    yield create_fight_item(
        fight_metadata,
        event_id,
        fight_summary,
    )

    # Yield FighterItems
    for fighter_item in create_fighter_items(fighter1_data, fighter2_data):
        yield fighter_item

    # Yield ParticipationItems
    for participation_item in create_participation_items(
        fight_id,
        fighter1_data,
        fighter2_data,
        result1=status_text,
        result2=status_text,
    ):
        yield participation_item
