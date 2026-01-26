"""Async API client for OpenWeatherMap API using aiohttp."""

import os
from typing import Any

import aiohttp
from aiohttp import ClientError

from .api_models import (
    AirQualityResponse,
    CurrentWeatherResponse,
    ForecastResponse,
    GeocodingResult,
    OneCallResponse,
)


class OpenWeatherMapAPIError(Exception):
    """Custom exception for OpenWeatherMap API errors."""

    def __init__(self, status: int, message: str, details: dict[str, Any] | None = None) -> None:
        self.status = status
        self.message = message
        self.details = details
        super().__init__(f"OpenWeatherMap API Error {status}: {message}")


class OpenWeatherMapClient:
    """Async API client for OpenWeatherMap API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openweathermap.org/data/2.5",
        geo_url: str = "https://api.openweathermap.org/geo/1.0",
        onecall_url: str = "https://api.openweathermap.org/data/3.0",
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENWEATHERMAP_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.geo_url = geo_url.rstrip("/")
        self.onecall_url = onecall_url.rstrip("/")
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "OpenWeatherMapClient":
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def _ensure_session(self) -> None:
        """Create session if it doesn't exist."""
        if not self._session:
            headers = {
                "User-Agent": "mcp-server-openweathermap/1.0",
                "Accept": "application/json",
            }
            self._session = aiohttp.ClientSession(
                headers=headers, timeout=aiohttp.ClientTimeout(total=self.timeout)
            )

    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json_data: Any | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with error handling."""
        await self._ensure_session()

        # Add API key to params
        if params is None:
            params = {}
        if self.api_key:
            params["appid"] = self.api_key

        kwargs: dict[str, Any] = {}
        if json_data is not None:
            kwargs["json"] = json_data

        try:
            if not self._session:
                raise RuntimeError("Session not initialized")

            async with self._session.request(method, url, params=params, **kwargs) as response:
                content_type = response.headers.get("Content-Type", "")

                if "application/json" in content_type:
                    result = await response.json()
                else:
                    text = await response.text()
                    # Try to parse as JSON
                    if text.startswith("{") or text.startswith("["):
                        import json

                        try:
                            result = json.loads(text)
                        except json.JSONDecodeError:
                            result = {"result": text}
                    else:
                        result = {"result": text}

                # Check for errors
                if response.status >= 400:
                    error_msg = "Unknown error"
                    if isinstance(result, dict):
                        error_msg = (
                            result.get("message")
                            or result.get("error", {}).get("message")
                            or str(result.get("error", error_msg))
                        )
                    raise OpenWeatherMapAPIError(response.status, error_msg, result)

                return result

        except ClientError as e:
            raise OpenWeatherMapAPIError(500, f"Network error: {str(e)}") from e

    async def get_current_weather(
        self, lat: float, lon: float, units: str = "metric"
    ) -> CurrentWeatherResponse:
        """Get current weather by coordinates.

        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            units: Units of measurement (metric, imperial, standard)

        Returns:
            Current weather data
        """
        params = {"lat": lat, "lon": lon, "units": units}
        data = await self._request("GET", f"{self.base_url}/weather", params=params)
        return CurrentWeatherResponse(**data)

    async def get_forecast(
        self, lat: float, lon: float, units: str = "metric", cnt: int | None = None
    ) -> ForecastResponse:
        """Get 5-day weather forecast with 3-hour intervals.

        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            units: Units of measurement (metric, imperial, standard)
            cnt: Number of timestamps to return (max: 40)

        Returns:
            5-day forecast data
        """
        params: dict[str, Any] = {"lat": lat, "lon": lon, "units": units}
        if cnt is not None:
            params["cnt"] = cnt
        data = await self._request("GET", f"{self.base_url}/forecast", params=params)
        return ForecastResponse(**data)

    async def get_air_quality(self, lat: float, lon: float) -> AirQualityResponse:
        """Get air quality index and pollutant data.

        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate

        Returns:
            Air quality data with AQI and pollutant concentrations
        """
        params = {"lat": lat, "lon": lon}
        data = await self._request("GET", f"{self.base_url}/air_pollution", params=params)
        return AirQualityResponse(**data)

    async def get_one_call(
        self, lat: float, lon: float, exclude: str | None = None
    ) -> OneCallResponse:
        """Get comprehensive weather data using One Call API 3.0.

        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            exclude: Comma-separated list to exclude (current, minutely, hourly, daily, alerts)

        Returns:
            Comprehensive weather data including current, forecasts, and alerts
        """
        params: dict[str, Any] = {"lat": lat, "lon": lon}
        if exclude:
            params["exclude"] = exclude
        data = await self._request("GET", f"{self.onecall_url}/onecall", params=params)
        return OneCallResponse(**data)

    async def geocode_location(self, location_name: str, limit: int = 5) -> list[GeocodingResult]:
        """Geocode a location name to coordinates.

        Args:
            location_name: Location name to search
            limit: Maximum number of results (default: 5)

        Returns:
            List of geocoding results with coordinates
        """
        params = {"q": location_name, "limit": limit}
        data = await self._request("GET", f"{self.geo_url}/direct", params=params)
        if isinstance(data, list):
            return [GeocodingResult(**item) for item in data]
        return []

    async def get_weather_by_city(self, city: str, units: str = "metric") -> CurrentWeatherResponse:
        """Get current weather by city name.

        Args:
            city: City name (e.g., 'London,GB', 'New York,US')
            units: Units of measurement (metric, imperial, standard)

        Returns:
            Current weather data
        """
        params = {"q": city, "units": units}
        data = await self._request("GET", f"{self.base_url}/weather", params=params)
        return CurrentWeatherResponse(**data)

    async def get_forecast_by_city(
        self, city: str, units: str = "metric", cnt: int | None = None
    ) -> ForecastResponse:
        """Get 5-day forecast by city name.

        Args:
            city: City name (e.g., 'London,GB')
            units: Units of measurement (metric, imperial, standard)
            cnt: Number of timestamps to return (max: 40)

        Returns:
            5-day forecast data
        """
        params: dict[str, Any] = {"q": city, "units": units}
        if cnt is not None:
            params["cnt"] = cnt
        data = await self._request("GET", f"{self.base_url}/forecast", params=params)
        return ForecastResponse(**data)

    async def get_one_call_timemachine(
        self, lat: float, lon: float, dt: int, units: str = "metric"
    ) -> OneCallResponse:
        """Get historical weather data using One Call API 3.0 timemachine.

        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            dt: Unix timestamp (UTC) for the historical date
            units: Units of measurement (metric, imperial, standard)

        Returns:
            Historical weather data
        """
        params: dict[str, Any] = {"lat": lat, "lon": lon, "dt": dt, "units": units}
        data = await self._request(
            "GET", f"{self.onecall_url}/onecall/timemachine", params=params
        )
        return OneCallResponse(**data)

    async def resolve_location(self, location: str) -> tuple[float, float]:
        """Resolve location to coordinates. Accepts:
        - City name: "London", "New York, US"
        - Coordinates: "51.5,-0.1" or "51.5, -0.1"

        Args:
            location: Location string (city name or coordinates)

        Returns:
            Tuple of (latitude, longitude)

        Raises:
            OpenWeatherMapAPIError: If location cannot be resolved
        """
        # Check if already coordinates (format: "lat,lon" or "lat, lon")
        if "," in location:
            parts = location.split(",")
            if len(parts) == 2:
                try:
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        return lat, lon
                except ValueError:
                    pass  # Not coordinates, try geocoding

        # Geocode the location name
        results = await self.geocode_location(location, limit=1)
        if not results:
            raise OpenWeatherMapAPIError(404, f"Location not found: {location}")
        return results[0].lat, results[0].lon

    async def get_forecast_with_fallback(
        self, lat: float, lon: float, units: str = "metric"
    ) -> dict[str, Any]:
        """Get forecast with graceful degradation.

        Tries One Call API first for rich data (hourly, daily, alerts).
        Falls back to free 5-day forecast on 401/403 errors.

        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            units: Units of measurement (metric, imperial, standard)

        Returns:
            Forecast data with 'source' field indicating data tier
        """
        try:
            one_call_data = await self.get_one_call(lat, lon)
            return {
                "source": "one_call",
                "current": one_call_data.current,
                "hourly": (
                    [h.model_dump() for h in one_call_data.hourly]
                    if one_call_data.hourly
                    else None
                ),
                "daily": (
                    [d.model_dump() for d in one_call_data.daily]
                    if one_call_data.daily
                    else None
                ),
                "alerts": (
                    [a.model_dump() for a in one_call_data.alerts]
                    if one_call_data.alerts
                    else []
                ),
                "timezone": one_call_data.timezone,
            }
        except OpenWeatherMapAPIError as e:
            if e.status in (401, 403):
                # Fall back to free tier
                forecast_data = await self.get_forecast(lat, lon, units)
                return {
                    "source": "free_tier",
                    "forecast_list": [f.model_dump() for f in forecast_data.forecast_list],
                    "city": forecast_data.city.model_dump(),
                    "alerts": [],
                    "note": "Hourly forecast and alerts require One Call API subscription",
                }
            raise
