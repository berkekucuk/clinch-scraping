import json
import logging
import re
from datetime import date, datetime

from ..items import FightOddsItem
from ..utils.matching import get_candidate_fights, log_unmatched_fights, match_fight, pick_by_date_and_name

logger = logging.getLogger(__name__)

METHOD_NAMES = {"TKO/KO": "KO/TKO", "submission": "SUB", "decision": "DEC"}
PROP_PATTERN = re.compile(r"wins by (TKO/KO|submission|decision)(?: in round (\d))?$")

SPORTSBOOKS = ("FanDuel", "Unibet", "BetRivers", "BetWay", "Caesars")


def _moneyline_keys(book_odds: dict) -> list[tuple]:
    """Returns the moneyline keys: each fighter wins by any method."""
    return [(side, "ANY", 0) for side in (1, 2)]


def _method_market_keys(book_odds: dict) -> list[tuple]:
    """Returns the method market keys: KO/TKO, SUB and DEC in any round for each fighter."""
    return [(side, method, 0) for side in (1, 2) for method in ("KO/TKO", "SUB", "DEC")]


def _round_market_keys(book_odds: dict) -> list[tuple]:
    """
    Returns the round market keys: KO/TKO and SUB in each round plus DEC for each fighter.

    Rounds 4 and 5 are included only if the sportsbook offers them (five-round fights).
    """
    rounds = 5 if any(key[2] in (4, 5) for key in book_odds) else 3
    keys = [(side, method, r) for side in (1, 2) for method in ("KO/TKO", "SUB") for r in range(1, rounds + 1)]
    return keys + [(side, "DEC", 0) for side in (1, 2)]


def _book_name(th) -> str:
    texts = [t.strip() for t in th.css("::text").getall() if t.strip()]
    return texts[0] if texts else ""


def _parse_odds(text: str | None) -> int | None:
    try:
        return int(text.strip()) if text else None
    except ValueError:
        return None


def _parse_fights(table) -> list[dict]:
    """Groups table rows into fights: two fighter rows (moneyline) followed by their prop rows."""
    fights = []

    for row in table.css("tbody tr"):
        label = " ".join(" ".join(row.css("th ::text").getall()).split())

        if "pr" not in (row.attrib.get("class") or "").split():
            matchup_id = row.css("th::attr(data-admin-matchup)").get()
            if matchup_id:
                fights.append({"fighters": [label], "props": {}})
            elif fights and len(fights[-1]["fighters"]) == 1:
                fights[-1]["fighters"].append(label)
            else:
                continue

            # data-li: [book_id, side, matchup_id]
            for cell in row.css("td[data-li]:not(.button-cell)"):
                book_id, side, *_ = json.loads(cell.attrib["data-li"])
                odds = _parse_odds(cell.css("span::text").get())
                if odds is not None:
                    fights[-1]["props"].setdefault(str(book_id), {})[(side, "ANY", 0)] = odds
            continue

        match = PROP_PATTERN.search(label)
        if not match or not fights:
            continue

        method = METHOD_NAMES[match.group(1)]
        round_number = int(match.group(2)) if match.group(2) else 0

        # data-li: [book_id, ?, matchup_id, prop_type, side]
        for cell in row.css("td[data-li]:not(.button-cell)"):
            book_id, *_, side = json.loads(cell.attrib["data-li"])
            odds = _parse_odds(cell.css("span::text").get())
            if odds is not None:
                fights[-1]["props"].setdefault(str(book_id), {})[(side, method, round_number)] = odds

    return fights


def _complete_markets(book_odds: dict) -> dict[str, list[tuple]]:
    """Returns the keys of each market the sportsbook offers with every outcome."""
    markets = {}
    for name, keys_fn in (("moneyline", _moneyline_keys), ("method", _method_market_keys), ("round", _round_market_keys)):
        keys = keys_fn(book_odds)
        if all(key in book_odds for key in keys):
            markets[name] = keys
    return markets


