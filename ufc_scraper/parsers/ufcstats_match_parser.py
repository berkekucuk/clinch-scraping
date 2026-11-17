import logging
from datetime import datetime, timedelta

from ..items import EventItem, FightItem, FighterItem
from ..utils.stats_parser import is_name_match, normalize_name

logger = logging.getLogger(__name__)

CANCELLED_BOUT_TYPES = ("cancelled", "canceled", "fizzled")

# UFCStats shows the local event date, which can differ from the UTC date by a day
DATE_TOLERANCE = timedelta(days=1)


def _extract_id(url: str | None) -> str | None:
    return url.rstrip("/").split("/")[-1] if url else None


# ==========================================
# 1. Event Matching (upcoming events list)
# ==========================================

def parse_upcoming_events(response, supabase_events: list[dict]):
    """Matches UFCStats upcoming events to Supabase events by name, then by date.
    Every event is re-matched on each run, but only changed ufcstats_ids are written."""
    candidate_events = [e for e in supabase_events if e.get("datetime_utc")]
    event_by_ufcstats_id = {e["ufcstats_id"]: e for e in supabase_events if e.get("ufcstats_id")}

    for row in response.css("tr.b-statistics__table-row"):
        link = row.css("a.b-link")
        if not link:
            continue

        ufcstats_id = _extract_id(link.attrib.get("href"))
        name = link.css("::text").get(default="").strip()
        date_str = row.css("span.b-statistics__date::text").get(default="").strip()

        if not ufcstats_id:
            continue

        try:
            event_date = datetime.strptime(date_str, "%B %d, %Y").date()
        except ValueError:
            logger.warning(f"[EVENT MATCH] Could not parse date '{date_str}' for '{name}'")
            continue

        candidates = [
            e for e in candidate_events
            if abs(datetime.fromisoformat(e["datetime_utc"]).date() - event_date) <= DATE_TOLERANCE
        ]
        name_matches = [e for e in candidates if name and normalize_name(e.get("name")) == normalize_name(name)]

        if len(name_matches) == 1:
            matched = name_matches[0]
        elif len(candidates) == 1:
            matched = candidates[0]
        else:
            logger.warning(f"[EVENT MATCH] No unique match for '{name}' ({date_str}), {len(candidates)} candidates")
            continue

        candidate_events.remove(matched)
        current_id = matched.get("ufcstats_id")

        if current_id == ufcstats_id:
            continue

        # Never give one UFCStats event to two Supabase events
        linked_event = event_by_ufcstats_id.get(ufcstats_id)
        if linked_event and linked_event["event_id"] != matched["event_id"]:
            logger.warning(f"[EVENT MATCH] '{name}' ufcstats_id {ufcstats_id} is already linked to event {linked_event['event_id']}, skipping event {matched['event_id']}")
            continue

        if current_id:
            logger.warning(f"[EVENT MATCH] '{name}' event {matched['event_id']} ufcstats_id changed: {current_id} -> {ufcstats_id}")
        else:
            logger.info(f"[EVENT MATCH] '{name}' -> event {matched['event_id']} (ufcstats_id: {ufcstats_id})")

        yield EventItem(
            item_type="event",
            event_id=matched["event_id"],
            ufcstats_id=ufcstats_id,
        )


# ==========================================
# 2. Fight Matching (event details page)
# ==========================================

def _match_participants(ufcstats_fighters: list[tuple[str, str]], participants: list[dict]) -> list[tuple[dict, str]] | None:
    """Pairs both UFCStats fighters with distinct participants.
    A participant with a known ufcstats_id matches only by that ID, otherwise by name."""
    pairs = []
    remaining = list(participants)

    for ufcstats_fighter_id, web_name in ufcstats_fighters:
        for participant in remaining:
            fighter = participant.get("fighters") or {}
            known_id = fighter.get("ufcstats_id")

            if (known_id and known_id == ufcstats_fighter_id) or (not known_id and is_name_match(web_name, fighter.get("name"))):
                pairs.append((participant, ufcstats_fighter_id))
                remaining.remove(participant)
                break
        else:
            return None

    return pairs


def parse_event_fights(response, event_id: str, supabase_fights: list[dict]):
    """Matches UFCStats fights to Supabase fights of the same event by fighter IDs or names.
    Every fight is re-matched on each run, but only changed ufcstats_ids are written."""
    candidate_fights = [
        f for f in supabase_fights
        if (f.get("bout_type") or "").strip().lower() not in CANCELLED_BOUT_TYPES
        and len(f.get("participants") or []) == 2
    ]

    rows = response.css("tr.b-fight-details__table-row[data-link]")
    logger.info(f"[FIGHT MATCH] Event {event_id}: {len(rows)} fights on UFCStats, {len(candidate_fights)} in DB")

    for row in rows:
        ufcstats_fight_id = _extract_id(row.attrib.get("data-link"))
        if not ufcstats_fight_id:
            continue

        ufcstats_fighters = [
            (_extract_id(a.attrib.get("href")), a.css("::text").get(default="").strip())
            for a in row.css("td:nth-child(2) a")
        ]
        if len(ufcstats_fighters) != 2:
            continue

        matches = [
            (fight, pairs) for fight in candidate_fights
            if (pairs := _match_participants(ufcstats_fighters, fight["participants"]))
        ]
        fight_label = " vs ".join(name for _, name in ufcstats_fighters)

        if len(matches) != 1:
            logger.warning(f"[FIGHT MATCH] No unique match for '{fight_label}' in event {event_id} ({len(matches)} candidates)")
            continue

        fight, pairs = matches[0]
        candidate_fights.remove(fight)
        current_id = fight.get("ufcstats_id")

        if current_id != ufcstats_fight_id:
            if current_id:
                logger.warning(f"[FIGHT MATCH] '{fight_label}' fight {fight['fight_id']} ufcstats_id changed: {current_id} -> {ufcstats_fight_id}")
            else:
                logger.info(f"[FIGHT MATCH] '{fight_label}' -> fight {fight['fight_id']} (ufcstats_id: {ufcstats_fight_id})")

            yield FightItem(
                item_type="fight",
                fight_id=fight["fight_id"],
                ufcstats_id=ufcstats_fight_id,
            )

        # Save fighter ufcstats_ids discovered by name, so later matches use IDs
        for participant, ufcstats_fighter_id in pairs:
            if not (participant.get("fighters") or {}).get("ufcstats_id"):
                yield FighterItem(
                    item_type="fighter_update",
                    fighter_id=participant["fighter_id"],
                    ufcstats_id=ufcstats_fighter_id,
                )

    for fight in candidate_fights:
        names = " vs ".join((p.get("fighters") or {}).get("name") or "?" for p in fight["participants"])
        logger.warning(f"[FIGHT MATCH] DB fight {fight['fight_id']} ('{names}') has no UFCStats match in event {event_id} (current ufcstats_id: {fight.get('ufcstats_id')})")
