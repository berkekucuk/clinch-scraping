import logging
from datetime import date, timedelta
from typing import Callable

from .stats_parser import is_name_match, normalize_name

logger = logging.getLogger(__name__)

CANCELLED_BOUT_TYPES = ("cancelled", "canceled", "fizzled")

# External sources show the local event date, which can differ from the UTC date by a day
DATE_TOLERANCE = timedelta(days=1)


def get_candidate_fights(fights: list[dict]) -> list[dict]:
    """Returns the fights that can be matched: not cancelled and with both participants."""
    return [
        f for f in fights
        if (f.get("bout_type") or "").strip().lower() not in CANCELLED_BOUT_TYPES
        and len(f.get("participants") or []) == 2
    ]


def pick_by_date_and_name(candidates: list, target_date: date, target_name: str | None,
                          get_date: Callable, get_name: Callable) -> tuple[object | None, int]:
    """
    Picks the candidate that matches the target date and name.

    Among candidates within DATE_TOLERANCE of target_date, the one with the same name is picked,
    otherwise the only one in range. Returns (match or None, number of candidates in range).
    """
    in_range = [c for c in candidates if (d := get_date(c)) and abs(d - target_date) <= DATE_TOLERANCE]
    name_matches = [c for c in in_range if target_name and normalize_name(get_name(c)) == normalize_name(target_name)]

    if len(name_matches) == 1:
        return name_matches[0], len(in_range)
    if len(in_range) == 1:
        return in_range[0], len(in_range)
    return None, len(in_range)


def match_participants(external_fighters: list[tuple[str | None, str]], participants: list[dict],
                       fighter_id_field: str | None = None) -> list[dict] | None:
    """
    Pairs external (id, name) fighters, in order, with distinct participants.

    A participant whose fighter has a known fighter_id_field value matches only by that ID,
    otherwise by name. Returns the participants in external fighter order, or None.
    """
    remaining = list(participants)
    mapped = []

    for external_id, name in external_fighters:
        for participant in remaining:
            fighter = participant.get("fighters") or {}
            known_id = fighter.get(fighter_id_field) if fighter_id_field else None

            if (known_id and known_id == external_id) or (not known_id and is_name_match(name, fighter.get("name"))):
                mapped.append(participant)
                remaining.remove(participant)
                break
        else:
            return None

    return mapped


def match_fight(external_fighters: list[tuple[str | None, str]], candidate_fights: list[dict],
                fighter_id_field: str | None = None) -> tuple[dict, list[dict]] | None:
    """
    Matches an external fight to the only Supabase fight with both fighters.

    Returns (fight, participants in external fighter order), or None if no single fight matches.
    """
    if len(external_fighters) != 2:
        return None

    matches = [
        (fight, sides) for fight in candidate_fights
        if (sides := match_participants(external_fighters, fight["participants"], fighter_id_field))
    ]
    return matches[0] if len(matches) == 1 else None


def has_id_changed(log_prefix: str, label: str, entity: str, entity_id: str, field: str,
                   current_id: str | None, new_id: str) -> bool:
    """Returns whether a stored external ID changed and needs to be written, logging the change."""
    if current_id == new_id:
        return False

    if current_id:
        logger.warning(f"{log_prefix} '{label}' {entity} {entity_id} {field} changed: {current_id} -> {new_id}")
    else:
        logger.info(f"{log_prefix} '{label}' -> {entity} {entity_id} ({field}: {new_id})")
    return True


def log_unmatched_fights(log_prefix: str, source: str, event_id: str, fights: list[dict], field: str | None = None):
    """
    Logs a warning for each Supabase fight left without a match in the external source.

    field is the stored external ID column to show, if the source has one.
    """
    for fight in fights:
        names = " vs ".join((p.get("fighters") or {}).get("name") or "?" for p in fight["participants"])
        current = f" (current {field}: {fight.get(field)})" if field else ""
        logger.warning(f"{log_prefix} DB fight {fight['fight_id']} ('{names}') has no {source} match in event {event_id}{current}")
