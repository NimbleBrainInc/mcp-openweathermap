"""Unit tests for the OpenWeatherMap API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError

from mcp_openweathermap.api_client import OpenWeatherMapAPIError, OpenWeatherMapClient


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    session = AsyncMock()
    return session


@pytest.fixture
def client():
    """Create an OpenWeatherMap client for testing."""
    return OpenWeatherMapClient(api_key="test_api_key")


class TestOpenWeatherMapClient:
    """Test the OpenWeatherMapClient class."""

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test client context manager protocol."""
        async with client as c:
            assert c._session is not None

        assert client._session is None

    @pytest.mark.asyncio
    async def test_get_current_weather_success(self, client, mock_session):
        """Test get_current_weather with successful response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers.get.return_value = "application/json"
        mock_response.json.return_value = {
            "coord": {"lon": -79.5199, "lat": 8.9824},
            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
            "base": "stations",
            "main": {
                "temp": 28.5,
                "feels_like": 30.2,
                "temp_min": 28.0,
                "temp_max": 29.0,
                "pressure": 1013,
                "humidity": 70,
            },
            "visibility": 10000,
            "wind": {"speed": 3.5, "deg": 180},
            "clouds": {"all": 20},
            "dt": 1609459200,
            "sys": {"country": "PA", "sunrise": 1609416000, "sunset": 1609459200},
            "timezone": -18000,
            "id": 3703443,
            "name": "Panama City",
            "cod": 200,
        }

        mock_session.request.return_value.__aenter__.return_value = mock_response
        client._session = mock_session

        result = await client.get_current_weather(8.9824, -79.5199)

        assert result.name == "Panama City"
        assert result.main.temp == 28.5
        assert result.coord.lat == 8.9824

    @pytest.mark.asyncio
    async def test_get_forecast_success(self, client, mock_session):
        """Test get_forecast with successful response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers.get.return_value = "application/json"
        mock_response.json.return_value = {
            "cod": "200",
            "message": 0,
            "cnt": 1,
            "list": [
                {
                    "dt": 1609459200,
                    "main": {
                        "temp": 28.5,
                        "feels_like": 30.2,
                        "temp_min": 28.0,
                        "temp_max": 29.0,
                        "pressure": 1013,
                        "humidity": 70,
                    },
                    "weather": [
                        {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
                    ],
                    "clouds": {"all": 20},
                    "wind": {"speed": 3.5, "deg": 180},
                    "visibility": 10000,
                    "pop": 0.1,
                    "dt_txt": "2021-01-01 00:00:00",
                }
            ],
            "city": {
                "id": 3703443,
                "name": "Panama City",
                "coord": {"lat": 8.9824, "lon": -79.5199},
                "country": "PA",
                "timezone": -18000,
                "sunrise": 1609416000,
                "sunset": 1609459200,
            },
        }

        mock_session.request.return_value.__aenter__.return_value = mock_response
        client._session = mock_session

        result = await client.get_forecast(8.9824, -79.5199)

        assert result.city.name == "Panama City"
        assert result.cnt == 1
        assert len(result.list) == 1

    @pytest.mark.asyncio
    async def test_get_air_quality_success(self, client, mock_session):
        """Test get_air_quality with successful response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers.get.return_value = "application/json"
        mock_response.json.return_value = {
            "coord": {"lon": -79.5199, "lat": 8.9824},
            "list": [
                {
                    "main": {"aqi": 2},
                    "components": {
                        "co": 220.0,
                        "no": 0.1,
                        "no2": 15.0,
                        "o3": 50.0,
                        "so2": 5.0,
                        "pm2_5": 12.0,
                        "pm10": 20.0,
                        "nh3": 1.0,
                    },
                    "dt": 1609459200,
                }
            ],
        }

        mock_session.request.return_value.__aenter__.return_value = mock_response
        client._session = mock_session

        result = await client.get_air_quality(8.9824, -79.5199)

        assert result.coord.lat == 8.9824
        assert len(result.list) == 1
        assert result.list[0].main.aqi == 2

    @pytest.mark.asyncio
    async def test_get_uv_index_success(self, client, mock_session):
        """Test get_uv_index with successful response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers.get.return_value = "application/json"
        mock_response.json.return_value = {
            "lat": 8.9824,
            "lon": -79.5199,
            "date_iso": "2021-01-01T12:00:00Z",
            "date": 1609459200,
            "value": 8.5,
        }

        mock_session.request.return_value.__aenter__.return_value = mock_response
        client._session = mock_session

        result = await client.get_uv_index(8.9824, -79.5199)

        assert result.lat == 8.9824
        assert result.value == 8.5

    @pytest.mark.asyncio
    async def test_geocode_location_success(self, client, mock_session):
        """Test geocode_location with successful response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers.get.return_value = "application/json"
        mock_response.json.return_value = [
            {
                "name": "Panama City",
                "lat": 8.9824,
                "lon": -79.5199,
                "country": "PA",
                "state": "Panamá Province",
            }
        ]

        mock_session.request.return_value.__aenter__.return_value = mock_response
        client._session = mock_session

        result = await client.geocode_location("Panama City")

        assert len(result) == 1
        assert result[0].name == "Panama City"
        assert result[0].lat == 8.9824

    @pytest.mark.asyncio
    async def test_api_error_handling(self, client, mock_session):
        """Test API error handling."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.headers.get.return_value = "application/json"
        mock_response.json.return_value = {"cod": "404", "message": "city not found"}

        mock_session.request.return_value.__aenter__.return_value = mock_response
        client._session = mock_session

        with pytest.raises(OpenWeatherMapAPIError) as exc_info:
            await client.get_current_weather(0, 0)

        assert exc_info.value.status == 404
        assert "city not found" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_network_error_handling(self, client, mock_session):
        """Test network error handling."""
        mock_session.request.side_effect = ClientError("Network error")
        client._session = mock_session

        with pytest.raises(OpenWeatherMapAPIError) as exc_info:
            await client.get_current_weather(0, 0)

        assert exc_info.value.status == 500
        assert "Network error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_session_initialization(self, client):
        """Test session is initialized when needed."""
        assert client._session is None

        await client._ensure_session()

        assert client._session is not None

    @pytest.mark.asyncio
    async def test_close_session(self, client):
        """Test session closing."""
        await client._ensure_session()
        assert client._session is not None

        await client.close()

        assert client._session is None
