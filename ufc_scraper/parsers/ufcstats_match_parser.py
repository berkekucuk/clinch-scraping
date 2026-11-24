import logging
from datetime import datetime
from ..items import EventItem, FightItem, FighterItem
from ..utils.matching import get_candidate_fights, has_id_changed, log_unmatched_fights, match_fight, pick_by_date_and_name

logger = logging.getLogger(__name__)


def _extract_id(url: str | None) -> str | None:
    return url.rstrip("/").split("/")[-1] if url else None


def parse_upcoming_events(response, supabase_events: list[dict]):
    """
    Matches UFCStats upcoming events to Supabase events and yields their ufcstats_ids.

    Events are matched by date, using the name as a tiebreaker. Every event is re-matched
    on each run, but only changed ufcstats_ids are written.
    """
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

        matched, candidate_count = pick_by_date_and_name(
            candidate_events, event_date, name,
            get_date=lambda e: datetime.fromisoformat(e["datetime_utc"]).date(),
            get_name=lambda e: e.get("name"),
        )
        if not matched:
            logger.warning(f"[EVENT MATCH] No unique match for '{name}' ({date_str}), {candidate_count} candidates")
            continue

        candidate_events.remove(matched)

        # Never give one UFCStats event to two Supabase events
        linked_event = event_by_ufcstats_id.get(ufcstats_id)
        if linked_event and linked_event["event_id"] != matched["event_id"]:
            logger.warning(f"[EVENT MATCH] '{name}' ufcstats_id {ufcstats_id} is already linked to event {linked_event['event_id']}, skipping event {matched['event_id']}")
            continue

        if has_id_changed("[EVENT MATCH]", name, "event", matched["event_id"], "ufcstats_id", matched.get("ufcstats_id"), ufcstats_id):
            yield EventItem(
                item_type="event",
                event_id=matched["event_id"],
                ufcstats_id=ufcstats_id,
            )


def parse_event_fights(response, event_id: str, supabase_fights: list[dict]):
    """
    Matches UFCStats fights to Supabase fights of the same event and yields their ufcstats_ids.

    Fights are matched by fighter IDs or names. Every fight is re-matched on each run,
    but only changed ufcstats_ids are written.
    """
    candidate_fights = get_candidate_fights(supabase_fights)

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
        fight_label = " vs ".join(name for _, name in ufcstats_fighters)

        matched = match_fight(ufcstats_fighters, candidate_fights, fighter_id_field="ufcstats_id")
        if not matched:
            logger.warning(f"[FIGHT MATCH] No unique match for '{fight_label}' in event {event_id}")
            continue

        fight, sides = matched
        candidate_fights.remove(fight)

        if has_id_changed("[FIGHT MATCH]", fight_label, "fight", fight["fight_id"], "ufcstats_id", fight.get("ufcstats_id"), ufcstats_fight_id):
            yield FightItem(
                item_type="fight",
                fight_id=fight["fight_id"],
                ufcstats_id=ufcstats_fight_id,
            )

        # Save fighter ufcstats_ids discovered by name, so later matches use IDs
        for participant, (ufcstats_fighter_id, _) in zip(sides, ufcstats_fighters):
            if not (participant.get("fighters") or {}).get("ufcstats_id"):
                yield FighterItem(
                    item_type="fighter_update",
                    fighter_id=participant["fighter_id"],
                    ufcstats_id=ufcstats_fighter_id,
                )

    log_unmatched_fights("[FIGHT MATCH]", "UFCStats", event_id, candidate_fights, "ufcstats_id")
