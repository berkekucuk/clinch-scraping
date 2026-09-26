import logging
import re
from typing import Generator
from bs4 import BeautifulSoup, Tag
from scrapy.http import HtmlResponse

from ..items import FightItem, FightStatItem

logger = logging.getLogger(__name__)


# ==========================================
# 1. Text & Numeric Parsing Helpers
# ==========================================

def parse_landed_attempted(text: str) -> tuple[int, int]:
    """Converts formats like "15 of 30" or "15" into an (landed, attempted) integer tuple."""
    if not text or "--" in text:
        return 0, 0
    parts = text.strip().split(" of ")
    if len(parts) == 2:
        try:
            return int(parts[0].strip()), int(parts[1].strip())
        except ValueError:
            return 0, 0
    elif len(parts) == 1:
        try:
            val = int(parts[0].strip())
            return val, val
        except ValueError:
            return 0, 0
    return 0, 0


def parse_control_time(text: str) -> int:
    """Converts "3:45" format control time into total seconds."""
    if not text or "--" in text:
        return 0
    text = text.strip()
    if ":" in text:
        parts = text.split(":")
        try:
            minutes = int(parts[0])
            seconds = int(parts[1])
            return (minutes * 60) + seconds
        except ValueError:
            return 0
    try:
        return int(text)
    except ValueError:
        return 0


def parse_int_safe(text: str) -> int:
    """Safely parses a string into integer, returning 0 on failure."""
    if not text or "--" in text:
        return 0
    try:
        return int(text.strip())
    except ValueError:
        return 0


def map_weight_class_name(text: str) -> str | None:
    """Maps raw UFCStats fight title text to standard weight_class_id code."""
    if not text:
        return None
    cleaned = text.strip().lower()

    # Women weight classes
    if "women" in cleaned or "w strawweight" in cleaned or "w flyweight" in cleaned:
        if "strawweight" in cleaned or "straw weight" in cleaned:
            return "SW"
        if "flyweight" in cleaned or "fly weight" in cleaned:
            return "W_FLW"
        if "bantamweight" in cleaned or "bantam weight" in cleaned:
            return "W_BW"
        if "featherweight" in cleaned or "feather weight" in cleaned:
            return "W_FW"

    # Catchweight / Openweight
    if "catch" in cleaned:
        return "CW"
    if "open" in cleaned:
        return "OW"

    # Men standard weight classes
    if "light heavyweight" in cleaned or "lightheavyweight" in cleaned or "light-heavyweight" in cleaned or "lt. heavyweight" in cleaned or "lt heavyweight" in cleaned:
        return "LHW"
    if "heavyweight" in cleaned or "heavy weight" in cleaned:
        return "HW"
    if "middleweight" in cleaned or "middle weight" in cleaned:
        return "MW"
    if "welterweight" in cleaned or "welter weight" in cleaned:
        return "WW"
    if "lightweight" in cleaned or "light weight" in cleaned:
        return "LW"
    if "featherweight" in cleaned or "feather weight" in cleaned:
        return "FW"
    if "bantamweight" in cleaned or "bantam weight" in cleaned:
        return "BW"
    if "flyweight" in cleaned or "fly weight" in cleaned:
        return "FLW"
    if "strawweight" in cleaned or "straw weight" in cleaned:
        return "SW"

    return None


# ==========================================
# 2. Fighter & Fight Metadata Extractors
# ==========================================

def build_fighter_id_map(soup: BeautifulSoup, supabase_fight: dict) -> dict[str, str]:
    """Maps UFCStats ufcstats_fighter_id to Supabase fighter_id."""
    participants = supabase_fight.get("participants", [])
    ufcstats_to_fighter_id_map: dict[str, str] = {}

    for participant in participants:
        fighter_info = participant.get("fighters") or {}
        fighter_id = participant.get("fighter_id") or fighter_info.get("fighter_id")
        ufcstats_fighter_id = fighter_info.get("ufcstats_id")
        if ufcstats_fighter_id and fighter_id:
            ufcstats_to_fighter_id_map[ufcstats_fighter_id] = fighter_id

    # Fallback: Identify fighter order from top page links if missing
    person_links = soup.select("div.b-fight-details__person a.b-link")
    top_ufcstats_fighter_ids = [
        (a.get("href") or "").rstrip("/").split("/")[-1]
        for a in person_links
        if a.get("href")
    ]

    if len(top_ufcstats_fighter_ids) >= 2 and len(participants) >= 2:
        for idx in (0, 1):
            top_ufcstats_id = top_ufcstats_fighter_ids[idx]
            participant_fighter_id = participants[idx].get("fighter_id")
            if top_ufcstats_id not in ufcstats_to_fighter_id_map and participant_fighter_id:
                ufcstats_to_fighter_id_map[top_ufcstats_id] = participant_fighter_id

    return ufcstats_to_fighter_id_map


