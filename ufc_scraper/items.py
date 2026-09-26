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
    event_id: str | None = None  # FK -> EventItem
    method_type: str | None = None
    method_detail: str | None = None
    round_summary: str | None = None
    bout_type: str | None = None
    weight_class_lbs: str | None = None
    weight_class_id: str | None = None
    rounds_format: str | None = None
    fight_order: str | None = None
    title_type: str | None = None
    referee: str | None = None
    bonuses: list[str] | None = None


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


@dataclass
class RankingItem:
    item_type: str
    weight_class_id: str
    fighter_id: str
    rank_number: int
    rank_change: int | None = None


@dataclass
class FightStatItem:
    item_type: str
    ufcstats_fight_id: str
    ufcstats_fighter_id: str
    round: int = 0
    fight_id: str | None = None
    fighter_id: str | None = None
    knockdowns: int = 0
    total_strikes_landed: int = 0
    total_strikes_attempted: int = 0
    sig_strikes_landed: int = 0
    sig_strikes_attempted: int = 0
    takedowns_landed: int = 0
    takedowns_attempted: int = 0
    submission_attempts: int = 0
    reversals: int = 0
    control_time_seconds: int = 0
    head_landed: int = 0
    head_attempted: int = 0
    body_landed: int = 0
    body_attempted: int = 0
    leg_landed: int = 0
    leg_attempted: int = 0
    distance_landed: int = 0
    distance_attempted: int = 0
    clinch_landed: int = 0
    clinch_attempted: int = 0
    ground_landed: int = 0
    ground_attempted: int = 0