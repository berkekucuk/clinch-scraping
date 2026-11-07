import re
import scrapy


def parse_odds(bout_details_div):

    table = bout_details_div.css("table#boutComparisonTable")
    odds_row = table.xpath(".//tr[td[contains(., 'Betting Odds')]]").get()

    if odds_row:
        row_sel = scrapy.Selector(text=odds_row)
        odds_texts = row_sel.css("div.hidden.md\\:inline::text").getall()
        odds_texts = [o.strip() for o in odds_texts if o.strip()]

        fighter1_odds = odds_texts[0] if len(odds_texts) > 0 else None
        fighter2_odds = odds_texts[1] if len(odds_texts) > 1 else None

        f1_parsed = split_odds(fighter1_odds)
        f2_parsed = split_odds(fighter2_odds)

        f1_fair, f2_fair = calculate_fair_odds(f1_parsed["odds_value"], f2_parsed["odds_value"])

        return {
            "fighter1_odds_value": f1_fair,
            "fighter1_raw_odds_value": f1_parsed["odds_value"],
            "fighter1_odds_label": f1_parsed["odds_label"],
            "fighter2_odds_value": f2_fair,
            "fighter2_raw_odds_value": f2_parsed["odds_value"],
            "fighter2_odds_label": f2_parsed["odds_label"],
        }
    else:
        return {
            "fighter1_odds_value": None,
            "fighter1_raw_odds_value": None,
            "fighter1_odds_label": None,
            "fighter2_odds_value": None,
            "fighter2_raw_odds_value": None,
            "fighter2_odds_label": None,
        }


def american_to_probability(odds: int) -> float:
    """-230 → 0.697, +190 → 0.345"""
    if odds < 0:
        return -odds / (-odds + 100)
    return 100 / (odds + 100)


def probability_to_american(probability: float) -> int:
    """0.669 → -200, 0.331 → +200 (rounded to the nearest 5)"""
    if probability > 0.5:
        odds = -100 * probability / (1 - probability)
    else:
        odds = 100 * (1 - probability) / probability
    return int(round(odds / 5) * 5)


def calculate_fair_odds(odds1: int | None, odds2: int | None) -> tuple[int | None, int | None]:
    """
    Removes the bookmaker margin so both probabilities add up to 100%.
    (-230, +190) → (-200, +200)
    """
    if odds1 is None or odds2 is None or odds1 == 0 or odds2 == 0:
        return None, None

    p1 = american_to_probability(odds1)
    p2 = american_to_probability(odds2)
    total = p1 + p2

    return probability_to_american(p1 / total), probability_to_american(p2 / total)


def split_odds(odds_str: str | None) -> dict:
    """
    '-350 (Moderate Favorite)' → {'odds_value': -350, 'odds_label': 'Moderate Favorite'}
    '+390 (Moderate Underdog)' → {'odds_value': 390, 'odds_label': 'Moderate Underdog'}
    """
    if not odds_str or not isinstance(odds_str, str):
        return {"odds_value": None, "odds_label": None}

    odds_str = odds_str.strip()

    match = re.match(r"([+-]?\d+)\s*\(([^)]+)\)", odds_str)
    if match:
        value = int(match.group(1))
        label = match.group(2).strip()
        return {"odds_value": value, "odds_label": label}

    try:
        value = int(odds_str)
        return {"odds_value": value, "odds_label": None}
    except ValueError:
        return {"odds_value": None, "odds_label": odds_str}