def extract_fight_metadata_item(soup: BeautifulSoup, fight_id: str) -> FightItem:
    """Extracts weight_class_id, title_type, referee and bonuses into a FightItem."""
    weight_class_id = None
    title_type = None
    referee = None
    bonuses = []
    has_belt_icon = False

    # 1. Fight Title, Weight Class, Title Belt, and Bonuses
    title_tag = soup.find("i", class_="b-fight-details__fight-title")
    if title_tag:
        img_tags = title_tag.find_all("img")
        for img in img_tags:
            src = img.get("src", "").lower()
            if "belt.png" in src:
                has_belt_icon = True
            elif "perf.png" in src:
                bonuses.append("PERF")
            elif "fight.png" in src:
                bonuses.append("FIGHT")
            elif "sub.png" in src:
                bonuses.append("SUB")
            elif "ko.png" in src:
                bonuses.append("KO")

        raw_text = re.sub(r"\s+", " ", title_tag.get_text()).strip()
        weight_class_id = map_weight_class_name(raw_text)

        raw_lower = raw_text.lower()
        if "interim" in raw_lower:
            title_type = "interim"
        elif "title bout" in raw_lower or has_belt_icon:
            title_type = "undisputed"

    # 2. Referee
    labels = soup.find_all("i", class_="b-fight-details__label")
    for lbl in labels:
        if "Referee:" in lbl.get_text():
            parent = lbl.parent
            if parent:
                span = parent.find("span")
                if span and span.get_text().strip():
                    referee = span.get_text().strip()
            break

    return FightItem(
        item_type="fight",
        fight_id=fight_id,
        weight_class_id=weight_class_id,
        title_type=title_type,
        referee=referee,
        bonuses=bonuses if bonuses else None
    )


# ==========================================
# 3. Fight Statistics Tables Extractors
# ==========================================

def _extract_fighter_ids_from_row(cols: list[Tag]) -> tuple[str, str] | None:
    """Extracts both ufcstats_fighter_ids from the first column links of a table row."""
    if not cols:
        return None
    links = cols[0].find_all("a")
    if len(links) < 2:
        return None
    ufcstats_fighter_id_1 = (links[0].get("href") or "").rstrip("/").split("/")[-1]
    ufcstats_fighter_id_2 = (links[1].get("href") or "").rstrip("/").split("/")[-1]
    return ufcstats_fighter_id_1, ufcstats_fighter_id_2


def _get_col_pair_texts(cols: list[Tag], col_idx: int) -> tuple[str, str]:
    """Extracts the pair of text values from two <p> tags in a table column."""
    if col_idx >= len(cols):
        return "", ""
    p_tags = cols[col_idx].find_all("p")
    text_1 = p_tags[0].get_text().strip() if len(p_tags) > 0 else ""
    text_2 = p_tags[1].get_text().strip() if len(p_tags) > 1 else ""
    return text_1, text_2


def _get_or_create_record(
    stats_map: dict[tuple[str, int], FightStatItem],
    ufcstats_fighter_id: str,
    round_num: int,
    ufcstats_fight_id: str,
    fight_id: str,
    ufcstats_to_fighter_id_map: dict[str, str],
) -> FightStatItem:
    """Retrieves existing FightStatItem or initializes a new one for the fighter and round."""
    key = (ufcstats_fighter_id, round_num)
    if key not in stats_map:
        stats_map[key] = FightStatItem(
            item_type="fight_stat",
            ufcstats_fight_id=ufcstats_fight_id,
            ufcstats_fighter_id=ufcstats_fighter_id,
            fight_id=fight_id,
            fighter_id=ufcstats_to_fighter_id_map.get(ufcstats_fighter_id),
            round=round_num,
        )
    return stats_map[key]


