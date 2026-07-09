from config.cities.bangalore import BANGALORE
from config.cities.chennai import CHENNAI
from config.cities.hyderabad import HYDERABAD
from config.cities.mumbai import MUMBAI
from config.cities.pune import PUNE

CITIES = {
    "pune": PUNE,
    "mumbai": MUMBAI,
    "bangalore": BANGALORE,
    "hyderabad": HYDERABAD,
    "chennai": CHENNAI,
}


def get_city_config(city_id: str):
    key = city_id.strip().lower()
    if key not in CITIES:
        available = ", ".join(sorted(CITIES))
        raise ValueError(f"Unknown city '{city_id}'. Available: {available}")
    return CITIES[key]
