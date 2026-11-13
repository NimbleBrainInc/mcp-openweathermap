"""
OpenWeatherMap MCP Server
Provides intent-based tools for accessing weather data, forecasts, and air quality.
"""

import logging
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from importlib.resources import files
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .api_client import OpenWeatherMapAPIError, OpenWeatherMapClient

# Diagnostics go to stderr (stdout is reserved for JSON-RPC), never to the client: MCP's
# logging capability is deprecated as of the 2026-07-28 protocol (SEP-2577). A failure the
# caller must see is raised as a ToolError.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp_openweathermap")

# Initialize FastMCP server
mcp = FastMCP(
    "OpenWeatherMap MCP Server",
    instructions=(
        "Before using OpenWeatherMap tools, read the skill://openweathermap/usage resource "
        "for location resolution patterns and tool selection."
    ),
)


SKILL_CONTENT = files("mcp_openweathermap").joinpath("SKILL.md").read_text()


@mcp.resource("skill://openweathermap/usage")
def openweathermap_skill() -> str:
    """How to effectively use OpenWeatherMap tools: location resolution, disambiguation, tool selection."""
    return SKILL_CONTENT


# Singleton client instance
_client: OpenWeatherMapClient | None = None


def get_client() -> OpenWeatherMapClient:
    """Get or create the singleton API client.

    Raises:
        ToolError: when OPENWEATHERMAP_API_KEY is not set, so the caller sees why the tool
            failed.
    """
    global _client
    if _client is None:
        api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
        if not api_key:
            logger.error("OPENWEATHERMAP_API_KEY is not set")
            raise ToolError("OPENWEATHERMAP_API_KEY environment variable is required")
        _client = OpenWeatherMapClient(api_key=api_key)
    return _client


@contextmanager
def surface_api_errors(tool: str) -> Iterator[None]:
    """Report an OpenWeatherMap API failure to the caller as a ToolError."""
    try:
        yield
    except OpenWeatherMapAPIError as e:
        logger.warning("%s failed: %s", tool, e)
        raise ToolError(str(e)) from e


async def resolve_coordinates(
    client: OpenWeatherMapClient,
    location: str | None,
    lat: float | None,
    lon: float | None,
) -> tuple[float, float]:
    """Resolve location string or lat/lon to coordinates.

    Raises OpenWeatherMapAPIError with helpful message if resolution fails.
    """
    if lat is not None and lon is not None:
        return lat, lon

    if location is None:
        raise OpenWeatherMapAPIError(
            400, "Provide either 'location' string or 'lat'/'lon' coordinates"
        )

    try:
        return await client.resolve_location(location)
    except OpenWeatherMapAPIError as e:
        if e.status == 404:
            raise OpenWeatherMapAPIError(
                404,
                f"Location not found: {location}. "
                "Try search_location with a simpler query (e.g., just city name).",
            ) from e
        raise


# Health endpoint for HTTP transport
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for container monitoring."""
    return JSONResponse({"status": "healthy", "service": "mcp-openweathermap"})


@mcp.tool()
async def search_location(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Resolve location query to coordinates. Returns candidate matches.

    Use when:
    - Location lookup fails in other tools
    - Query is ambiguous (e.g., 'Springfield' exists in many states)
    - Need to disambiguate (e.g., 'Waimea' has 2 locations in Hawaii)

    Args:
        query: Location search query (city name, landmark, etc.)
        limit: Max results to return (default 5)

    Returns:
        List of matching locations with name, state, country, lat, lon
    """
    with surface_api_errors("search_location"):
        client = get_client()
        async with client:
            results = await client.geocode_location(query, limit=limit)
            return [
                {
                    "name": r.name,
                    "state": r.state,
                    "country": r.country,
                    "lat": r.lat,
                    "lon": r.lon,
                }
                for r in results
            ]


