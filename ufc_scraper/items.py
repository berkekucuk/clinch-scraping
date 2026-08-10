from dataclasses import dataclass

@dataclass
class EventItem:
    item_type: str
    event_id: str  # PK
    event_url: str
    status: str | None = None
    name: str | None = None
    datetime_utc: str | None = None
    venue: str | None = None
    location: str | None = None


@dataclass
class FightItem:
    item_type: str
    fight_id: str  # PK
    event_id: str  # FK -> EventItem
    method_type: str | None = None
    method_detail: str | None = None
    round_summary: str | None = None
    bout_type: str | None = None
    weight_class_lbs: str | None = None
    weight_class_id: str | None = None
    rounds_format: str | None = None
    fight_order: str | None = None


@dataclass
class FighterItem:
    item_type: str
    fighter_id: str  # PK
    name: str | None = None
    nickname: str | None = None
    record: dict | None = None
    date_of_birth: str | None = None
    height: dict | None = None
    reach: dict | None = None
    weight_class_id: str | None = None
    born: str | None = None
    fighting_out_of: str | None = None
    style: str | None = None
    country_code: str | None = None
    profile_url: str | None = None
    image_url: str | None = None


@dataclass
class ParticipantItem:
    item_type: str
    fight_id: str  # FK -> FightItem
    fighter_id: str  # FK -> FighterItem
    odds_value: int | None = None
    odds_label: str | None = None
    result: str | None = None
    record_after_fight: dict | None = None
    is_red_corner: bool | None = None
