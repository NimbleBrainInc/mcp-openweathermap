"""Tests for OpenWeatherMap MCP server tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_openweathermap import server
from mcp_openweathermap.api_client import OpenWeatherMapAPIError


@pytest.fixture(autouse=True)
def reset_client() -> None:
    """Reset the singleton client before each test."""
    server._client = None


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock client."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


# Access the underlying functions from FastMCP tools
search_location_fn = server.search_location.fn
check_weather_fn = server.check_weather.fn
get_forecast_fn = server.get_forecast.fn
check_air_quality_fn = server.check_air_quality.fn
get_historical_weather_fn = server.get_historical_weather.fn


class TestSearchLocation:
    """Tests for search_location tool."""

    async def test_search_returns_candidates(self, mock_client: MagicMock) -> None:
        """Test search_location returns matching locations."""
        mock_result1 = MagicMock()
        mock_result1.name = "Waimea"
        mock_result1.state = "Hawaii"
        mock_result1.country = "US"
        mock_result1.lat = 20.02
        mock_result1.lon = -155.66

        mock_result2 = MagicMock()
        mock_result2.name = "Waimea"
        mock_result2.state = "Hawaii"
        mock_result2.country = "US"
        mock_result2.lat = 21.96
        mock_result2.lon = -159.67

        mock_client.geocode_location = AsyncMock(return_value=[mock_result1, mock_result2])

        with patch.object(server, "get_client", return_value=mock_client):
            result = await search_location_fn("Waimea")

            mock_client.geocode_location.assert_called_once_with("Waimea", limit=5)
            assert len(result) == 2
            assert result[0]["name"] == "Waimea"
            assert result[0]["lat"] == 20.02
            assert result[1]["lat"] == 21.96

    async def test_search_with_custom_limit(self, mock_client: MagicMock) -> None:
        """Test search_location respects limit parameter."""
        mock_client.geocode_location = AsyncMock(return_value=[])

        with patch.object(server, "get_client", return_value=mock_client):
            await search_location_fn("Springfield", limit=10)

            mock_client.geocode_location.assert_called_once_with("Springfield", limit=10)

    async def test_search_returns_empty_for_no_matches(self, mock_client: MagicMock) -> None:
        """Test search_location returns empty list for no matches."""
        mock_client.geocode_location = AsyncMock(return_value=[])

        with patch.object(server, "get_client", return_value=mock_client):
            result = await search_location_fn("NonexistentPlace12345")

            assert result == []


class TestCheckWeather:
    """Tests for check_weather tool."""

    async def test_check_weather_by_city(self, mock_client: MagicMock) -> None:
        """Test getting weather for a city name."""
        mock_weather = MagicMock()
        mock_weather.model_dump.return_value = {
            "name": "London",
            "main": {"temp": 15.5, "humidity": 80},
            "weather": [{"description": "cloudy"}],
        }

        mock_client.resolve_location = AsyncMock(return_value=(51.5, -0.1))
        mock_client.get_current_weather = AsyncMock(return_value=mock_weather)

        with patch.object(server, "get_client", return_value=mock_client):
            result = await check_weather_fn(location="London")

            mock_client.resolve_location.assert_called_once_with("London")
            mock_client.get_current_weather.assert_called_once_with(51.5, -0.1, "metric")
            assert result["name"] == "London"
            assert result["main"]["temp"] == 15.5

    async def test_check_weather_with_units(self, mock_client: MagicMock) -> None:
        """Test getting weather with imperial units."""
        mock_weather = MagicMock()
        mock_weather.model_dump.return_value = {"main": {"temp": 59.9}}

        mock_client.resolve_location = AsyncMock(return_value=(40.7, -74.0))
        mock_client.get_current_weather = AsyncMock(return_value=mock_weather)

        with patch.object(server, "get_client", return_value=mock_client):
            result = await check_weather_fn(location="New York", units="imperial")

            mock_client.get_current_weather.assert_called_once_with(40.7, -74.0, "imperial")
            assert result["main"]["temp"] == 59.9

    async def test_check_weather_by_lat_lon(self, mock_client: MagicMock) -> None:
        """Test getting weather using direct lat/lon coordinates."""
        mock_weather = MagicMock()
        mock_weather.model_dump.return_value = {"coord": {"lat": 35.6, "lon": 139.6}}

        mock_client.get_current_weather = AsyncMock(return_value=mock_weather)

        with patch.object(server, "get_client", return_value=mock_client):
            result = await check_weather_fn(lat=35.6762, lon=139.6503)

            # Should NOT call resolve_location when lat/lon provided
            mock_client.resolve_location = AsyncMock()
            mock_client.get_current_weather.assert_called_once_with(35.6762, 139.6503, "metric")
            assert result["coord"]["lat"] == 35.6

    async def test_check_weather_missing_params_error(self, mock_client: MagicMock) -> None:
        """Test error when neither location nor lat/lon provided."""
        with patch.object(server, "get_client", return_value=mock_client):
            with pytest.raises(OpenWeatherMapAPIError) as exc_info:
                await check_weather_fn()
            assert exc_info.value.status == 400
            assert "Provide either" in exc_info.value.message


class TestGetForecast:
    """Tests for get_forecast tool."""

    async def test_forecast_one_call_success(self, mock_client: MagicMock) -> None:
        """Test forecast returns One Call data when available."""
        mock_client.resolve_location = AsyncMock(return_value=(51.5, -0.1))
        mock_client.get_forecast_with_fallback = AsyncMock(
            return_value={
                "source": "one_call",
                "hourly": [{"temp": 15}],
                "daily": [{"temp": {"day": 18}}],
                "alerts": [],
            }
        )

        with patch.object(server, "get_client", return_value=mock_client):
            result = await get_forecast_fn(location="London")

            assert result["source"] == "one_call"
            assert "hourly" in result
            assert "daily" in result

    async def test_forecast_free_tier_fallback(self, mock_client: MagicMock) -> None:
        """Test forecast falls back to free tier gracefully."""
        mock_client.resolve_location = AsyncMock(return_value=(51.5, -0.1))
        mock_client.get_forecast_with_fallback = AsyncMock(
            return_value={
                "source": "free_tier",
                "forecast_list": [{"dt": 1704067200}],
                "city": {"name": "London"},
                "alerts": [],
                "note": "Hourly forecast and alerts require One Call API subscription",
            }
        )

        with patch.object(server, "get_client", return_value=mock_client):
            result = await get_forecast_fn(location="London")

            assert result["source"] == "free_tier"
            assert "note" in result
            assert "forecast_list" in result

    async def test_forecast_with_lat_lon(self, mock_client: MagicMock) -> None:
        """Test forecast using direct coordinates."""
        mock_client.get_forecast_with_fallback = AsyncMock(
            return_value={"source": "one_call", "hourly": []}
        )

        with patch.object(server, "get_client", return_value=mock_client):
            result = await get_forecast_fn(lat=51.5, lon=-0.1)

            mock_client.get_forecast_with_fallback.assert_called_once_with(51.5, -0.1, "metric")
            assert result["source"] == "one_call"


class TestCheckAirQuality:
    """Tests for check_air_quality tool."""

    async def test_air_quality_by_location(self, mock_client: MagicMock) -> None:
        """Test getting air quality data by location string."""
        mock_aq = MagicMock()
        mock_aq.model_dump.return_value = {
            "coord": {"lat": 51.5, "lon": -0.1},
            "items": [
                {
                    "main": {"aqi": 2},
                    "components": {"pm2_5": 12.5, "pm10": 25.0, "o3": 45.0},
                }
            ],
        }

        mock_client.resolve_location = AsyncMock(return_value=(51.5, -0.1))
        mock_client.get_air_quality = AsyncMock(return_value=mock_aq)

        with patch.object(server, "get_client", return_value=mock_client):
            result = await check_air_quality_fn(location="London")

            mock_client.get_air_quality.assert_called_once_with(51.5, -0.1)
            assert result["items"][0]["main"]["aqi"] == 2

    async def test_air_quality_by_lat_lon(self, mock_client: MagicMock) -> None:
        """Test getting air quality data by coordinates."""
        mock_aq = MagicMock()
        mock_aq.model_dump.return_value = {
            "coord": {"lat": 35.6, "lon": 139.6},
            "items": [{"main": {"aqi": 3}}],
        }

        mock_client.get_air_quality = AsyncMock(return_value=mock_aq)

        with patch.object(server, "get_client", return_value=mock_client):
            result = await check_air_quality_fn(lat=35.6, lon=139.6)

            mock_client.get_air_quality.assert_called_once_with(35.6, 139.6)
            assert result["items"][0]["main"]["aqi"] == 3


class TestGetHistoricalWeather:
    """Tests for get_historical_weather tool."""

    async def test_historical_weather_success(self, mock_client: MagicMock) -> None:
        """Test successful historical weather retrieval."""
        mock_data = MagicMock()
        mock_data.model_dump.return_value = {
            "lat": 51.5,
            "lon": -0.1,
            "timezone": "Europe/London",
            "current": {"temp": 12.5},
        }

        mock_client.resolve_location = AsyncMock(return_value=(51.5, -0.1))
        mock_client.get_one_call_timemachine = AsyncMock(return_value=mock_data)

        with patch.object(server, "get_client", return_value=mock_client):
            result = await get_historical_weather_fn(date="2024-01-15", location="London")

            assert result["source"] == "one_call"
            assert result["lat"] == 51.5

    async def test_historical_weather_with_lat_lon(self, mock_client: MagicMock) -> None:
        """Test historical weather with direct coordinates."""
        mock_data = MagicMock()
        mock_data.model_dump.return_value = {"lat": 51.5, "lon": -0.1}

        mock_client.get_one_call_timemachine = AsyncMock(return_value=mock_data)

        with patch.object(server, "get_client", return_value=mock_client):
            result = await get_historical_weather_fn(date="2024-01-15", lat=51.5, lon=-0.1)

            assert result["source"] == "one_call"

    async def test_historical_weather_no_subscription(self, mock_client: MagicMock) -> None:
        """Test helpful error when One Call subscription is missing."""
        mock_client.resolve_location = AsyncMock(return_value=(51.5, -0.1))
        mock_client.get_one_call_timemachine = AsyncMock(
            side_effect=OpenWeatherMapAPIError(401, "Unauthorized")
        )

        with patch.object(server, "get_client", return_value=mock_client):
            result = await get_historical_weather_fn(date="2024-01-15", location="London")

            assert "error" in result
            assert "One Call API subscription" in result["error"]
            assert "subscription_url" in result

    async def test_historical_weather_invalid_date(self, mock_client: MagicMock) -> None:
        """Test error handling for invalid date format."""
        mock_client.resolve_location = AsyncMock(return_value=(51.5, -0.1))

        with patch.object(server, "get_client", return_value=mock_client):
            result = await get_historical_weather_fn(date="not-a-date", location="London")

            assert "error" in result
            assert "Invalid date format" in result["error"]

    async def test_historical_weather_other_errors_propagate(
        self, mock_client: MagicMock
    ) -> None:
        """Test that non-auth errors are raised."""
        mock_client.resolve_location = AsyncMock(return_value=(51.5, -0.1))
        mock_client.get_one_call_timemachine = AsyncMock(
            side_effect=OpenWeatherMapAPIError(500, "Server Error")
        )

        with patch.object(server, "get_client", return_value=mock_client):
            with pytest.raises(OpenWeatherMapAPIError) as exc_info:
                await get_historical_weather_fn(date="2024-01-15", location="London")
            assert exc_info.value.status == 500


class TestLocationResolution:
    """Tests for location handling across tools."""

    async def test_location_not_found_suggests_search(self, mock_client: MagicMock) -> None:
        """Test error message suggests search_location fallback."""
        mock_client.resolve_location = AsyncMock(
            side_effect=OpenWeatherMapAPIError(404, "Location not found: Waimea, HI")
        )

        with patch.object(server, "get_client", return_value=mock_client):
            with pytest.raises(OpenWeatherMapAPIError) as exc_info:
                await check_weather_fn(location="Waimea, HI")
            assert exc_info.value.status == 404
            assert "search_location" in exc_info.value.message

    async def test_lat_lon_bypasses_location_resolution(self, mock_client: MagicMock) -> None:
        """Test that lat/lon coordinates skip resolve_location entirely."""
        mock_weather = MagicMock()
        mock_weather.model_dump.return_value = {"main": {"temp": 25}}

        mock_client.resolve_location = AsyncMock()  # Should not be called
        mock_client.get_current_weather = AsyncMock(return_value=mock_weather)

        with patch.object(server, "get_client", return_value=mock_client):
            await check_weather_fn(lat=20.02, lon=-155.66)

            mock_client.resolve_location.assert_not_called()
            mock_client.get_current_weather.assert_called_once_with(20.02, -155.66, "metric")


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    async def test_health_check(self) -> None:
        """Test health endpoint returns healthy status."""
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        response = await server.health_check(mock_request)

        assert response.status_code == 200
        # JSONResponse body is bytes, decode and check
        import json

        body = json.loads(response.body)
        assert body["status"] == "healthy"
        assert body["service"] == "mcp-openweathermap"
