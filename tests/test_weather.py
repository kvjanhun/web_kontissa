from unittest.mock import patch, MagicMock

import pytest

from app.api.weather import (
    _wawa_to_condition,
    _wind_chill,
    _parse_fmi_xml,
    _extract_param_name,
    _cache,
)

# Minimal FMI WFS XML matching the real response structure.
# Uses omso:PointTimeSeriesObservation and query-string style hrefs,
# as returned by the actual FMI open data API.
SAMPLE_FMI_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<wfs:FeatureCollection
    xmlns:wfs="http://www.opengis.net/wfs/2.0"
    xmlns:om="http://www.opengis.net/om/2.0"
    xmlns:omso="http://inspire.ec.europa.eu/schemas/omso/3.0"
    xmlns:wml2="http://www.opengis.net/waterml/2.0"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:gml="http://www.opengis.net/gml/3.2">
  <wfs:member>
    <omso:PointTimeSeriesObservation gml:id="obs-1">
      <om:observedProperty xlink:href="https://opendata.fmi.fi/meta?observableProperty=observation&amp;param=t2m&amp;language=eng"/>
      <om:result>
        <wml2:MeasurementTimeseries gml:id="obs-obs-1-1-t2m">
          <wml2:point><wml2:MeasurementTVP>
            <wml2:time>2026-02-19T18:50:00Z</wml2:time>
            <wml2:value>-5.3</wml2:value>
          </wml2:MeasurementTVP></wml2:point>
          <wml2:point><wml2:MeasurementTVP>
            <wml2:time>2026-02-19T19:00:00Z</wml2:time>
            <wml2:value>-6.1</wml2:value>
          </wml2:MeasurementTVP></wml2:point>
        </wml2:MeasurementTimeseries>
      </om:result>
    </omso:PointTimeSeriesObservation>
  </wfs:member>
  <wfs:member>
    <omso:PointTimeSeriesObservation gml:id="obs-2">
      <om:observedProperty xlink:href="https://opendata.fmi.fi/meta?observableProperty=observation&amp;param=ws_10min&amp;language=eng"/>
      <om:result>
        <wml2:MeasurementTimeseries gml:id="obs-obs-1-1-ws_10min">
          <wml2:point><wml2:MeasurementTVP>
            <wml2:time>2026-02-19T19:00:00Z</wml2:time>
            <wml2:value>3.2</wml2:value>
          </wml2:MeasurementTVP></wml2:point>
        </wml2:MeasurementTimeseries>
      </om:result>
    </omso:PointTimeSeriesObservation>
  </wfs:member>
  <wfs:member>
    <omso:PointTimeSeriesObservation gml:id="obs-3">
      <om:observedProperty xlink:href="https://opendata.fmi.fi/meta?observableProperty=observation&amp;param=wawa&amp;language=eng"/>
      <om:result>
        <wml2:MeasurementTimeseries gml:id="obs-obs-1-1-wawa">
          <wml2:point><wml2:MeasurementTVP>
            <wml2:time>2026-02-19T19:00:00Z</wml2:time>
            <wml2:value>71</wml2:value>
          </wml2:MeasurementTVP></wml2:point>
        </wml2:MeasurementTimeseries>
      </om:result>
    </omso:PointTimeSeriesObservation>
  </wfs:member>
</wfs:FeatureCollection>
"""

# Same structure but with NaN values (happens when sensor is offline)
NAN_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<wfs:FeatureCollection
    xmlns:wfs="http://www.opengis.net/wfs/2.0"
    xmlns:om="http://www.opengis.net/om/2.0"
    xmlns:omso="http://inspire.ec.europa.eu/schemas/omso/3.0"
    xmlns:wml2="http://www.opengis.net/waterml/2.0"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:gml="http://www.opengis.net/gml/3.2">
  <wfs:member>
    <omso:PointTimeSeriesObservation gml:id="obs-1">
      <om:observedProperty xlink:href="https://opendata.fmi.fi/meta?observableProperty=observation&amp;param=t2m&amp;language=eng"/>
      <om:result>
        <wml2:MeasurementTimeseries gml:id="obs-obs-1-1-t2m">
          <wml2:point><wml2:MeasurementTVP>
            <wml2:time>2026-02-19T19:00:00Z</wml2:time>
            <wml2:value>NaN</wml2:value>
          </wml2:MeasurementTVP></wml2:point>
        </wml2:MeasurementTimeseries>
      </om:result>
    </omso:PointTimeSeriesObservation>
  </wfs:member>
</wfs:FeatureCollection>
"""