def _pick_sportsbook(fight: dict, book_ids: dict[str, str]) -> tuple[str, dict, dict] | None:
    """
    Picks the single sportsbook to take all odds of the fight from.

    A sportsbook with the moneyline is preferred, then the one with the most complete prop markets.
    Ties are broken by SPORTSBOOKS order. Returns (book, its odds, its complete markets) or None.
    """
    best, best_score = None, None

    for book in SPORTSBOOKS:
        book_odds = fight["props"].get(book_ids.get(book), {})
        markets = _complete_markets(book_odds)
        if not markets:
            continue

        score = ("moneyline" in markets, len(markets))
        if best_score is None or score > best_score:
            best, best_score = (book, book_odds, markets), score

    return best


def _parse_header_date(text: str | None, reference: date) -> date | None:
    """
    Parses a table header date such as 'December 5th'.

    The header has no year, so the year closest to the reference date is used.
    """
    match = re.match(r"([A-Za-z]+)\s+(\d{1,2})", (text or "").strip())
    if not match:
        return None

    candidates = []
    for year in (reference.year - 1, reference.year, reference.year + 1):
        try:
            candidates.append(datetime.strptime(f"{match.group(1)} {match.group(2)} {year}", "%B %d %Y").date())
        except ValueError:
            continue

    return min(candidates, key=lambda d: abs(d - reference)) if candidates else None


def _find_event_table(response, event: dict):
    """Returns (name, table) for the event's UFC odds table, matched by date with the name as a tiebreaker."""
    event_date = datetime.fromisoformat(event["datetime_utc"]).date()
    tables = []

    for table in response.css("table.odds-table"):
        if not table.css("thead th[data-b]"):
            continue

        header = table.xpath("preceding::div[contains(@class, 'table-header')][1]")
        name = " ".join(header.css("h1 ::text").getall()).strip()
        if name.startswith("UFC"):
            tables.append((name, _parse_header_date(header.css(".table-header-date::text").get(), event_date), table))

    matched, candidate_count = pick_by_date_and_name(
        tables, event_date, event.get("name"),
        get_date=lambda t: t[1],
        get_name=lambda t: t[0].removesuffix(" Odds"),
    )
    if not matched:
        logger.warning(f"[ODDS PARSER] No unique odds table for event {event['event_id']} ({candidate_count} candidates)")
        return None

    name, _, table = matched
    return name, table


def parse_event_odds(response, event: dict):
    """
    Parses the odds of a Supabase event from the BestFightOdds homepage.

    Yields fight winner odds and method of victory odds (KO/TKO, SUB, DEC), overall and per round.
    """
    found = _find_event_table(response, event)
    if not found:
        return

    table_name, table = found
    book_ids = {_book_name(th): th.attrib["data-b"] for th in table.css("thead th[data-b]")}
    bfo_fights = _parse_fights(table)

    candidate_fights = get_candidate_fights(event.get("fights") or [])
    logger.info(f"[ODDS PARSER] '{table_name}' -> event {event['event_id']}: {len(bfo_fights)} fights on BestFightOdds, {len(candidate_fights)} in DB")

    for bfo_fight in bfo_fights:
        fight_label = " vs ".join(bfo_fight["fighters"])
        matched = match_fight([(None, name) for name in bfo_fight["fighters"]], candidate_fights)

        if not matched:
            logger.warning(f"[ODDS PARSER] No unique DB match for '{fight_label}' in event {event['event_id']}")
            continue

        fight, sides = matched
        candidate_fights.remove(fight)

        picked = _pick_sportsbook(bfo_fight, book_ids)
        if not picked:
            logger.info(f"[ODDS PARSER] No odds yet for '{fight_label}'")
            continue

        book, book_odds, markets = picked
        if markets.keys() == {"moneyline"}:
            logger.info(f"[ODDS PARSER] No method/round props yet for '{fight_label}', moneyline only ({book})")

        # Decision is part of both the method and the round market, so keys are deduplicated
        keys = dict.fromkeys(key for market_keys in markets.values() for key in market_keys)

        for side, method, round_number in keys:
            yield FightOddsItem(
                item_type="fight_odds",
                fight_id=fight["fight_id"],
                fighter_id=sides[side - 1]["fighter_id"],
                method=method,
                round=round_number,
                odds_value=book_odds[(side, method, round_number)],
                sportsbook=book,
            )

    log_unmatched_fights("[ODDS PARSER]", "BestFightOdds", event["event_id"], candidate_fights)
