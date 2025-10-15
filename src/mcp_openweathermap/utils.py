"""Utility functions for OpenWeatherMap MCP server."""

import math
from typing import Any

from .api_models import Coordinates, SolarRadiationData

# Panama location presets with coordinates
PANAMA_LOCATIONS: dict[str, dict[str, float]] = {
    "Panama City": {"lat": 8.9824, "lon": -79.5199},
    "David": {"lat": 8.4270, "lon": -82.4278},
    "Colón": {"lat": 9.3592, "lon": -79.9009},
    "Santiago": {"lat": 8.1000, "lon": -80.9833},
    "Chitré": {"lat": 7.9614, "lon": -80.4289},
    "La Chorrera": {"lat": 8.8800, "lon": -79.7833},
    "Bocas del Toro": {"lat": 9.3400, "lon": -82.2400},
    "Penonomé": {"lat": 8.5167, "lon": -80.3500},
}


def parse_location_name(location: str) -> dict[str, float] | None:
    """Parse a location name and return coordinates if it's a known Panama location.

    Args:
        location: Location name to parse

    Returns:
        Dictionary with lat/lon if found, None otherwise
    """
    # Check exact match first
    if location in PANAMA_LOCATIONS:
        return PANAMA_LOCATIONS[location]

    # Check case-insensitive match
    location_lower = location.lower()
    for name, coords in PANAMA_LOCATIONS.items():
        if name.lower() == location_lower:
            return coords

    # Check partial match
    for name, coords in PANAMA_LOCATIONS.items():
        if location_lower in name.lower() or name.lower() in location_lower:
            return coords

    return None


def calculate_solar_radiation_from_weather(
    lat: float,
    cloud_cover: float,
    uv_index: float | None = None,
    month: int | None = None,
) -> dict[str, float]:
    """Calculate solar radiation data from weather parameters.

    This is an approximation based on:
    - Latitude (affects solar angle and day length)
    - Cloud cover (reduces solar radiation)
    - UV index (correlates with solar radiation)
    - Month/season (affects solar angle)

    Args:
        lat: Latitude coordinate
        cloud_cover: Cloud cover percentage (0-100)
        uv_index: UV index value (optional)
        month: Month number 1-12 (optional, for seasonal adjustment)

    Returns:
        Dictionary with solar radiation estimates
    """
    # Base solar radiation at given latitude (kWh/m²/day)
    # Tropical latitudes (0-23.5°) have high solar radiation year-round
    abs_lat = abs(lat)

    # Base radiation by latitude zone
    if abs_lat < 10:
        base_radiation = 5.8  # Equatorial zone
    elif abs_lat < 23.5:
        base_radiation = 5.5  # Tropical zone
    elif abs_lat < 35:
        base_radiation = 4.5  # Subtropical zone
    else:
        base_radiation = 3.5  # Temperate zone

    # Seasonal adjustment if month is provided
    if month is not None:
        # Northern hemisphere: June (6) is peak, December (12) is minimum
        # Southern hemisphere: opposite
        if lat >= 0:  # Northern hemisphere
            seasonal_factor = 1 + 0.3 * math.cos((month - 6) * math.pi / 6)
        else:  # Southern hemisphere
            seasonal_factor = 1 + 0.3 * math.cos((month - 12) * math.pi / 6)
        base_radiation *= seasonal_factor

    # Cloud cover reduction factor (0-100% clouds)
    cloud_factor = 1 - (cloud_cover / 100) * 0.75  # Clouds reduce by up to 75%

    # UV index adjustment (if available)
    uv_factor = 1.0
    if uv_index is not None:
        # UV index correlates with solar radiation
        # UV 0-2: Low, 3-5: Moderate, 6-7: High, 8-10: Very High, 11+: Extreme
        # Adjust radiation based on UV index
        uv_factor = min(1.5, 0.7 + (uv_index * 0.08))  # Scale from 0.7 to 1.5

    # Calculate adjusted radiation
    avg_daily_kwh_m2 = base_radiation * cloud_factor * uv_factor

    # Peak sun hours is approximately equal to kWh/m²/day
    peak_sun_hours = avg_daily_kwh_m2

    return {
        "avg_daily_kwh_m2": round(avg_daily_kwh_m2, 2),
        "peak_sun_hours": round(peak_sun_hours, 2),
        "cloud_cover_factor": round(cloud_factor, 3),
        "uv_factor": round(uv_factor, 3),
    }


def calculate_monthly_solar_averages(
    lat: float, annual_avg_cloud_cover: float = 50.0
) -> dict[str, float]:
    """Calculate monthly solar radiation averages based on latitude.

    Args:
        lat: Latitude coordinate
        annual_avg_cloud_cover: Annual average cloud cover percentage (default: 50%)

    Returns:
        Dictionary with monthly averages (January through December)
    """
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

    monthly_data = {}
    for month_num, month_name in enumerate(months, start=1):
        radiation_data = calculate_solar_radiation_from_weather(
            lat=lat, cloud_cover=annual_avg_cloud_cover, month=month_num
        )
        monthly_data[month_name] = radiation_data["avg_daily_kwh_m2"]

    return monthly_data


def create_solar_radiation_response(
    location: str,
    lat: float,
    lon: float,
    cloud_cover: float,
    uv_index: float | None = None,
    month: int | None = None,
) -> SolarRadiationData:
    """Create a Solar5Estrella-formatted solar radiation response.

    Args:
        location: Location name
        lat: Latitude coordinate
        lon: Longitude coordinate
        cloud_cover: Cloud cover percentage (0-100)
        uv_index: UV index value (optional)
        month: Current month 1-12 (optional)

    Returns:
        SolarRadiationData object formatted for Solar5Estrella integration
    """
    # Calculate current solar radiation
    radiation_data = calculate_solar_radiation_from_weather(
        lat=lat, cloud_cover=cloud_cover, uv_index=uv_index, month=month
    )

    # Calculate monthly averages
    monthly_averages = calculate_monthly_solar_averages(lat=lat, annual_avg_cloud_cover=cloud_cover)

    return SolarRadiationData(
        location=location,
        coordinates=Coordinates(lat=lat, lon=lon),
        avg_daily_kwh_m2=radiation_data["avg_daily_kwh_m2"],
        peak_sun_hours=radiation_data["peak_sun_hours"],
        monthly_averages=monthly_averages,
        source="OpenWeatherMap",
        cloud_cover_factor=radiation_data.get("cloud_cover_factor"),
        uv_index_avg=uv_index,
    )


def format_weather_for_solar(weather_data: dict[str, Any], location: str) -> SolarRadiationData:
    """Format weather data into Solar5Estrella solar radiation format.

    Args:
        weather_data: Current weather data from OpenWeatherMap
        location: Location name

    Returns:
        SolarRadiationData object
    """
    lat = weather_data.get("coord", {}).get("lat", 0.0)
    lon = weather_data.get("coord", {}).get("lon", 0.0)
    cloud_cover = weather_data.get("clouds", {}).get("all", 50.0)

    return create_solar_radiation_response(
        location=location,
        lat=lat,
        lon=lon,
        cloud_cover=float(cloud_cover),
        uv_index=None,  # UV index not available in basic weather data
        month=None,
    )