# Latest value is NaN but earlier values are valid (common for wawa)
NAN_TRAILING_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<wfs:FeatureCollection
    xmlns:wfs="http://www.opengis.net/wfs/2.0"
    xmlns:om="http://www.opengis.net/om/2.0"
    xmlns:omso="http://inspire.ec.europa.eu/schemas/omso/3.0"
    xmlns:wml2="http://www.opengis.net/waterml/2.0"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:gml="http://www.opengis.net/gml/3.2">
  <wfs:member>
    <omso:PointTimeSeriesObservation gml:id="obs-1">
      <om:observedProperty xlink:href="https://opendata.fmi.fi/meta?observableProperty=observation&amp;param=wawa&amp;language=eng"/>
      <om:result>
        <wml2:MeasurementTimeseries gml:id="obs-obs-1-1-wawa">
          <wml2:point><wml2:MeasurementTVP>
            <wml2:time>2026-02-19T19:20:00Z</wml2:time>
            <wml2:value>24.0</wml2:value>
          </wml2:MeasurementTVP></wml2:point>
          <wml2:point><wml2:MeasurementTVP>
            <wml2:time>2026-02-19T19:30:00Z</wml2:time>
            <wml2:value>NaN</wml2:value>
          </wml2:MeasurementTVP></wml2:point>
        </wml2:MeasurementTimeseries>
      </om:result>
    </omso:PointTimeSeriesObservation>
  </wfs:member>
</wfs:FeatureCollection>
"""


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the module-level cache before each test."""
    _cache["data"] = None
    _cache["ts"] = 0
    yield
    _cache["data"] = None
    _cache["ts"] = 0


class TestExtractParamName:
    def test_query_string_href(self):
        href = "https://opendata.fmi.fi/meta?observableProperty=observation&param=t2m&language=eng"
        assert _extract_param_name(href) == "t2m"

    def test_query_string_param_last(self):
        href = "https://opendata.fmi.fi/meta?observableProperty=observation&param=ws_10min"
        assert _extract_param_name(href) == "ws_10min"

    def test_path_style_href(self):
        assert _extract_param_name("https://opendata.fmi.fi/meta/param/t2m") == "t2m"

    def test_empty_string(self):
        assert _extract_param_name("") == ""


class TestWawaToCondition:
    def test_clear(self):
        assert _wawa_to_condition(0) == ("Clear", "Selkeä")

    def test_partly_cloudy_range(self):
        for code in (1, 2, 3):
            assert _wawa_to_condition(code) == ("Partly cloudy", "Puolipilvistä")

    def test_haze(self):
        assert _wawa_to_condition(4) == ("Haze", "Utua")
        assert _wawa_to_condition(5) == ("Haze", "Utua")

    def test_mist(self):
        assert _wawa_to_condition(10) == ("Mist", "Sumua")

    def test_fog_range(self):
        assert _wawa_to_condition(30) == ("Fog", "Sumua")
        assert _wawa_to_condition(34) == ("Fog", "Sumua")

    def test_code_21_precipitation_recently(self):
        assert _wawa_to_condition(21) == ("Precipitation recently", "Sadetta aiemmin")

    def test_code_24_snow_recently(self):
        assert _wawa_to_condition(24) == ("Snow recently", "Lumisadetta aiemmin")

    def test_code_25_freezing_rain_recently(self):
        assert _wawa_to_condition(25) == ("Freezing rain recently", "Jäätävää sadetta aiemmin")

    def test_drizzle(self):
        assert _wawa_to_condition(51) == ("Drizzle", "Tihkusadetta")

    def test_freezing_drizzle(self):
        assert _wawa_to_condition(55) == ("Freezing drizzle", "Jäätävää tihkua")

    def test_rain(self):
        assert _wawa_to_condition(61) == ("Rain", "Sadetta")

    def test_freezing_rain(self):
        assert _wawa_to_condition(64) == ("Freezing rain", "Jäätävää sadetta")

    def test_rain_and_snow(self):
        assert _wawa_to_condition(67) == ("Rain and snow", "Räntää")

    def test_snow(self):
        assert _wawa_to_condition(71) == ("Snow", "Lumisadetta")

    def test_rain_showers(self):
        assert _wawa_to_condition(81) == ("Rain showers", "Sadekuuroja")

    def test_snow_showers(self):
        assert _wawa_to_condition(86) == ("Snow showers", "Lumikuuroja")

    def test_thunderstorm(self):
        assert _wawa_to_condition(91) == ("Thunderstorm", "Ukkosta")

    def test_tornado(self):
        assert _wawa_to_condition(99) == ("Tornado", "Tornado")

    def test_none(self):
        assert _wawa_to_condition(None) == ("N/A", "N/A")

    def test_unknown_code(self):
        assert _wawa_to_condition(7) == ("N/A", "N/A")

    def test_float_code_truncated(self):
        assert _wawa_to_condition(71.0) == ("Snow", "Lumisadetta")


