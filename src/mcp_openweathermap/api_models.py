"""Pydantic models for OpenWeatherMap API responses."""

from typing import Any
from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """Geographic coordinates."""

    lon: float = Field(..., description="Longitude")
    lat: float = Field(..., description="Latitude")


class WeatherCondition(BaseModel):
    """Weather condition details."""

    id: int = Field(..., description="Weather condition ID")
    main: str = Field(..., description="Weather condition group (Rain, Snow, Clouds, etc.)")
    description: str = Field(..., description="Weather condition description")
    icon: str = Field(..., description="Weather icon ID")


class Temperature(BaseModel):
    """Temperature data."""

    temp: float = Field(..., description="Current temperature")
    feels_like: float = Field(..., description="Feels like temperature")
    temp_min: float = Field(..., description="Minimum temperature")
    temp_max: float = Field(..., description="Maximum temperature")
    pressure: int = Field(..., description="Atmospheric pressure (hPa)")
    humidity: int = Field(..., description="Humidity percentage")
    sea_level: int | None = Field(None, description="Sea level atmospheric pressure (hPa)")
    grnd_level: int | None = Field(None, description="Ground level atmospheric pressure (hPa)")


class Wind(BaseModel):
    """Wind data."""

    speed: float = Field(..., description="Wind speed")
    deg: int | None = Field(None, description="Wind direction in degrees")
    gust: float | None = Field(None, description="Wind gust speed")


class Clouds(BaseModel):
    """Cloud data."""

    all: int = Field(..., description="Cloudiness percentage")


class Rain(BaseModel):
    """Rain data."""

    one_hour: float | None = Field(None, alias="1h", description="Rain volume for last 1 hour (mm)")
    three_hour: float | None = Field(
        None, alias="3h", description="Rain volume for last 3 hours (mm)"
    )


class Snow(BaseModel):
    """Snow data."""

    one_hour: float | None = Field(None, alias="1h", description="Snow volume for last 1 hour (mm)")
    three_hour: float | None = Field(
        None, alias="3h", description="Snow volume for last 3 hours (mm)"
    )


class SystemData(BaseModel):
    """System data."""

    type: int | None = Field(None, description="Internal parameter")
    id: int | None = Field(None, description="Internal parameter")
    country: str | None = Field(None, description="Country code (GB, JP, etc.)")
    sunrise: int | None = Field(None, description="Sunrise time (Unix, UTC)")
    sunset: int | None = Field(None, description="Sunset time (Unix, UTC)")


class CurrentWeatherResponse(BaseModel):
    """Response model for current weather endpoint."""

    coord: Coordinates = Field(..., description="Geographic coordinates")
    weather: list[WeatherCondition] = Field(..., description="Weather conditions")
    base: str | None = Field(None, description="Internal parameter")
    main: Temperature = Field(..., description="Temperature and atmospheric data")
    visibility: int | None = Field(None, description="Visibility in meters")
    wind: Wind = Field(..., description="Wind data")
    clouds: Clouds = Field(..., description="Cloud data")
    rain: Rain | None = Field(None, description="Rain data")
    snow: Snow | None = Field(None, description="Snow data")
    dt: int = Field(..., description="Data calculation time (Unix, UTC)")
    sys: SystemData = Field(..., description="System data")
    timezone: int = Field(..., description="Timezone offset from UTC in seconds")
    id: int = Field(..., description="City ID")
    name: str = Field(..., description="City name")
    cod: int = Field(..., description="HTTP status code")


class ForecastItem(BaseModel):
    """Individual forecast data point."""

    dt: int = Field(..., description="Data calculation time (Unix, UTC)")
    main: Temperature = Field(..., description="Temperature and atmospheric data")
    weather: list[WeatherCondition] = Field(..., description="Weather conditions")
    clouds: Clouds = Field(..., description="Cloud data")
    wind: Wind = Field(..., description="Wind data")
    visibility: int | None = Field(None, description="Visibility in meters")
    pop: float | None = Field(None, description="Probability of precipitation (0-1)")
    rain: Rain | None = Field(None, description="Rain data")
    snow: Snow | None = Field(None, description="Snow data")
    sys: dict[str, Any] | None = Field(None, description="System data")
    dt_txt: str | None = Field(None, description="Forecast time in text format")


