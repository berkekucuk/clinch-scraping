def determine_fight_result(fighter_div):
    color_map = {
        "text-blue-100": "draw",
        "text-neutral-100": "no_contest",
        "text-green-100": "win",
        "text-red-100": "loss",
    }

    for color_class, result in color_map.items():
        text = fighter_div.css(f"span.{color_class}.font-bold::text").get()
        if text:
            return result

    return "pending"
