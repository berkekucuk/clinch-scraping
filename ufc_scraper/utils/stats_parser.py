import unicodedata
from difflib import SequenceMatcher


def parse_landed_attempted(text: str) -> tuple[int, int]:
    """Converts formats like \"15 of 30\" or \"15\" into an (landed, attempted) integer tuple."""
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
    """Converts \"3:45\" format control time into total seconds."""
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


def normalize_name(val: str) -> str:
    """Normalizes fighter names/slugs by removing accents and non-alphanumeric chars."""
    if not val:
        return ""
    val = unicodedata.normalize("NFKD", val).encode("ASCII", "ignore").decode("utf-8")
    return "".join(c for c in val.lower() if c.isalnum())


def is_name_match(name1: str, name2: str, threshold: float = 0.8) -> bool:
    """Performs fuzzy & substring matching between two fighter names."""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    if not n1 or not n2:
        return False
    if n1 == n2 or n1 in n2 or n2 in n1:
        return True
    return SequenceMatcher(None, n1, n2).ratio() >= threshold
