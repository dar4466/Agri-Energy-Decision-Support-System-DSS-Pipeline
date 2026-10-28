import json
import logging
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

NASA_URL = (
    "https://power.larc.nasa.gov/api/temporal/climatology/point"
    "?parameters=ALLSKY_SFC_SW_DWN&community=AG&longitude={lon}&latitude={lat}&format=JSON"
)
MONTHS = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
]
MJ_PER_KWH = 3.6  # 1 kWh = 3.6 MJ


def fetch_nasa_solar(lat: float, lon: float) -> dict:
    """Get NASA POWER solar climatology for (lat, lon) as a dict.

    Cached as a JSON file in ./data/.cache, so later runs for the same location don't
    call the API again (climatology is a long-term average; it doesn't change).
    """
    file_path = Path("data/.cache") / f"nasa_solar_{lat:.4f}_{lon:.4f}.json"

    if file_path.exists():
        logger.info(f"Using cached NASA data from {file_path}.")
        return json.loads(file_path.read_text())

    url = NASA_URL.format(lat=f"{lat:.4f}", lon=f"{lon:.4f}")
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.load(response)
    except Exception as e:  # no internet, timeout, server error, or not valid JSON
        raise RuntimeError(f"NASA POWER request failed: {e}") from e

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data))
    logger.info(f"NASA data downloaded and cached to {file_path}.")
    return data


def solar_peak_hours(data: dict) -> dict:
    """Extract Peak Sun Hours (kWh/m²/day) from a NASA POWER response.

    Returns the lowest month (the PDF's "design month", the worst case the system must
    still work in) and the annual average PSH.
    """
    # Pick the values out of the JSON; fail clearly if NASA returned an error instead
    try:
        values = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
        monthly = {month: values[month] for month in MONTHS}
        annual = values["ANN"]
    except (KeyError, TypeError) as e:
        raise RuntimeError(f"Unexpected NASA POWER response, missing key: {e}") from e

    # NASA writes -999 when it has no data; it would wrongly become the lowest month
    if -999 in monthly.values() or annual == -999:
        raise RuntimeError("NASA POWER has no solar data for this location (-999 values).")

    # NASA gives MJ/m²/day; PSH is kWh/m²/day (1 kWh = 3.6 MJ)
    lowest_month = min(monthly, key=monthly.get)  # month with the least sun
    return {
        "lowest_month": lowest_month,
        "lowest_psh": monthly[lowest_month] / MJ_PER_KWH,
        "avg_psh": annual / MJ_PER_KWH,
    }
