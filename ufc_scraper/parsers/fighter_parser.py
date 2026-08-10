from urllib.parse import urljoin
from ..utils.date_parser import parse_date_to_iso
from ..utils.record_parser import parse_record
from ..utils.url_parser import extract_country_code
from ..utils.measurement_parser import parse_measurement
from ..utils.weight_class_mapper import map_weight_class
from ..utils.fighter_detail_extractor import extract_detail, extract_reach
from ..utils.item_factory import create_fighter_update_item


def parse_fighter_profile(response, fighter_id):
    header = response.css("div#fighterPageHeader")
    container = response.css("div#standardDetails")

    nickname = extract_detail(container, "Nickname:")

    record_str = extract_detail(container, "Pro MMA Record:")
    record = parse_record(record_str)

    date_of_birth_str = extract_detail(container, "Date of Birth:")
    date_of_birth = parse_date_to_iso(date_of_birth_str)

    height_str = extract_detail(container, "Height:")
    height = parse_measurement(height_str)

    reach_str = extract_reach(container)
    reach = parse_measurement(reach_str)

    weight_class_name = extract_detail(container, "Weight Class:")
    weight_class_id = map_weight_class(weight_class_name)

    born = extract_detail(container, "Born:")
    fighting_out_of = extract_detail(container, "Fighting out of:")
    style = extract_detail(container, "Foundation Style:")

    country_flag_relative_url = header.css("img::attr(src)").get(default="").strip() or None
    country_flag_url = urljoin("https://www.tapology.com", country_flag_relative_url) if country_flag_relative_url else None
    country_code = extract_country_code(country_flag_url) if country_flag_url else None

    return create_fighter_update_item(
        fighter_id=fighter_id,
        nickname=nickname,
        record=record,
        date_of_birth=date_of_birth,
        height=height,
        reach=reach,
        weight_class_id=weight_class_id,
        born=born,
        fighting_out_of=fighting_out_of,
        style=style,
        country_code=country_code,
    )
