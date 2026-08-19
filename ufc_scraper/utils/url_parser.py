
def extract_event_id(url: str) -> str | None:
    try:
        event_part = url.split("/events/")[1]
        first_part = event_part.split("-")[0]
        event_id = first_part if first_part.isdigit() else event_part
        return event_id.strip().lower()

    except (IndexError, AttributeError):
        return None


def extract_fighter_id(url: str) -> str | None:
    try:
        fighter_part = url.split("/fighters/")[1]
        first_part = fighter_part.split("-")[0]
        fighter_id = first_part if first_part.isdigit() else fighter_part
        return fighter_id.strip().lower()

    except (IndexError, AttributeError):
        return None


def extract_fight_id(url: str) -> str | None:
    try:
        fight_part = url.split("/bouts/")[1]
        first_part = fight_part.split("-")[0]
        fight_id = first_part if first_part.isdigit() else fight_part
        return fight_id.strip().lower()

    except (IndexError, AttributeError):
        return None


def extract_country_code(url: str) -> str | None:
    if not url:
        return None

    filename = url.split('/')[-1]
    country_code = filename.split('-')[0]
    return country_code
