from ..items import FightItem, FighterItem, ParticipantItem
from ..utils.url_parser import extract_fight_id, extract_fighter_id


def parse_cancelled_fight(cancelled_fight_div, response, event_id: str):

    ### Fight metadata ###
    middle_div = cancelled_fight_div.xpath('.//div[@data-controller="tooltip"]')
    status_text = middle_div.xpath(".//a/text()").get(default="").strip()
    fight_relative_url = middle_div.xpath(".//a/@href").get(default="").strip()
    fight_id = extract_fight_id(fight_relative_url)

    # Sol dövüşçü
    fighter1_name = cancelled_fight_div.xpath('.//div[@id="leftNdesktop"]//a/text()').get(default="").strip()
    fighter1_relative_url = cancelled_fight_div.xpath('.//div[@id="leftNdesktop"]//a/@href').get(default="").strip()
    fighter1_profile_url = response.urljoin(fighter1_relative_url) if fighter1_relative_url else ""
    fighter1_id = extract_fighter_id(fighter1_relative_url)
    fighter1_img = cancelled_fight_div.xpath(".//div[1]//img/@src").get(default="").strip()

    # Sağ dövüşçü
    fighter2_name = cancelled_fight_div.xpath('.//div[@id="rightNdesktop"]//a/text()').get(default="").strip()
    fighter2_relative_url = cancelled_fight_div.xpath('.//div[@id="rightNdesktop"]//a/@href').get(default="").strip()
    fighter2_profile_url = response.urljoin(fighter2_relative_url) if fighter2_relative_url else ""
    fighter2_id = extract_fighter_id(fighter2_relative_url)
    fighter2_img = cancelled_fight_div.xpath('.//div[@id="rightNdesktop"]/following-sibling::div//img/@src').get(default="").strip()

    # Ensure all primary/foreign keys are present to satisfy DB schema and type checker
    if fight_id is None or fighter1_id is None or fighter2_id is None:
        return

    # Yield FightItem
    yield FightItem(
        item_type="fight",
        fight_id=fight_id,
        event_id=event_id,
        bout_type=status_text,
    )

    # Yield FighterItems
    for f_id, f_name, f_url, f_img in [
        (fighter1_id, fighter1_name, fighter1_profile_url, fighter1_img),
        (fighter2_id, fighter2_name, fighter2_profile_url, fighter2_img),
    ]:
        yield FighterItem(
            item_type="fighter",
            fighter_id=f_id,
            name=f_name,
            profile_url=f_url,
            image_url=f_img,
        )

    # Yield ParticipationItems
    yield ParticipantItem(
        item_type="participation",
        fight_id=fight_id,
        fighter_id=fighter1_id,
        result=status_text,
        is_red_corner=True,
    )

    yield ParticipantItem(
        item_type="participation",
        fight_id=fight_id,
        fighter_id=fighter2_id,
        result=status_text,
        is_red_corner=False,
    )
