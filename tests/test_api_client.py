"""Tests for OpenWeatherMap API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_openweathermap.api_client import OpenWeatherMapAPIError, OpenWeatherMapClient


@pytest.fixture
def client() -> OpenWeatherMapClient:
    """Create a client with a test API key."""
    return OpenWeatherMapClient(api_key="test_api_key")


class TestResolveLocation:
    """Tests for location resolution."""

    async def test_resolve_coordinates_format(self, client: OpenWeatherMapClient) -> None:
        """Test parsing 'lat,lon' format directly."""
        lat, lon = await client.resolve_location("51.5074,-0.1278")
        assert lat == 51.5074
        assert lon == -0.1278

    async def test_resolve_coordinates_with_spaces(self, client: OpenWeatherMapClient) -> None:
        """Test parsing 'lat, lon' format with spaces."""
        lat, lon = await client.resolve_location("40.7128, -74.0060")
        assert lat == 40.7128
        assert lon == -74.0060

    async def test_resolve_invalid_coordinates_falls_back_to_geocoding(
        self, client: OpenWeatherMapClient
    ) -> None:
        """Test that invalid coordinate-like strings fall back to geocoding."""
        mock_result = MagicMock()
        mock_result.lat = 51.5074
        mock_result.lon = -0.1278

        with patch.object(
            client, "geocode_location", new_callable=AsyncMock, return_value=[mock_result]
        ):
            lat, lon = await client.resolve_location("London, UK")
            assert lat == 51.5074
            assert lon == -0.1278

    async def test_resolve_out_of_range_coordinates_falls_back(
        self, client: OpenWeatherMapClient
    ) -> None:
        """Test that out-of-range coordinates fall back to geocoding."""
        mock_result = MagicMock()
        mock_result.lat = 0.0
        mock_result.lon = 0.0

        with patch.object(
            client, "geocode_location", new_callable=AsyncMock, return_value=[mock_result]
        ):
            # Latitude > 90 is invalid
            lat, lon = await client.resolve_location("100.0,50.0")
            # Should have called geocoding since coords were invalid
            client.geocode_location.assert_called_once()

    async def test_resolve_location_not_found(self, client: OpenWeatherMapClient) -> None:
        """Test error when location cannot be found."""
        with patch.object(
            client, "geocode_location", new_callable=AsyncMock, return_value=[]
        ):
            with pytest.raises(OpenWeatherMapAPIError) as exc_info:
                await client.resolve_location("NonexistentPlace12345")
            assert exc_info.value.status == 404
            assert "Location not found" in exc_info.value.message


class TestGetForecastWithFallback:
    """Tests for graceful degradation in forecast retrieval."""

    async def test_one_call_success(self, client: OpenWeatherMapClient) -> None:
        """Test successful One Call API response."""
        mock_one_call = MagicMock()
        mock_one_call.current = {"temp": 20}
        mock_one_call.hourly = []
        mock_one_call.daily = []
        mock_one_call.alerts = None
        mock_one_call.timezone = "Europe/London"

        with patch.object(
            client, "get_one_call", new_callable=AsyncMock, return_value=mock_one_call
        ):
            result = await client.get_forecast_with_fallback(51.5, -0.1)

            assert result["source"] == "one_call"
            assert result["timezone"] == "Europe/London"
            assert result["alerts"] == []

    async def test_fallback_on_401(self, client: OpenWeatherMapClient) -> None:
        """Test fallback to free tier on 401 unauthorized."""
        mock_forecast = MagicMock()
        mock_forecast.forecast_list = []
        mock_forecast.city = MagicMock()
        mock_forecast.city.model_dump.return_value = {"name": "London"}

        with (
            patch.object(
                client,
                "get_one_call",
                new_callable=AsyncMock,
                side_effect=OpenWeatherMapAPIError(401, "Unauthorized"),
            ),
            patch.object(
                client, "get_forecast", new_callable=AsyncMock, return_value=mock_forecast
            ),
        ):
            result = await client.get_forecast_with_fallback(51.5, -0.1)

            assert result["source"] == "free_tier"
            assert "note" in result
            assert "One Call API subscription" in result["note"]

    async def test_fallback_on_403(self, client: OpenWeatherMapClient) -> None:
        """Test fallback to free tier on 403 forbidden."""
        mock_forecast = MagicMock()
        mock_forecast.forecast_list = []
        mock_forecast.city = MagicMock()
        mock_forecast.city.model_dump.return_value = {"name": "London"}

        with (
            patch.object(
                client,
                "get_one_call",
                new_callable=AsyncMock,
                side_effect=OpenWeatherMapAPIError(403, "Forbidden"),
            ),
            patch.object(
                client, "get_forecast", new_callable=AsyncMock, return_value=mock_forecast
            ),
        ):
            result = await client.get_forecast_with_fallback(51.5, -0.1)

            assert result["source"] == "free_tier"

    async def test_other_errors_propagate(self, client: OpenWeatherMapClient) -> None:
        """Test that non-auth errors are not caught."""
        with patch.object(
            client,
            "get_one_call",
            new_callable=AsyncMock,
            side_effect=OpenWeatherMapAPIError(500, "Server Error"),
        ):
            with pytest.raises(OpenWeatherMapAPIError) as exc_info:
                await client.get_forecast_with_fallback(51.5, -0.1)
            assert exc_info.value.status == 500


class TestGetOneCallTimemachine:
    """Tests for historical weather retrieval."""

    async def test_timemachine_request(self, client: OpenWeatherMapClient) -> None:
        """Test that timemachine endpoint is called correctly."""
        mock_response = {
            "lat": 51.5,
            "lon": -0.1,
            "timezone": "Europe/London",
            "timezone_offset": 0,
        }

        with patch.object(
            client, "_request", new_callable=AsyncMock, return_value=mock_response
        ):
            await client.get_one_call_timemachine(51.5, -0.1, 1704067200)

            client._request.assert_called_once()
            call_args = client._request.call_args
            assert "onecall/timemachine" in call_args[0][1]
            assert call_args[1]["params"]["dt"] == 1704067200


class TestErrorHandling:
    """Tests for API error handling."""

    async def test_api_error_with_details(self) -> None:
        """Test OpenWeatherMapAPIError stores details correctly."""
        error = OpenWeatherMapAPIError(
            status=401, message="Invalid API key", details={"cod": 401}
        )
        assert error.status == 401
        assert error.message == "Invalid API key"
        assert error.details == {"cod": 401}
        assert "401" in str(error)
        assert "Invalid API key" in str(error)

    async def test_client_without_api_key_uses_env(self) -> None:
        """Test client reads API key from environment."""
        with patch.dict("os.environ", {"OPENWEATHERMAP_API_KEY": "env_key"}):
            client = OpenWeatherMapClient()
            assert client.api_key == "env_key"


class TestClientLifecycle:
    """Tests for client session management."""

    async def test_context_manager(self, client: OpenWeatherMapClient) -> None:
        """Test client works as async context manager."""
        assert client._session is None

        async with client:
            assert client._session is not None

        assert client._session is None

    async def test_ensure_session_creates_session(self, client: OpenWeatherMapClient) -> None:
        """Test _ensure_session creates a session if none exists."""
        assert client._session is None
        await client._ensure_session()
        assert client._session is not None
        await client.close()

    async def test_close_is_idempotent(self, client: OpenWeatherMapClient) -> None:
        """Test closing multiple times doesn't error."""
        await client._ensure_session()
        await client.close()
        await client.close()  # Should not raise
