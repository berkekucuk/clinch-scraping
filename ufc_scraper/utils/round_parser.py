import re


def standardize_round_summary(round_summary_str: str) -> str:
    if not round_summary_str:
        return None

    text = round_summary_str.strip()

    match_time_first = re.search(r'^(\d{1,2}:\d{2})\s+Round\s+(\d+)', text, re.IGNORECASE)
    if match_time_first:
        time_str = match_time_first.group(1)
        round_num = match_time_first.group(2)
        return f"R{round_num} {time_str}"

    match_decision = re.search(r'^(\d+)\s+Rounds?', text, re.IGNORECASE)
    if match_decision:
        round_num = match_decision.group(1)
        return f"R{round_num} 5:00"

    match_no_time = re.search(r'^Round\s+(\d+)\s+of', text, re.IGNORECASE)
    if match_no_time:
        round_num = match_no_time.group(1)
        return f"R{round_num} 0:00"

    return text
