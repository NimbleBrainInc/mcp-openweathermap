# OpenWeatherMap Integration

## Location Resolution Pattern

**When location lookup fails, use search then coordinates.**

The geocoding API rejects US state abbreviations and some country codes. When `check_weather(location=<user_query>)` returns "Location not found":

1. Call `search_location(query=<simplified_query>)` with just the city name
2. If multiple results, ask user which one they meant
3. Retry with coordinates from the selected result

All weather tools accept either `location=` string OR `lat=`/`lon=` coordinates. Coordinates always work.

## Disambiguation Rule

When `search_location` returns multiple matches, **always ask user to choose**. Never guess between results.

## Tool Overview

| Tool | Purpose |
|------|---------|
| `search_location` | Resolve ambiguous locations to coordinates |
| `check_weather` | Current conditions |
| `get_forecast` | Hourly/daily forecast |
| `check_air_quality` | AQI and pollutants |
| `get_historical_weather` | Past weather (subscription required) |

## Response Source Field

Forecast responses include `source`:
- `one_call` - Rich data (hourly, daily, alerts)
- `free_tier` - Basic data (3-hour intervals)

Historical weather requires One Call subscription. Communicate gracefully if unavailable.
