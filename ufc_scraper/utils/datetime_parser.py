from dateutil import parser
from zoneinfo import ZoneInfo
import logging


def parse_datetime(date_time_str: str) -> str | None:

    if not date_time_str:
        return None

    try:
        eastern = ZoneInfo("America/New_York")

        tzinfos = {"ET": eastern}

        dt = parser.parse(date_time_str, fuzzy=True, tzinfos=tzinfos)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=eastern)
        else:
            dt = dt.astimezone(eastern)

        dt_utc = dt.astimezone(ZoneInfo("UTC"))
        return dt_utc.isoformat()

    except Exception as e:
        logging.error(f"'{date_time_str}' An error occurred while parsing: {e}")
        return None
