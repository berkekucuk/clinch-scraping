def map_weight_class(value):
    if value is None:
        return None

    if isinstance(value, str) and value.isdigit():
        value = int(value)

    if isinstance(value, int):
        int_mapping = {
            115: "SW",
            125: "FLW",
            135: "BW",
            145: "FW",
            155: "LW",
            170: "WW",
            185: "MW",
            205: "LHW",
            265: "HW"
        }
        return int_mapping.get(value, "CW")

    elif isinstance(value, str):
        normalized = value.lower().strip()

        str_mapping = {
            "strawweight": "SW", "straw weight": "SW",
            "flyweight": "FLW", "fly weight": "FLW",
            "bantamweight": "BW", "bantam weight": "BW",
            "featherweight": "FW", "feather weight": "FW",
            "lightweight": "LW", "light weight": "LW",
            "welterweight": "WW", "welter weight": "WW",
            "middleweight": "MW", "middle weight": "MW",
            "light heavyweight": "LHW", "lightheavyweight": "LHW",
            "light-heavyweight": "LHW", "lt. heavyweight": "LHW", "lt heavyweight": "LHW",
            "heavyweight": "HW", "heavy weight": "HW"
        }

        return str_mapping.get(normalized, None)

    return None
