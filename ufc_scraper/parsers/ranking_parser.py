import logging
from ..utils.ranking_mappings import WEIGHT_CLASS_MAPPING
from ..items import RankingItem

logger = logging.getLogger(__name__)

P4P_TITLES = ("Men's Pound-for-Pound", "Women's Pound-for-Pound")


def _get_ranking_groups(response) -> list:
    """Pound-for-pound groups from the media rankings, division groups from the meta rankings."""
    media_groups = response.css('.block-views-blockathlete-rankings-block-1 .view-grouping')
    meta_groups = response.css('.block-views-blockathlete-rankings-meta-rankings .view-grouping')

    if not meta_groups:
        logger.error("Meta rankings block not found on rankings page")

    return [g for g in media_groups if _get_group_title(g) in P4P_TITLES] + list(meta_groups)


def extract_ufc_slugs(response) -> list[str]:
    """Returns the UFC.com slugs of every ranked fighter on the page."""
    slugs = {
        _get_ufc_slug(href)
        for group in _get_ranking_groups(response)
        for href in group.css('.info h5 a::attr(href), .views-field-title a::attr(href)').getall()
    }
    return sorted(slug for slug in slugs if slug)


def parse_rankings(response, fighter_ids: dict[str, str]):
    """Yields a RankingItem for each ranked fighter. fighter_ids maps ufc_slug to fighter_id."""
    for group in _get_ranking_groups(response):
        yield from _parse_group(group, fighter_ids)


def _get_ufc_slug(href: str | None) -> str | None:
    return href.rstrip("/").split("/")[-1] if href and "/athlete/" in href else None


def _get_group_title(group):
    raw_title = group.css('.view-grouping-header::text').get()
    return raw_title.strip() if raw_title else None


def _parse_group(group, fighter_ids):
    title = _get_group_title(group)
    if not title:
        return

    db_weight_class_id = WEIGHT_CLASS_MAPPING.get(title)

    if not db_weight_class_id:
        logger.warning(f"Weight class not matched: {title}")
        return

    champion_link = group.css('.info h5 a')
    if champion_link:
        item = _process_fighter(champion_link[0], db_weight_class_id, 0, 0, fighter_ids)
        if item:
            yield item

    rows = group.css('tbody tr')
    current_rank = 1

    for row in rows:
        fighter_link = row.css('.views-field-title a')

        rank_change = 0
        rank_change_td = row.css('.views-field-meta-weight-class-rank-change, .views-field-weight-class-rank-change')
        if rank_change_td:
            change_texts = rank_change_td.xpath('./text()').getall()
            change_text = "".join(change_texts).strip().replace('"', '')
            change_span_class = rank_change_td.css('span::attr(class)').get()

            if change_span_class and 'not-ranked' in change_span_class:
                rank_change = None
            elif change_text and change_span_class:
                try:
                    change_val = int(change_text)
                    if 'increase' in change_span_class:
                        rank_change = change_val
                    elif 'decrease' in change_span_class:
                        rank_change = -change_val
                except ValueError:
                    pass

        if fighter_link:
            item = _process_fighter(fighter_link[0], db_weight_class_id, current_rank, rank_change, fighter_ids)
            if item:
                yield item
            current_rank += 1


def _process_fighter(fighter_link, weight_class_id, rank, rank_change, fighter_ids):
    if rank == 0 and weight_class_id in ["mens_p4p", "womens_p4p"]:
        return None

    fighter_name = fighter_link.css('::text').get(default="").strip()
    ufc_slug = _get_ufc_slug(fighter_link.attrib.get("href"))
    found_id = fighter_ids.get(ufc_slug)

    if found_id:
        return RankingItem(
            item_type="ranking",
            weight_class_id=weight_class_id,
            fighter_id=found_id,
            rank_number=rank,
            rank_change=rank_change,
        )
    else:
        logger.error(f"Fighter not found in DB: {fighter_name} (ufc_slug: {ufc_slug})")
        return None