@mcp.tool()
async def check_weather(
    location: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    units: str = "metric",
) -> dict[str, Any]:
    """Get current weather conditions.

    Pass location string OR lat/lon coordinates.
    If location lookup fails, use search_location to resolve first.

    Args:
        location: City name (e.g., 'London', 'Tokyo')
        lat: Latitude (use with lon instead of location)
        lon: Longitude (use with lat instead of location)
        units: 'metric' (Celsius), 'imperial' (Fahrenheit), 'standard' (Kelvin)

    Returns:
        Current temperature, humidity, wind, weather conditions
    """
    with surface_api_errors("check_weather"):
        client = get_client()
        async with client:
            resolved_lat, resolved_lon = await resolve_coordinates(client, location, lat, lon)
            weather = await client.get_current_weather(resolved_lat, resolved_lon, units)
            return weather.model_dump()


@mcp.tool()
async def get_forecast(
    location: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    units: str = "metric",
) -> dict[str, Any]:
    """Get weather forecast (hourly/daily with alerts if subscribed, else 5-day/3h).

    Pass location string OR lat/lon coordinates.
    If location lookup fails, use search_location to resolve first.

    Args:
        location: City name (e.g., 'London', 'Tokyo')
        lat: Latitude (use with lon instead of location)
        lon: Longitude (use with lat instead of location)
        units: 'metric' (Celsius), 'imperial' (Fahrenheit), 'standard' (Kelvin)

    Returns:
        Forecast data with 'source' field ('one_call' or 'free_tier')
    """
    with surface_api_errors("get_forecast"):
        client = get_client()
        async with client:
            resolved_lat, resolved_lon = await resolve_coordinates(client, location, lat, lon)
            return await client.get_forecast_with_fallback(resolved_lat, resolved_lon, units)


@mcp.tool()
async def check_air_quality(
    location: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, Any]:
    """Get air quality index and pollutant levels.

    Pass location string OR lat/lon coordinates.
    If location lookup fails, use search_location to resolve first.

    Args:
        location: City name (e.g., 'London', 'Tokyo')
        lat: Latitude (use with lon instead of location)
        lon: Longitude (use with lat instead of location)

    Returns:
        AQI (1=Good to 5=Very Poor) and pollutant concentrations
    """
    with surface_api_errors("check_air_quality"):
        client = get_client()
        async with client:
            resolved_lat, resolved_lon = await resolve_coordinates(client, location, lat, lon)
            data = await client.get_air_quality(resolved_lat, resolved_lon)
            return data.model_dump()


@mcp.tool()
async def get_historical_weather(
    date: str,
    location: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    units: str = "metric",
) -> dict[str, Any]:
    """Get historical weather for a past date (requires One Call API subscription).

    Pass location string OR lat/lon coordinates.
    If location lookup fails, use search_location to resolve first.

    Args:
        date: Date in YYYY-MM-DD format (last ~5 days)
        location: City name (e.g., 'London', 'Tokyo')
        lat: Latitude (use with lon instead of location)
        lon: Longitude (use with lat instead of location)
        units: 'metric' (Celsius), 'imperial' (Fahrenheit), 'standard' (Kelvin)

    Returns:
        Historical weather data or subscription error
    """
    with surface_api_errors("get_historical_weather"):
        client = get_client()
        async with client:
            resolved_lat, resolved_lon = await resolve_coordinates(client, location, lat, lon)

            try:
                dt = int(datetime.strptime(date, "%Y-%m-%d").timestamp())
            except ValueError as e:
                return {"error": f"Invalid date format. Use YYYY-MM-DD. {e}"}

            try:
                data = await client.get_one_call_timemachine(resolved_lat, resolved_lon, dt, units)
                return {"source": "one_call", **data.model_dump()}
            except OpenWeatherMapAPIError as e:
                if e.status in (401, 403):
                    return {
                        "error": "Historical weather requires One Call API subscription",
                        "subscription_url": "https://openweathermap.org/api/one-call-3",
                    }
                raise


# Create ASGI application for uvicorn
app = mcp.http_app()


if __name__ == "__main__":
    mcp.run()
