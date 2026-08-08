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

        return {
            "fighter1_odds_value": f1_parsed["odds_value"],
            "fighter1_odds_label": f1_parsed["odds_label"],
            "fighter2_odds_value": f2_parsed["odds_value"],
            "fighter2_odds_label": f2_parsed["odds_label"],
        }
    else:
        return {
            "fighter1_odds_value": None,
            "fighter1_odds_label": None,
            "fighter2_odds_value": None,
            "fighter2_odds_label": None,
        }


def split_odds(odds_str: str) -> dict:
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
