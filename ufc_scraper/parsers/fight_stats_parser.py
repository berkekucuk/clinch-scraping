import logging

from ..items import FightItem, FightStatItem
from ..utils.stats_parser import (
    is_name_match,
    parse_control_time,
    parse_int_safe,
    parse_landed_attempted,
)

logger = logging.getLogger(__name__)


# ==========================================
# 1. Fighter & Fight Metadata Extractors
# ==========================================

def build_fighter_id_map(response, supabase_fight: dict) -> dict[str, str]:
    """Maps UFCStats ufcstats_fighter_id to Supabase fighter_id using Scrapy CSS selectors and name matching."""
    participants = supabase_fight.get("participants", [])
    ufcstats_to_fighter_id_map: dict[str, str] = {}

    # 1. Primary: Direct ufcstats_id match from database
    for participant in participants:
        fighter_info = participant.get("fighters")
        fighter_id = participant.get("fighter_id")
        ufcstats_fighter_id = fighter_info.get("ufcstats_id")
        if ufcstats_fighter_id and fighter_id:
            ufcstats_to_fighter_id_map[ufcstats_fighter_id] = fighter_id

    # 2. Fallback: Fuzzy name-based matching from top page person cards
    for person in response.css("div.b-fight-details__person"):
        href = person.css("a.b-link::attr(href)").get()
        if not href:
            continue
        ufcstats_id = href.rstrip("/").split("/")[-1]
        if ufcstats_id in ufcstats_to_fighter_id_map:
            continue

        web_name = person.css("a.b-link::text").get() or ""

        for participant in participants:
            fighter_id = participant.get("fighter_id")
            fighter_info = participant.get("fighters")
            db_name = fighter_info.get("name")

            if is_name_match(web_name, db_name):
                ufcstats_to_fighter_id_map[ufcstats_id] = fighter_id
                break

    return ufcstats_to_fighter_id_map


def extract_fight_metadata_item(response, fight_id: str) -> FightItem:
    """Extracts title_type, referee and bonuses into a FightItem using CSS selectors."""
    title_type = None
    bonuses = []

    # 1. Fight Title, Title Belt, and Bonuses
    title_tag = response.css("i.b-fight-details__fight-title")
    if title_tag:
        img_srcs = [s.lower() for s in title_tag.css("img::attr(src)").getall()]
        for src in img_srcs:
            if "perf.png" in src:
                bonuses.append("PERF")
            elif "fight.png" in src:
                bonuses.append("FIGHT")
            elif "sub.png" in src:
                bonuses.append("SUB")
            elif "ko.png" in src:
                bonuses.append("KO")

        title_text = "".join(title_tag.css("::text").getall()).lower()
        is_tournament = any(kw in title_text for kw in ("tournament", "ultimate fighter", "tuf"))

        if not is_tournament and "title bout" in title_text:
            title_type = "interim" if "interim" in title_text else "undisputed"

    # 2. Referee
    ref_text = response.xpath("//i[contains(text(), 'Referee:')]/following-sibling::span/text()").get()
    referee = ref_text.strip() if ref_text and ref_text.strip() else None

    return FightItem(
        item_type="fight",
        fight_id=fight_id,
        title_type=title_type,
        referee=referee,
        bonuses=bonuses if bonuses else None
    )


# ==========================================
# 2. Fight Statistics Tables Extractors
# ==========================================

def _get_col_pair_texts(cols, col_idx: int) -> tuple[str, str]:
    """Extracts the pair of text values from two <p> tags in a table column."""
    if col_idx >= len(cols):
        return "", ""
    p_texts = [t.strip() for t in cols[col_idx].css("p::text").getall() if t.strip()]
    text_1 = p_texts[0] if len(p_texts) > 0 else ""
    text_2 = p_texts[1] if len(p_texts) > 1 else ""
    return text_1, text_2


