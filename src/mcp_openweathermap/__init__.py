"""OpenWeatherMap MCP Server - Intent-based weather tools."""

from .api_client import OpenWeatherMapAPIError, OpenWeatherMapClient
from .api_models import (
    AirQualityResponse,
    CurrentWeatherResponse,
    ForecastResponse,
    GeocodingResult,
    OneCallResponse,
    SolarRadiationData,
)
from .server import app, mcp

__version__ = "0.4.0"

__all__ = [
    "OpenWeatherMapClient",
    "OpenWeatherMapAPIError",
    "CurrentWeatherResponse",
    "ForecastResponse",
    "AirQualityResponse",
    "OneCallResponse",
    "SolarRadiationData",
    "GeocodingResult",
    "app",
    "mcp",
]
