from ..items import EventItem, FightItem, FightParticipationItem, FighterItem


def create_event_item(event_id, event_url, name, status, datetime_utc, venue, location):

    event_item = EventItem()
    event_item["item_type"] = "event"
    event_item["event_id"] = event_id
    event_item["event_url"] = event_url
    event_item["name"] = name
    event_item["status"] = status
    event_item["datetime_utc"] = datetime_utc
    event_item["venue"] = venue
    event_item["location"] = location
    return event_item


def create_fight_item(fight_metadata, event_id, fight_summary):

    fight_item = FightItem()
    fight_item["item_type"] = "fight"
    fight_item["fight_id"] = fight_metadata.get("fight_id")
    fight_item["event_id"] = event_id
    fight_item["method_type"] = fight_summary.get("method_type")
    fight_item["method_detail"] = fight_summary.get("method_detail")
    fight_item["round_summary"] = fight_summary.get("round_summary")
    fight_item["bout_type"] = fight_metadata.get("bout_type")
    fight_item["weight_class_lbs"] = fight_metadata.get("weight_class_lbs")
    fight_item["weight_class_id"] = fight_metadata.get("weight_class_id")
    fight_item["rounds_format"] = fight_metadata.get("rounds_format")
    fight_item["fight_order"] = fight_metadata.get("fight_order")
    return fight_item


def create_fighter_items(fighter1_data, fighter2_data):

    items = []
    for fighter_data in [fighter1_data, fighter2_data]:
        fighter_item = FighterItem()
        fighter_item["item_type"] = "fighter"
        fighter_item["fighter_id"] = fighter_data.get("fighter_id")
        fighter_item["name"] = fighter_data.get("name")
        fighter_item["profile_url"] = fighter_data.get("profile_url")
        fighter_item["image_url"] = fighter_data.get("image_url")
        items.append(fighter_item)
    return items


def create_participation_items(
    fight_id,
    fighter1_data,
    fighter2_data,
    odds_data=None,
    result1=None,
    result2=None,
):

    odds_data = odds_data or {}

    items = []
    for fighter_data, odds_value, odds_label, result in [
        (
            fighter1_data,
            odds_data.get("fighter1_odds_value", None),
            odds_data.get("fighter1_odds_label", None),
            result1 or fighter1_data.get("result"),
        ),
        (
            fighter2_data,
            odds_data.get("fighter2_odds_value", None),
            odds_data.get("fighter2_odds_label", None),
            result2 or fighter2_data.get("result"),
        ),
    ]:
        participation = FightParticipationItem()
        participation["item_type"] = "participation"
        participation["fight_id"] = fight_id
        participation["fighter_id"] = fighter_data.get("fighter_id")
        participation["odds_value"] = odds_value
        participation["odds_label"] = odds_label
        participation["result"] = result
        participation["record_after_fight"] = fighter_data.get("record_after_fight")
        participation["is_red_corner"] = fighter_data.get("is_red_corner")
        items.append(participation)
    return items


def create_fighter_update_item(
    fighter_id,
    nickname,
    record,
    date_of_birth,
    height,
    reach,
    weight_class_id,
    born,
    fighting_out_of,
    style,
    country_code,
):
    fighter_item = FighterItem()
    fighter_item['item_type'] = "fighter_update"
    fighter_item['fighter_id'] = fighter_id
    fighter_item['nickname'] = nickname
    fighter_item['record'] = record
    fighter_item['date_of_birth'] = date_of_birth
    fighter_item['height'] = height
    fighter_item['reach'] = reach
    fighter_item['weight_class_id'] = weight_class_id
    fighter_item['born'] = born
    fighter_item['fighting_out_of'] = fighting_out_of
    fighter_item['style'] = style
    fighter_item['country_code'] = country_code
    return fighter_item

