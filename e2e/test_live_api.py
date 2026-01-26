"""End-to-end tests against live OpenWeatherMap API.

These tests require a valid OPENWEATHERMAP_API_KEY environment variable.
They are skipped if the API key is not set.

Run with: uv run pytest e2e/ -v
"""

import os

import pytest

from mcp_openweathermap.api_client import OpenWeatherMapAPIError, OpenWeatherMapClient

# Skip all tests if no API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENWEATHERMAP_API_KEY"),
    reason="OPENWEATHERMAP_API_KEY not set",
)


class TestDirectLocationResolution:
    """Tests for locations that resolve directly."""

    async def test_simple_city_name(self) -> None:
        """Test simple city names resolve directly."""
        async with OpenWeatherMapClient() as client:
            lat, lon = await client.resolve_location("Tokyo")

            # Verify Tokyo coordinates
            assert 35 < lat < 36
            assert 139 < lon < 140

            weather = await client.get_current_weather(lat, lon)
            assert weather.main.temp is not None

    async def test_city_with_country(self) -> None:
        """Test city with full country name."""
        async with OpenWeatherMapClient() as client:
            lat, lon = await client.resolve_location("Paris, France")

            assert 48 < lat < 49
            assert 2 < lon < 3

    async def test_coordinates_passthrough(self) -> None:
        """Test direct coordinates work."""
        async with OpenWeatherMapClient() as client:
            # Honolulu coordinates
            lat, lon = await client.resolve_location("21.3069,-157.8583")

            assert lat == 21.3069
            assert lon == -157.8583


class TestSearchLocationFallback:
    """Tests demonstrating the search_location fallback pattern.

    These test locations that fail direct resolution but work via search.
    """

    async def test_waimea_hawaii_via_search(self) -> None:
        """Test Waimea, HI - fails direct, works via search.

        This demonstrates the LLM fallback pattern:
        1. check_weather("Waimea, HI") fails
        2. search_location("Waimea") returns candidates
        3. LLM picks correct one, calls check_weather(lat=..., lon=...)
        """
        async with OpenWeatherMapClient() as client:
            # Direct resolution fails for "Waimea, HI"
            with pytest.raises(OpenWeatherMapAPIError) as exc_info:
                await client.resolve_location("Waimea, HI")
            assert exc_info.value.status == 404

            # But search_location("Waimea") works
            results = await client.geocode_location("Waimea", limit=5)

            # Should find Waimea in Hawaii
            hawaii_results = [r for r in results if r.state == "Hawaii"]
            assert len(hawaii_results) >= 1, "Should find at least one Waimea in Hawaii"

            # Pick first Hawaii result and get weather
            waimea = hawaii_results[0]
            assert 19 < waimea.lat < 22  # Hawaii latitude range
            assert -160 < waimea.lon < -154  # Hawaii longitude range

            weather = await client.get_current_weather(waimea.lat, waimea.lon)
            assert weather.main.temp is not None
            assert -10 < weather.main.temp < 40  # Reasonable Hawaii temp

    async def test_london_uk_via_search(self) -> None:
        """Test London, UK - fails direct (needs GB), works via search."""
        async with OpenWeatherMapClient() as client:
            # "London, UK" fails, API wants "London, GB"
            with pytest.raises(OpenWeatherMapAPIError):
                await client.resolve_location("London, UK")

            # Search for just "London" works
            results = await client.geocode_location("London", limit=5)

            # Find London in GB
            gb_results = [r for r in results if r.country == "GB"]
            assert len(gb_results) >= 1

            london = gb_results[0]
            assert 51 < london.lat < 52
            assert -1 < london.lon < 1

    async def test_springfield_disambiguation(self) -> None:
        """Test ambiguous location - multiple Springfields exist."""
        async with OpenWeatherMapClient() as client:
            results = await client.geocode_location("Springfield", limit=5)

            # Should return multiple results
            assert len(results) >= 3, "Springfield exists in many US states"

            # Results should include different states
            states = {r.state for r in results if r.state}
            assert len(states) >= 2, "Should have Springfields in different states"


class TestWeatherTools:
    """Tests for weather data retrieval."""

    async def test_air_quality(self) -> None:
        """Test air quality data."""
        async with OpenWeatherMapClient() as client:
            lat, lon = await client.resolve_location("Tokyo")

            aq = await client.get_air_quality(lat, lon)

            assert len(aq.items) > 0
            assert 1 <= aq.items[0].main.aqi <= 5
            assert aq.items[0].components.pm2_5 >= 0

    async def test_forecast_free_tier(self) -> None:
        """Test 5-day forecast."""
        async with OpenWeatherMapClient() as client:
            lat, lon = await client.resolve_location("Sydney")

            forecast = await client.get_forecast(lat, lon)

            assert forecast.cnt > 0
            assert len(forecast.forecast_list) > 0
            assert forecast.city.name is not None

    async def test_forecast_with_fallback(self) -> None:
        """Test forecast graceful degradation."""
        async with OpenWeatherMapClient() as client:
            lat, lon = await client.resolve_location("Berlin")

            result = await client.get_forecast_with_fallback(lat, lon)

            # Either source is valid
            assert result["source"] in ("one_call", "free_tier")

            if result["source"] == "one_call":
                assert "hourly" in result or "daily" in result
            else:
                assert "forecast_list" in result
                assert "note" in result