class TestWindChill:
    def test_cold_windy(self):
        # -10°C, 5 m/s (18 km/h) → should apply formula
        result = _wind_chill(-10, 5)
        assert result < -10
        assert isinstance(result, float)

    def test_warm_no_chill(self):
        # 15°C → above 10°C threshold, returns temp as-is
        assert _wind_chill(15, 5) == 15

    def test_low_wind_no_chill(self):
        # -10°C, 1 m/s (3.6 km/h) → below 4.8 km/h threshold
        assert _wind_chill(-10, 1) == -10

    def test_none_temp(self):
        assert _wind_chill(None, 5) is None

    def test_none_wind(self):
        assert _wind_chill(-5, None) == -5

    def test_boundary_temp_10(self):
        # Exactly 10°C with enough wind → formula applies
        result = _wind_chill(10, 5)
        assert isinstance(result, float)

    def test_known_value(self):
        # -20°C, 30 km/h wind (8.33 m/s)
        # WC = 13.12 + 0.6215*(-20) - 11.37*(30^0.16) + 0.3965*(-20)*(30^0.16)
        result = _wind_chill(-20, 8.33)
        assert -35 < result < -25  # rough sanity check


class TestParseFmiXml:
    def test_parses_all_parameters(self):
        result = _parse_fmi_xml(SAMPLE_FMI_XML)
        assert "t2m" in result
        assert "ws_10min" in result
        assert "wawa" in result

    def test_takes_last_measurement(self):
        result = _parse_fmi_xml(SAMPLE_FMI_XML)
        # t2m has two points; should pick the last one (-6.1)
        assert result["t2m"]["value"] == -6.1
        assert result["t2m"]["time"] == "2026-02-19T19:00:00Z"

    def test_correct_values(self):
        result = _parse_fmi_xml(SAMPLE_FMI_XML)
        assert result["ws_10min"]["value"] == 3.2
        assert result["wawa"]["value"] == 71.0

    def test_nan_values_skipped(self):
        result = _parse_fmi_xml(NAN_XML)
        assert "t2m" not in result

    def test_nan_trailing_falls_back_to_previous(self):
        result = _parse_fmi_xml(NAN_TRAILING_XML)
        assert "wawa" in result
        assert result["wawa"]["value"] == 24.0
        assert result["wawa"]["time"] == "2026-02-19T19:20:00Z"

    def test_empty_collection(self):
        xml = (
            '<?xml version="1.0"?>'
            '<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0">'
            "</wfs:FeatureCollection>"
        )
        result = _parse_fmi_xml(xml)
        assert result == {}


class TestWeatherEndpoint:
    def _mock_response(self, xml=SAMPLE_FMI_XML, status=200):
        mock_resp = MagicMock()
        mock_resp.text = xml
        mock_resp.status_code = status
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    @patch("app.api.weather.requests.get")
    def test_returns_json(self, mock_get, client):
        mock_get.return_value = self._mock_response()
        res = client.get("/api/weather")
        assert res.status_code == 200
        data = res.get_json()
        assert data["station"] == "Vantaa"
        assert data["temperature"] == -6.1
        assert data["wind_speed"] == 3.2
        assert data["condition"] == "Snow"
        assert data["condition_fi"] == "Lumisadetta"
        assert data["wawa_code"] == 71
        assert data["timestamp"] == "2026-02-19T19:00:00Z"

    @patch("app.api.weather.requests.get")
    def test_feels_like_calculated(self, mock_get, client):
        mock_get.return_value = self._mock_response()
        res = client.get("/api/weather")
        data = res.get_json()
        # -6.1°C with 3.2 m/s wind → feels_like should be colder
        assert data["feels_like"] < data["temperature"]

    @patch("app.api.weather.requests.get")
    def test_cache_prevents_second_fetch(self, mock_get, client):
        mock_get.return_value = self._mock_response()
        client.get("/api/weather")
        client.get("/api/weather")
        assert mock_get.call_count == 1

    @patch("app.api.weather.time.time")
    @patch("app.api.weather.requests.get")
    def test_cache_expires(self, mock_get, mock_time, client):
        mock_get.return_value = self._mock_response()
        mock_time.return_value = 1000.0
        client.get("/api/weather")
        # Advance past TTL
        mock_time.return_value = 1000.0 + 601
        client.get("/api/weather")
        assert mock_get.call_count == 2

    @patch("app.api.weather.requests.get")
    def test_api_error_returns_cached(self, mock_get, client):
        # First call succeeds
        mock_get.return_value = self._mock_response()
        client.get("/api/weather")
        # Expire cache
        _cache["ts"] = 0
        # Second call fails
        mock_get.side_effect = Exception("FMI down")
        res = client.get("/api/weather")
        assert res.status_code == 200
        assert res.get_json()["station"] == "Vantaa"

    @patch("app.api.weather.requests.get")
    def test_api_error_no_cache_returns_502(self, mock_get, client):
        mock_get.side_effect = Exception("FMI down")
        res = client.get("/api/weather")
        assert res.status_code == 502
        assert "error" in res.get_json()