def process_totals_row(
    row,
    round_num: int,
    stats_map: dict[tuple[str, int], FightStatItem],
    ufcstats_fight_id: str,
    fight_id: str,
    ufcstats_to_fighter_id_map: dict[str, str],
) -> None:
    """Parses Totals table row (knockdowns, strikes, takedowns, submissions, control time)."""
    cols = row.css("td")
    if len(cols) < 10:
        return

    links = cols[0].css("a::attr(href)").getall()
    if len(links) < 2:
        return
    ufcstats_fighter_id_1 = links[0].rstrip("/").split("/")[-1]
    ufcstats_fighter_id_2 = links[1].rstrip("/").split("/")[-1]

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
        record = stats_map[key]
        record.knockdowns = parse_int_safe(kd)
        record.sig_strikes_landed, record.sig_strikes_attempted = parse_landed_attempted(sig)
        record.total_strikes_landed, record.total_strikes_attempted = parse_landed_attempted(tot)
        record.takedowns_landed, record.takedowns_attempted = parse_landed_attempted(td)
        record.submission_attempts = parse_int_safe(sub)
        record.reversals = parse_int_safe(rev)
        record.control_time_seconds = parse_control_time(ctrl)


def process_sig_strikes_row(
    row,
    round_num: int,
    stats_map: dict[tuple[str, int], FightStatItem],
    ufcstats_fight_id: str,
    fight_id: str,
    ufcstats_to_fighter_id_map: dict[str, str],
) -> None:
    """Parses Significant Strikes table row (head, body, leg, distance, clinch, ground)."""
    cols = row.css("td")
    if len(cols) < 9:
        return

    links = cols[0].css("a::attr(href)").getall()
    if len(links) < 2:
        return
    ufcstats_fighter_id_1 = links[0].rstrip("/").split("/")[-1]
    ufcstats_fighter_id_2 = links[1].rstrip("/").split("/")[-1]

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
        record = stats_map[key]
        record.head_landed, record.head_attempted = parse_landed_attempted(head)
        record.body_landed, record.body_attempted = parse_landed_attempted(body)
        record.leg_landed, record.leg_attempted = parse_landed_attempted(leg)
        record.distance_landed, record.distance_attempted = parse_landed_attempted(dist)
        record.clinch_landed, record.clinch_attempted = parse_landed_attempted(clinch)
        record.ground_landed, record.ground_attempted = parse_landed_attempted(ground)


def extract_fight_stat_items(
    response,
    ufcstats_fight_id: str,
    fight_id: str,
    ufcstats_to_fighter_id_map: dict[str, str]
) -> list[FightStatItem]:
    """Extracts all Totals and Significant Strikes tables using Scrapy CSS selectors."""
    stats_map: dict[tuple[str, int], FightStatItem] = {}

    for table in response.css("table"):
        thead_text = "".join(table.css("thead ::text").getall())
        is_totals = "KD" in thead_text and "Total str." in thead_text
        is_sig = "Head" in thead_text and "Distance" in thead_text

        if not (is_totals or is_sig):
            continue

        processor = process_totals_row if is_totals else process_sig_strikes_row
        thead_class = table.css("thead::attr(class)").get() or ""
        is_rnd_table = "b-fight-details__table-head_rnd" in thead_class

        data_rows = [
            r for r in table.css("tr.b-fight-details__table-row")
            if len(r.css("td:first-child a")) >= 2
        ]

        for idx, row in enumerate(data_rows):
            round_num = 0 if not is_rnd_table else (idx + 1)
            processor(row, round_num, stats_map, ufcstats_fight_id, fight_id, ufcstats_to_fighter_id_map)

    return [stat for stat in stats_map.values() if stat.fighter_id]


# ==========================================
# 3. Main Callback Orchestrator
# ==========================================

def parse_live_fight_details(
    response,
    fight_id: str,
    ufcstats_fight_id: str,
    supabase_fight: dict
):
    """
    Parses live fight statistics and metadata (title_type, referee, bonuses)
    from UFCStats fight details page using native Scrapy CSS selectors.
    """
    logger.info(f"[LIVE FIGHT PARSER] Parsing fight details: {response.url} (Fight ID: {fight_id})")

    # 1. Build Fighter ID Mapping
    ufcstats_to_fighter_id_map = build_fighter_id_map(response, supabase_fight)

    # 2. Extract Fight Statistics Tables (Totals & Significant Strikes)
    stat_items = extract_fight_stat_items(response, ufcstats_fight_id, fight_id, ufcstats_to_fighter_id_map)
    for stat_item in stat_items:
        yield stat_item

    logger.info(f"[LIVE FIGHT PARSER] Extracted {len(stat_items)} stat rows for Fight ID: {fight_id}")

    # 3. Extract Fight Metadata (title_type, referee, bonuses)
    yield extract_fight_metadata_item(response, fight_id)