def process_totals_row(
    row: Tag,
    round_num: int,
    stats_map: dict[tuple[str, int], FightStatItem],
    ufcstats_fight_id: str,
    fight_id: str,
    ufcstats_to_fighter_id_map: dict[str, str],
) -> None:
    """Parses Totals table row (knockdowns, strikes, takedowns, submissions, control time)."""
    cols = row.find_all("td")
    if len(cols) < 10:
        return

    ufcstats_fighter_ids = _extract_fighter_ids_from_row(cols)
    if not ufcstats_fighter_ids:
        return
    ufcstats_fighter_id_1, ufcstats_fighter_id_2 = ufcstats_fighter_ids

    kd_1, kd_2 = _get_col_pair_texts(cols, 1)
    sig_1, sig_2 = _get_col_pair_texts(cols, 2)
    tot_1, tot_2 = _get_col_pair_texts(cols, 4)
    td_1, td_2 = _get_col_pair_texts(cols, 5)
    sub_1, sub_2 = _get_col_pair_texts(cols, 7)
    rev_1, rev_2 = _get_col_pair_texts(cols, 8)
    ctrl_1, ctrl_2 = _get_col_pair_texts(cols, 9)

    for ufcstats_fighter_id, kd, sig, tot, td, sub, rev, ctrl in (
        (ufcstats_fighter_id_1, kd_1, sig_1, tot_1, td_1, sub_1, rev_1, ctrl_1),
        (ufcstats_fighter_id_2, kd_2, sig_2, tot_2, td_2, sub_2, rev_2, ctrl_2),
    ):
        record = _get_or_create_record(
            stats_map, ufcstats_fighter_id, round_num, ufcstats_fight_id, fight_id, ufcstats_to_fighter_id_map
        )
        record.knockdowns = parse_int_safe(kd)
        record.sig_strikes_landed, record.sig_strikes_attempted = parse_landed_attempted(sig)
        record.total_strikes_landed, record.total_strikes_attempted = parse_landed_attempted(tot)
        record.takedowns_landed, record.takedowns_attempted = parse_landed_attempted(td)
        record.submission_attempts = parse_int_safe(sub)
        record.reversals = parse_int_safe(rev)
        record.control_time_seconds = parse_control_time(ctrl)


def process_sig_strikes_row(
    row: Tag,
    round_num: int,
    stats_map: dict[tuple[str, int], FightStatItem],
    ufcstats_fight_id: str,
    fight_id: str,
    ufcstats_to_fighter_id_map: dict[str, str],
) -> None:
    """Parses Significant Strikes table row (head, body, leg, distance, clinch, ground)."""
    cols = row.find_all("td")
    if len(cols) < 9:
        return

    ufcstats_fighter_ids = _extract_fighter_ids_from_row(cols)
    if not ufcstats_fighter_ids:
        return
    ufcstats_fighter_id_1, ufcstats_fighter_id_2 = ufcstats_fighter_ids

    head_1, head_2 = _get_col_pair_texts(cols, 3)
    body_1, body_2 = _get_col_pair_texts(cols, 4)
    leg_1, leg_2 = _get_col_pair_texts(cols, 5)
    dist_1, dist_2 = _get_col_pair_texts(cols, 6)
    clinch_1, clinch_2 = _get_col_pair_texts(cols, 7)
    ground_1, ground_2 = _get_col_pair_texts(cols, 8)

    for ufcstats_fighter_id, head, body, leg, dist, clinch, ground in (
        (ufcstats_fighter_id_1, head_1, body_1, leg_1, dist_1, clinch_1, ground_1),
        (ufcstats_fighter_id_2, head_2, body_2, leg_2, dist_2, clinch_2, ground_2),
    ):
        record = _get_or_create_record(
            stats_map, ufcstats_fighter_id, round_num, ufcstats_fight_id, fight_id, ufcstats_to_fighter_id_map
        )
        record.head_landed, record.head_attempted = parse_landed_attempted(head)
        record.body_landed, record.body_attempted = parse_landed_attempted(body)
        record.leg_landed, record.leg_attempted = parse_landed_attempted(leg)
        record.distance_landed, record.distance_attempted = parse_landed_attempted(dist)
        record.clinch_landed, record.clinch_attempted = parse_landed_attempted(clinch)
        record.ground_landed, record.ground_attempted = parse_landed_attempted(ground)


