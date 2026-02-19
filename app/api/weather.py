import time
import xml.etree.ElementTree as ET

import requests
from flask import jsonify

from app import app

FMI_URL = (
    "https://opendata.fmi.fi/wfs?service=WFS&version=2.0.0"
    "&request=GetFeature"
    "&storedquery_id=fmi::observations::weather::timevaluepair"
    "&fmisid=100968"
    "&parameters=t2m,ws_10min,wawa"
    "&timestep=10"
    "&maxlocations=1"
)

_cache = {"data": None, "ts": 0}
CACHE_TTL = 600  # 10 minutes

# WMO code table 4680 — present weather from automatic stations
WAWA_MAP = {
    0: ("Clear", "Selkeä"),
    (1, 3): ("Partly cloudy", "Puolipilvistä"),
    (4, 5): ("Haze", "Utua"),
    10: ("Mist", "Sumua"),
    11: ("Diamond dust", "Timanttipölyä"),
    12: ("Distant lightning", "Salamointia"),
    18: ("Squalls", "Puuskia"),
    20: ("Fog recently", "Sumua aiemmin"),
    21: ("Precipitation recently", "Sadetta aiemmin"),
    22: ("Drizzle recently", "Tihkua aiemmin"),
    23: ("Rain recently", "Sadetta aiemmin"),
    24: ("Snow recently", "Lumisadetta aiemmin"),
    25: ("Freezing rain recently", "Jäätävää sadetta aiemmin"),
    26: ("Thunderstorm recently", "Ukkosta aiemmin"),
    (27, 29): ("Blowing snow", "Tuiskua"),
    (30, 35): ("Fog", "Sumua"),
    (40, 49): ("Precipitation", "Sadetta"),
    (50, 53): ("Drizzle", "Tihkusadetta"),
    (54, 56): ("Freezing drizzle", "Jäätävää tihkua"),
    (57, 58): ("Drizzle and rain", "Tihkua ja sadetta"),
    60: ("Rain", "Sadetta"),
    (61, 63): ("Rain", "Sadetta"),
    (64, 66): ("Freezing rain", "Jäätävää sadetta"),
    (67, 68): ("Rain and snow", "Räntää"),
    70: ("Snow", "Lumisadetta"),
    (71, 73): ("Snow", "Lumisadetta"),
    (74, 76): ("Ice pellets", "Jääjyväsiä"),
    77: ("Snow grains", "Lumijyväsiä"),
    78: ("Ice crystals", "Jääkiteitä"),
    (80, 84): ("Rain showers", "Sadekuuroja"),
    (85, 87): ("Snow showers", "Lumikuuroja"),
    89: ("Hail", "Rakeita"),
    (90, 96): ("Thunderstorm", "Ukkosta"),
    99: ("Tornado", "Tornado"),
}


def _wawa_to_condition(code):
    if code is None:
        return "N/A", "N/A"
    code = int(code)
    for key, val in WAWA_MAP.items():
        if isinstance(key, int) and code == key:
            return val
        if isinstance(key, tuple) and key[0] <= code <= key[1]:
            return val
    return "N/A", "N/A"


def _wind_chill(temp, wind_ms):
    if temp is None or wind_ms is None:
        return temp
    wind_kmh = wind_ms * 3.6
    if temp <= 10 and wind_kmh > 4.8:
        wc = (
            13.12
            + 0.6215 * temp
            - 11.37 * wind_kmh**0.16
            + 0.3965 * temp * wind_kmh**0.16
        )
        return round(wc, 1)
    return temp


def _extract_param_name(href):
    """Extract parameter name from observedProperty href.

    FMI uses query-string style hrefs like:
      https://opendata.fmi.fi/meta?observableProperty=observation&param=t2m&language=eng
    """
    if "param=" in href:
        after = href.split("param=", 1)[1]
        return after.split("&", 1)[0]
    if "/" in href:
        return href.rsplit("/", 1)[-1]
    return ""


def _parse_fmi_xml(xml_text):
    ns = {
        "wfs": "http://www.opengis.net/wfs/2.0",
        "om": "http://www.opengis.net/om/2.0",
        "omso": "http://inspire.ec.europa.eu/schemas/omso/3.0",
        "wml2": "http://www.opengis.net/waterml/2.0",
        "gml": "http://www.opengis.net/gml/3.2",
    }
    root = ET.fromstring(xml_text)

    results = {}
    for obs in root.findall(".//omso:PointTimeSeriesObservation", ns):
        param_link = obs.find(".//om:observedProperty", ns)
        if param_link is None:
            continue
        href = param_link.get(
            "{http://www.w3.org/1999/xlink}href", ""
        )
        param_name = _extract_param_name(href)
        if not param_name:
            continue

        points = obs.findall(
            ".//wml2:MeasurementTimeseries/wml2:point/wml2:MeasurementTVP", ns
        )
        # Walk backwards to find the most recent non-NaN value
        for point in reversed(points):
            value_el = point.find("wml2:value", ns)
            if value_el is not None and value_el.text and value_el.text.strip() != "NaN":
                time_el = point.find("wml2:time", ns)
                results[param_name] = {
                    "value": float(value_el.text),
                    "time": time_el.text.strip() if time_el is not None and time_el.text else None,
                }
                break

    return results


def _fetch_weather():
    now = time.time()
    if _cache["data"] and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]

    resp = requests.get(FMI_URL, timeout=10)
    resp.raise_for_status()
    parsed = _parse_fmi_xml(resp.text)

    temp = parsed.get("t2m", {}).get("value")
    wind = parsed.get("ws_10min", {}).get("value")
    wawa = parsed.get("wawa", {}).get("value")
    timestamp = (
        parsed.get("t2m", {}).get("time")
        or parsed.get("ws_10min", {}).get("time")
    )

    condition_en, condition_fi = _wawa_to_condition(wawa)
    feels_like = _wind_chill(temp, wind)

    data = {
        "temperature": temp,
        "feels_like": feels_like,
        "wind_speed": wind,
        "condition": condition_en,
        "condition_fi": condition_fi,
        "station": "Vantaa",
        "wawa_code": int(wawa) if wawa is not None else None,
        "timestamp": timestamp,
    }
    _cache["data"] = data
    _cache["ts"] = now
    return data


@app.route("/api/weather")
def weather_route():
    try:
        data = _fetch_weather()
        return jsonify(data)
    except Exception as e:
        if _cache["data"]:
            return jsonify(_cache["data"])
        return jsonify({"error": str(e)}), 502
