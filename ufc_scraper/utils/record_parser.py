import re


def parse_record(record_str):

    if not record_str or record_str.strip() == "" or record_str == "N/A":
        return {"wins": 0, "losses": 0, "draws": 0}

    cleaned = record_str.split(',')[0].split("(")[0].strip()

    match = re.match(r'(\d+)-(\d+)-?(\d+)?', cleaned)

    if not match:
        return {"wins": 0, "losses": 0, "draws": 0}

    wins = int(match.group(1))
    losses = int(match.group(2))
    draws = int(match.group(3)) if match.group(3) else 0

    return {"wins": wins, "losses": losses, "draws": draws}
