"""Unit tests for the MCP server tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Context

from mcp_openweathermap.api_models import (
    AirQualityComponents,
    AirQualityItem,
    AirQualityMain,
    AirQualityResponse,
    City,
    Clouds,
    Coordinates,
    CurrentWeatherResponse,
    ForecastItem,
    ForecastResponse,
    GeocodingResult,
    SystemData,
    Temperature,
    UVIndexResponse,
    WeatherCondition,
    Wind,
)
from mcp_openweathermap.server import (
    get_air_quality,
    get_current_weather,
    get_location_coordinates,
    get_solar_radiation,
    get_uv_index,
    get_weather_forecast,
)


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    ctx = MagicMock(spec=Context)
    ctx.warning = MagicMock()
    ctx.error = MagicMock()
    return ctx


@pytest.fixture
def mock_weather_response():
    """Create a mock current weather response."""
    return CurrentWeatherResponse(
        coord=Coordinates(lon=-79.5199, lat=8.9824),
        weather=[
            WeatherCondition(id=800, main="Clear", description="clear sky", icon="01d")
        ],
        base="stations",
        main=Temperature(
            temp=28.5,
            feels_like=30.2,
            temp_min=28.0,
            temp_max=29.0,
            pressure=1013,
            humidity=70,
        ),
        visibility=10000,
        wind=Wind(speed=3.5, deg=180),
        clouds=Clouds(all=20),
        dt=1609459200,
        sys=SystemData(country="PA", sunrise=1609416000, sunset=1609459200),
        timezone=-18000,
        id=3703443,
        name="Panama City",
        cod=200,
    )


@pytest.fixture
def mock_forecast_response():
    """Create a mock forecast response."""
    return ForecastResponse(
        cod="200",
        message=0,
        cnt=1,
        list=[
            ForecastItem(
                dt=1609459200,
                main=Temperature(
                    temp=28.5,
                    feels_like=30.2,
                    temp_min=28.0,
                    temp_max=29.0,
                    pressure=1013,
                    humidity=70,
                ),
                weather=[
                    WeatherCondition(id=800, main="Clear", description="clear sky", icon="01d")
                ],
                clouds=Clouds(all=20),
                wind=Wind(speed=3.5, deg=180),
                visibility=10000,
                pop=0.1,
                dt_txt="2021-01-01 00:00:00",
            )
        ],
        city=City(
            id=3703443,
            name="Panama City",
            coord=Coordinates(lat=8.9824, lon=-79.5199),
            country="PA",
            timezone=-18000,
            sunrise=1609416000,
            sunset=1609459200,
        ),
    )


class TestMCPTools:
    """Test the MCP server tools."""

    @pytest.mark.asyncio
    async def test_get_current_weather_by_location(
        self, mock_context, mock_weather_response
    ):
        """Test get_current_weather with location name."""
        with patch("mcp_openweathermap.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.get_current_weather.return_value = mock_weather_response

            result = await get_current_weather(
                location="Panama City", ctx=mock_context
            )

            assert result["name"] == "Panama City"
            assert result["main"]["temp"] == 28.5
            assert result["coord"]["lat"] == 8.9824
            mock_client.get_current_weather.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_weather_by_coordinates(
        self, mock_context, mock_weather_response
    ):
        """Test get_current_weather with coordinates."""
        with patch("mcp_openweathermap.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.get_current_weather.return_value = mock_weather_response

            result = await get_current_weather(
                lat=8.9824, lon=-79.5199, ctx=mock_context
            )

            assert result["name"] == "Panama City"
            mock_client.get_current_weather.assert_called_once_with(
                8.9824, -79.5199, "metric"
            )

    @pytest.mark.asyncio
    async def test_get_weather_forecast(self, mock_context, mock_forecast_response):
        """Test get_weather_forecast tool."""
        with patch("mcp_openweathermap.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.get_forecast.return_value = mock_forecast_response

            result = await get_weather_forecast(
                location="Panama City", ctx=mock_context
            )

            assert result["city"]["name"] == "Panama City"
            assert result["cnt"] == 1
            assert len(result["list"]) == 1
            mock_client.get_forecast.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_air_quality(self, mock_context):
        """Test get_air_quality tool."""
        mock_response = AirQualityResponse(
            coord=Coordinates(lon=-79.5199, lat=8.9824),
            list=[
                AirQualityItem(
                    main=AirQualityMain(aqi=2),
                    components=AirQualityComponents(
                        co=220.0,
                        no=0.1,
                        no2=15.0,
                        o3=50.0,
                        so2=5.0,
                        pm2_5=12.0,
                        pm10=20.0,
                        nh3=1.0,
                    ),
                    dt=1609459200,
                )
            ],
        )

        with patch("mcp_openweathermap.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.get_air_quality.return_value = mock_response

            result = await get_air_quality(
                location="Panama City", ctx=mock_context
            )

            assert result["coord"]["lat"] == 8.9824
            assert len(result["list"]) == 1
            assert result["list"][0]["main"]["aqi"] == 2
            mock_client.get_air_quality.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_uv_index(self, mock_context):
        """Test get_uv_index tool."""
        mock_response = UVIndexResponse(
            lat=8.9824,
            lon=-79.5199,
            date_iso="2021-01-01T12:00:00Z",
            date=1609459200,
            value=8.5,
        )

        with patch("mcp_openweathermap.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.get_uv_index.return_value = mock_response

            result = await get_uv_index(
                location="Panama City", ctx=mock_context
            )

            assert result["lat"] == 8.9824
            assert result["value"] == 8.5
            mock_client.get_uv_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_solar_radiation(self, mock_context, mock_weather_response):
        """Test get_solar_radiation tool for Solar5Estrella integration."""
        mock_uv = UVIndexResponse(
            lat=8.9824,
            lon=-79.5199,
            date_iso="2021-01-01T12:00:00Z",
            date=1609459200,
            value=8.5,
        )

        with patch("mcp_openweathermap.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.get_current_weather.return_value = mock_weather_response
            mock_client.get_uv_index.return_value = mock_uv

            result = await get_solar_radiation(
                location="Panama City", ctx=mock_context
            )

            # Validate Solar5Estrella format
            assert "location" in result
            assert "coordinates" in result
            assert "avg_daily_kwh_m2" in result
            assert "peak_sun_hours" in result
            assert "monthly_averages" in result
            assert "source" in result

            # Validate coordinates
            assert result["coordinates"]["lat"] == 8.9824
            assert result["coordinates"]["lon"] == -79.5199

            # Validate monthly averages has all 12 months
            months = [
                "january",
                "february",
                "march",
                "april",
                "may",
                "june",
                "july",
                "august",
                "september",
                "october",
                "november",
                "december",
            ]
            for month in months:
                assert month in result["monthly_averages"]
                assert isinstance(result["monthly_averages"][month], (int, float))

            # Validate data types
            assert isinstance(result["avg_daily_kwh_m2"], (int, float))
            assert isinstance(result["peak_sun_hours"], (int, float))
            assert result["source"] == "OpenWeatherMap"

            # Validate reasonable values for Panama (tropical location)
            assert 3.0 <= result["avg_daily_kwh_m2"] <= 7.0
            assert 3.0 <= result["peak_sun_hours"] <= 7.0

    @pytest.mark.asyncio
    async def test_get_solar_radiation_by_coordinates(
        self, mock_context, mock_weather_response
    ):
        """Test get_solar_radiation with coordinates."""
        mock_uv = UVIndexResponse(
            lat=8.9824,
            lon=-79.5199,
            date_iso="2021-01-01T12:00:00Z",
            date=1609459200,
            value=8.5,
        )

        with patch("mcp_openweathermap.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.get_current_weather.return_value = mock_weather_response
            mock_client.get_uv_index.return_value = mock_uv

            result = await get_solar_radiation(
                lat=8.9824, lon=-79.5199, ctx=mock_context
            )

            assert result["coordinates"]["lat"] == 8.9824
            assert result["coordinates"]["lon"] == -79.5199

    @pytest.mark.asyncio
    async def test_get_location_coordinates_preset(self, mock_context):
        """Test get_location_coordinates with preset Panama location."""
        result = await get_location_coordinates(
            location="Panama City", ctx=mock_context
        )

        assert result["location"] == "Panama City"
        assert result["lat"] == 8.9824
        assert result["lon"] == -79.5199
        assert result["country"] == "PA"
        assert result["source"] == "preset"

    @pytest.mark.asyncio
    async def test_get_location_coordinates_geocoding(self, mock_context):
        """Test get_location_coordinates with geocoding."""
        mock_geocode = [
            GeocodingResult(
                name="London",
                lat=51.5074,
                lon=-0.1278,
                country="GB",
                state=None,
            )
        ]

        with patch("mcp_openweathermap.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.geocode_location.return_value = mock_geocode

            result = await get_location_coordinates(
                location="London", ctx=mock_context
            )

            assert result["lat"] == 51.5074
            assert result["lon"] == -0.1278
            assert result["country"] == "GB"
            assert result["source"] == "geocoding"
            mock_client.geocode_location.assert_called_once_with("London", limit=1)

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_context):
        """Test error handling in tools."""
        with patch("mcp_openweathermap.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.get_current_weather.side_effect = Exception("API Error")

            with pytest.raises(Exception):
                await get_current_weather(lat=0, lon=0, ctx=mock_context)

            mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_missing_location_error(self, mock_context):
        """Test error when neither location nor coordinates provided."""
        with pytest.raises(ValueError) as exc_info:
            await get_current_weather(ctx=mock_context)

        assert "location name or coordinates" in str(exc_info.value)
