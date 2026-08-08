def parse_status(status_string: str) -> str | None:

    if not status_string:
        return None

    return status_string.split()[0]