class City(BaseModel):
    """City information in forecast."""

    id: int = Field(..., description="City ID")
    name: str = Field(..., description="City name")
    coord: Coordinates = Field(..., description="Geographic coordinates")
    country: str = Field(..., description="Country code")
    population: int | None = Field(None, description="City population")
    timezone: int = Field(..., description="Timezone offset from UTC in seconds")
    sunrise: int = Field(..., description="Sunrise time (Unix, UTC)")
    sunset: int = Field(..., description="Sunset time (Unix, UTC)")


class ForecastResponse(BaseModel):
    """Response model for 5-day/3-hour forecast endpoint."""

    cod: str = Field(..., description="HTTP status code")
    message: int | None = Field(None, description="Internal parameter")
    cnt: int = Field(..., description="Number of forecast items")
    forecast_list: list[ForecastItem] = Field(..., alias="list", description="Forecast data points")
    city: City = Field(..., description="City information")


class AirQualityComponents(BaseModel):
    """Air quality pollutant components."""

    co: float = Field(..., description="Carbon monoxide (μg/m³)")
    no: float = Field(..., description="Nitrogen monoxide (μg/m³)")
    no2: float = Field(..., description="Nitrogen dioxide (μg/m³)")
    o3: float = Field(..., description="Ozone (μg/m³)")
    so2: float = Field(..., description="Sulphur dioxide (μg/m³)")
    pm2_5: float = Field(..., alias="pm2_5", description="Fine particles (μg/m³)")
    pm10: float = Field(..., description="Coarse particles (μg/m³)")
    nh3: float = Field(..., description="Ammonia (μg/m³)")


class AirQualityMain(BaseModel):
    """Air quality index."""

    aqi: int = Field(..., description="Air Quality Index (1=Good, 5=Very Poor)")


class AirQualityItem(BaseModel):
    """Air quality data item."""

    main: AirQualityMain = Field(..., description="Air quality index")
    components: AirQualityComponents = Field(..., description="Pollutant concentrations")
    dt: int = Field(..., description="Data calculation time (Unix, UTC)")


class AirQualityResponse(BaseModel):
    """Response model for air quality endpoint."""

    coord: Coordinates = Field(..., description="Geographic coordinates")
    items: list[AirQualityItem] = Field(..., description="Air quality data", alias="list")


class UVIndexResponse(BaseModel):
    """Response model for UV index endpoint."""

    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    date_iso: str = Field(..., description="Date in ISO format")
    date: int = Field(..., description="Unix timestamp")
    value: float = Field(..., description="UV index value")


class MinutelyForecast(BaseModel):
    """Minutely forecast data."""

    dt: int = Field(..., description="Time (Unix, UTC)")
    precipitation: float = Field(..., description="Precipitation volume (mm)")


class HourlyForecast(BaseModel):
    """Hourly forecast data."""

    dt: int = Field(..., description="Time (Unix, UTC)")
    temp: float = Field(..., description="Temperature")
    feels_like: float = Field(..., description="Feels like temperature")
    pressure: int = Field(..., description="Atmospheric pressure (hPa)")
    humidity: int = Field(..., description="Humidity percentage")
    dew_point: float = Field(..., description="Dew point temperature")
    uvi: float = Field(..., description="UV index")
    clouds: int = Field(..., description="Cloudiness percentage")
    visibility: int = Field(..., description="Visibility in meters")
    wind_speed: float = Field(..., description="Wind speed")
    wind_deg: int = Field(..., description="Wind direction in degrees")
    wind_gust: float | None = Field(None, description="Wind gust speed")
    weather: list[WeatherCondition] = Field(..., description="Weather conditions")
    pop: float = Field(..., description="Probability of precipitation (0-1)")
    rain: dict[str, float] | None = Field(None, description="Rain data")
    snow: dict[str, float] | None = Field(None, description="Snow data")


