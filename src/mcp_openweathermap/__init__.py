"""OpenWeatherMap MCP Server - S-Tier Architecture."""

from .api_client import OpenWeatherMapAPIError, OpenWeatherMapClient
from .api_models import (
    AirQualityResponse,
    CurrentWeatherResponse,
    ForecastResponse,
    GeocodingResult,
    OneCallResponse,
    SolarRadiationData,
    UVIndexResponse,
)
from .server import app, mcp

__version__ = "1.0.0"

__all__ = [
    "OpenWeatherMapClient",
    "OpenWeatherMapAPIError",
    "CurrentWeatherResponse",
    "ForecastResponse",
    "AirQualityResponse",
    "UVIndexResponse",
    "OneCallResponse",
    "SolarRadiationData",
    "GeocodingResult",
    "app",
    "mcp",
]