def _process_stat_table(
    table: Tag,
    row_processor,
    stats_map: dict[tuple[str, int], FightStatItem],
    ufcstats_fight_id: str,
    fight_id: str,
    ufcstats_to_fighter_id_map: dict[str, str],
) -> None:
    """Processes single or round-by-round statistics table."""
    thead = table.find("thead")
    tbody = table.find("tbody")
    if not thead or not tbody:
        return

    thead_classes = thead.get("class", [])
    is_rnd_table = "b-fight-details__table-head_rnd" in thead_classes

    if not is_rnd_table:
        row = tbody.find("tr")
        if row:
            row_processor(row, 0, stats_map, ufcstats_fight_id, fight_id, ufcstats_to_fighter_id_map)
    else:
        round_headers = table.find_all(lambda tag: tag.name in ("thead", "tr") and "Round" in tag.get_text())
        for r_head in round_headers:
            m = re.search(r"Round\s+(\d+)", r_head.get_text(), re.IGNORECASE)
            if m:
                round_num = int(m.group(1))
                next_tr = r_head.find_next(
                    "tr",
                    class_=lambda c: c and "b-fight-details__table-row" in c and "b-fight-details__table-row_type_head" not in c
                )
                if next_tr:
                    row_processor(next_tr, round_num, stats_map, ufcstats_fight_id, fight_id, ufcstats_to_fighter_id_map)


def extract_fight_stat_items(
    soup: BeautifulSoup,
    ufcstats_fight_id: str,
    fight_id: str,
    ufcstats_to_fighter_id_map: dict[str, str]
) -> list[FightStatItem]:
    """Extracts all Totals and Significant Strikes tables into a list of FightStatItem objects."""
    stats_map: dict[tuple[str, int], FightStatItem] = {}

    for table in soup.find_all("table"):
        thead = table.find("thead")
        if not thead:
            continue
        thead_text = thead.get_text()

        if "KD" in thead_text and "Total str." in thead_text:
            _process_stat_table(table, process_totals_row, stats_map, ufcstats_fight_id, fight_id, ufcstats_to_fighter_id_map)
        elif "Head" in thead_text and "Distance" in thead_text:
            _process_stat_table(table, process_sig_strikes_row, stats_map, ufcstats_fight_id, fight_id, ufcstats_to_fighter_id_map)

    return [stat for stat in stats_map.values() if stat.fighter_id]


# ==========================================
# 4. Main Callback Orchestrator
# ==========================================

def parse_live_fight_details(
    response: HtmlResponse,
    fight_id: str,
    ufcstats_fight_id: str,
    supabase_fight: dict
) -> Generator[FightStatItem | FightItem, None, None]:
    """
    Parses live fight statistics and metadata (weight_class, title_type, referee, bonuses)
    from UFCStats fight details page.
    """
    logger.info(f"[LIVE FIGHT PARSER] Parsing fight details: {response.url} (Fight ID: {fight_id})")

    soup = BeautifulSoup(response.text, "html.parser")

    # 1. Build Fighter ID Mapping
    ufcstats_to_fighter_id_map = build_fighter_id_map(soup, supabase_fight)

    # 2. Extract Fight Statistics Tables (Totals & Significant Strikes)
    stat_items = extract_fight_stat_items(soup, ufcstats_fight_id, fight_id, ufcstats_to_fighter_id_map)
    for stat_item in stat_items:
        yield stat_item

    logger.info(f"[LIVE FIGHT PARSER] Extracted {len(stat_items)} stat rows for Fight ID: {fight_id}")

    # 3. Extract Fight Metadata (weight_class_id, title_type, referee, bonuses)
    yield extract_fight_metadata_item(soup, fight_id)