class DailyTemperature(BaseModel):
    """Daily temperature data."""

    day: float = Field(..., description="Day temperature")
    min: float = Field(..., description="Minimum daily temperature")
    max: float = Field(..., description="Maximum daily temperature")
    night: float = Field(..., description="Night temperature")
    eve: float = Field(..., description="Evening temperature")
    morn: float = Field(..., description="Morning temperature")


class DailyFeelsLike(BaseModel):
    """Daily feels like temperature data."""

    day: float = Field(..., description="Day feels like temperature")
    night: float = Field(..., description="Night feels like temperature")
    eve: float = Field(..., description="Evening feels like temperature")
    morn: float = Field(..., description="Morning feels like temperature")


class DailyForecast(BaseModel):
    """Daily forecast data."""

    dt: int = Field(..., description="Time (Unix, UTC)")
    sunrise: int = Field(..., description="Sunrise time (Unix, UTC)")
    sunset: int = Field(..., description="Sunset time (Unix, UTC)")
    moonrise: int = Field(..., description="Moonrise time (Unix, UTC)")
    moonset: int = Field(..., description="Moonset time (Unix, UTC)")
    moon_phase: float = Field(..., description="Moon phase (0-1)")
    temp: DailyTemperature = Field(..., description="Temperature data")
    feels_like: DailyFeelsLike = Field(..., description="Feels like temperature data")
    pressure: int = Field(..., description="Atmospheric pressure (hPa)")
    humidity: int = Field(..., description="Humidity percentage")
    dew_point: float = Field(..., description="Dew point temperature")
    wind_speed: float = Field(..., description="Wind speed")
    wind_deg: int = Field(..., description="Wind direction in degrees")
    wind_gust: float | None = Field(None, description="Wind gust speed")
    weather: list[WeatherCondition] = Field(..., description="Weather conditions")
    clouds: int = Field(..., description="Cloudiness percentage")
    pop: float = Field(..., description="Probability of precipitation (0-1)")
    rain: float | None = Field(None, description="Rain volume (mm)")
    snow: float | None = Field(None, description="Snow volume (mm)")
    uvi: float = Field(..., description="UV index")


class WeatherAlert(BaseModel):
    """Weather alert data."""

    sender_name: str = Field(..., description="Alert source name")
    event: str = Field(..., description="Alert event type")
    start: int = Field(..., description="Alert start time (Unix, UTC)")
    end: int = Field(..., description="Alert end time (Unix, UTC)")
    description: str = Field(..., description="Alert description")
    tags: list[str] | None = Field(None, description="Alert tags")


class OneCallResponse(BaseModel):
    """Response model for One Call API endpoint."""

    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    timezone: str = Field(..., description="Timezone name")
    timezone_offset: int = Field(..., description="Timezone offset from UTC in seconds")
    current: dict[str, Any] | None = Field(None, description="Current weather data")
    minutely: list[MinutelyForecast] | None = Field(None, description="Minutely forecast data")
    hourly: list[HourlyForecast] | None = Field(None, description="Hourly forecast data")
    daily: list[DailyForecast] | None = Field(None, description="Daily forecast data")
    alerts: list[WeatherAlert] | None = Field(None, description="Weather alerts")


class SolarRadiationData(BaseModel):
    """Solar radiation data for Solar5Estrella integration."""

    location: str = Field(..., description="Location name")
    coordinates: Coordinates = Field(..., description="Geographic coordinates")
    avg_daily_kwh_m2: float = Field(..., description="Average daily solar radiation (kWh/m²)")
    peak_sun_hours: float = Field(..., description="Peak sun hours per day")
    monthly_averages: dict[str, float] = Field(
        ..., description="Monthly average solar radiation (kWh/m²)"
    )
    source: str = Field(default="OpenWeatherMap", description="Data source")
    cloud_cover_factor: float | None = Field(
        None, description="Average cloud cover factor (0-1)"
    )
    uv_index_avg: float | None = Field(None, description="Average UV index")


class GeocodingResult(BaseModel):
    """Geocoding result for location search."""

    name: str = Field(..., description="Location name")
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    country: str = Field(..., description="Country code")
    state: str | None = Field(None, description="State/region name")
    local_names: dict[str, str] | None = Field(None, description="Local names in different languages")
