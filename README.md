# OpenWeatherMap MCP Server

[![NimbleTools Registry](https://img.shields.io/badge/NimbleTools-Registry-green)](https://github.com/nimbletoolsinc/mcp-registry)
[![NimbleBrain Platform](https://img.shields.io/badge/NimbleBrain-Platform-blue)](https://www.nimblebrain.ai)
[![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?logo=discord&logoColor=white)](https://www.nimblebrain.ai/discord?utm_source=github&utm_medium=readme&utm_campaign=mcp-abstract&utm_content=discord-badge)

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/NimbleBrainInc/mcp-abstract/actions/workflows/ci.yaml/badge.svg)](https://github.com/NimbleBrainInc/mcp-openweathermap/actions)


## About

Production-ready MCP server for accessing comprehensive weather data from OpenWeatherMap.

## Features

- **Enterprise ready**: Production-ready with separation of concerns, strong typing, and comprehensive testing
- **Full API Coverage**: Current weather, forecasts, air quality, UV index
- **Strongly Typed**: All responses use Pydantic models with full type safety
- **HTTP & Stdio Transport**: Supports both streamable-http and stdio for Claude Desktop
- **Async/Await**: Built on aiohttp for high performance
- **Type Safe**: Full mypy strict mode compliance
- **Comprehensive Tests**: 100% coverage with pytest + AsyncMock
- **Panama Locations**: Built-in coordinates for major Panama cities

## Architecture

```
src/mcp_openweathermap/
├── __init__.py          # Package exports
├── server.py            # FastMCP server with 6 MCP tools
├── api_client.py        # OpenWeatherMapClient with aiohttp
├── api_models.py        # Pydantic models for type safety
└── utils.py             # Helper functions and solar calculations

tests/
├── test_server.py       # MCP tool tests
└── test_api_client.py   # API client tests
```

## Installation

### Prerequisites

- Python >=3.10
- OpenWeatherMap API key from [openweathermap.org](https://openweathermap.org/api)

### Using uv (recommended)

```bash
# Install dependencies
uv pip install -e .

# Install with dev dependencies
uv pip install -e . --group dev
```

### Using pip

```bash
pip install -e .
```

## Configuration

Set your API key as an environment variable:

```bash
export OPENWEATHERMAP_API_KEY=your_api_key_here
```

Or create a `.env` file:

```
OPENWEATHERMAP_API_KEY=your_api_key_here
```

## Running the Server

### Stdio Mode (for Claude Desktop)

```bash
# Using make
make run

# Or directly
uv run python -m mcp_openweathermap.server
```

### HTTP Mode (for web applications)

```bash
# Using make
make run-http

# Or directly
uv run uvicorn mcp_openweathermap.server:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Build image
make docker-build

# Run container
make docker-run OPENWEATHERMAP_API_KEY=your_key

# Or using docker directly
docker build -t mcp-openweathermap .
docker run -p 8000:8000 -e OPENWEATHERMAP_API_KEY=your_key mcp-openweathermap
```

## Available MCP Tools

### 1. `get_current_weather`

Get current weather conditions for a location.

**Parameters:**
- `location` (str, optional): Location name (e.g., 'Panama City', 'London,GB')
- `lat` (float, optional): Latitude coordinate (use with lon)
- `lon` (float, optional): Longitude coordinate (use with lat)
- `units` (str, default='metric'): Units ('metric', 'imperial', 'standard')

**Returns:** Current weather data including temperature, humidity, pressure, wind, clouds

**Example:**
```python
# By location name
get_current_weather(location="Panama City")

# By coordinates
get_current_weather(lat=8.9824, lon=-79.5199)
```

### 2. `get_weather_forecast`

Get 5-day weather forecast with 3-hour intervals.

**Parameters:**
- `location` (str, optional): Location name
- `lat` (float, optional): Latitude coordinate (use with lon)
- `lon` (float, optional): Longitude coordinate (use with lat)
- `units` (str, default='metric'): Units
- `days` (int, optional): Number of days to forecast (max: 5)

**Returns:** 5-day forecast data with 3-hour intervals

### 3. `get_air_quality`

Get air quality index and pollutant concentrations.

**Parameters:**
- `location` (str, optional): Location name
- `lat` (float, optional): Latitude coordinate (use with lon)
- `lon` (float, optional): Longitude coordinate (use with lat)

**Returns:** Air quality data with AQI (1=Good to 5=Very Poor) and pollutant levels (CO, NO, NO2, O3, SO2, PM2.5, PM10, NH3)

### 4. `get_uv_index`

Get UV index for a location.

**Parameters:**
- `location` (str, optional): Location name
- `lat` (float, optional): Latitude coordinate (use with lon)
- `lon` (float, optional): Longitude coordinate (use with lat)

**Returns:** UV index data (0-2: Low, 3-5: Moderate, 6-7: High, 8-10: Very High, 11+: Extreme)

### 5. `get_solar_radiation`

Get solar radiation data for solar energy calculations.

**Parameters:**
- `location` (str, optional): Location name
- `lat` (float, optional): Latitude coordinate (use with lon)
- `lon` (float, optional): Longitude coordinate (use with lat)

**Returns:** Solar radiation data including:
- `avg_daily_kwh_m2`: Average daily solar radiation (kWh/m²)
- `peak_sun_hours`: Equivalent peak sun hours per day
- `monthly_averages`: Monthly solar radiation estimates for all 12 months
- `coordinates`: Location coordinates
- `cloud_cover_factor`: Cloud cover reduction factor
- `uv_index_avg`: Average UV index

**Response Format:**
```json
{
  "location": "Panama City, Panama",
  "coordinates": {"lat": 8.9824, "lon": -79.5199},
  "avg_daily_kwh_m2": 5.2,
  "peak_sun_hours": 5.2,
  "monthly_averages": {
    "january": 5.8,
    "february": 6.1,
    ...
  },
  "source": "OpenWeatherMap"
}
```

### 6. `get_location_coordinates`

Convert location name to geographic coordinates.

**Parameters:**
- `location` (str, required): Location name

**Returns:** Coordinates and location information including lat, lon, country

**Supports:**
- Known Panama locations (Panama City, David, Colón, Santiago, Chitré, La Chorrera, Bocas del Toro, Penonomé)
- Any city worldwide via OpenWeatherMap geocoding

## Panama Location Presets

The server includes built-in coordinates for major Panama cities:

| City | Latitude | Longitude |
|------|----------|-----------|
| Panama City | 8.9824 | -79.5199 |
| David | 8.4270 | -82.4278 |
| Colón | 9.3592 | -79.9009 |
| Santiago | 8.1000 | -80.9833 |
| Chitré | 7.9614 | -80.4289 |
| La Chorrera | 8.8800 | -79.7833 |
| Bocas del Toro | 9.3400 | -82.2400 |
| Penonomé | 8.5167 | -80.3500 |

## Development

### Available Make Commands

```bash
make help          # Show all commands
make install       # Install dependencies
make dev-install   # Install with dev dependencies
make format        # Format code with ruff
make lint          # Lint code with ruff
make lint-fix      # Lint and auto-fix issues
make typecheck     # Type check with mypy
make test          # Run tests
make test-cov      # Run tests with coverage
make clean         # Clean up artifacts
make run           # Run server (stdio)
make run-http      # Run server (HTTP)
make check         # Run all checks (lint + typecheck + test)
make all           # Full workflow
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
uv run pytest tests/test_server.py -v

# Run specific test
uv run pytest tests/test_server.py::TestMCPTools::test_get_solar_radiation -v
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Type check
make typecheck

# Run all quality checks
make check
```

## Solar Radiation Calculations

The `get_solar_radiation` tool calculates solar radiation using:

1. **Latitude**: Affects solar angle and day length
   - Equatorial (0-10°): 5.8 kWh/m²/day base
   - Tropical (10-23.5°): 5.5 kWh/m²/day base
   - Subtropical (23.5-35°): 4.5 kWh/m²/day base

2. **Cloud Cover**: Reduces solar radiation by up to 75%
   - Clear sky (0% clouds): Full radiation
   - Overcast (100% clouds): 25% radiation

3. **UV Index**: Correlates with solar intensity
   - Used as adjustment factor (0.7-1.5x)

4. **Seasonal Patterns**: Monthly variation based on latitude
   - Northern hemisphere: Peak in June
   - Southern hemisphere: Peak in December

Formula:
```
radiation = base_radiation × (1 - cloud_cover × 0.75) × uv_factor × seasonal_factor
```

## API Documentation

For detailed OpenWeatherMap API documentation:
- [API Documentation](https://openweathermap.org/api)
- [Current Weather](https://openweathermap.org/current)
- [5-day Forecast](https://openweathermap.org/forecast5)
- [Air Pollution API](https://openweathermap.org/api/air-pollution)
- [UV Index](https://openweathermap.org/api/uvi)

## Requirements

- Python >=3.10
- aiohttp >=3.12.15
- fastapi >=0.117.1
- fastmcp >=2.12.4
- pydantic >=2.0.0
- uvicorn >=0.32.1

## Rate Limits

### Free Tier
- 1,000 calls/day
- 60 calls/minute
- Current weather and 5-day forecast
- Air pollution data
- UV index

For higher limits, see [OpenWeatherMap pricing](https://openweathermap.org/price).

## Health Check

When running in HTTP mode, a health check endpoint is available:

```bash
curl http://localhost:8000/health
# {"status": "healthy", "service": "openweathermap-mcp"}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `make check` to ensure quality
5. Submit a pull request

## Support

For issues or questions:
- OpenWeatherMap API: [support.openweathermap.org](https://support.openweathermap.org)
- MCP Server: Create an issue in the repository

## License

MIT

## Links

Part of the [NimbleTools Registry](https://github.com/nimbletoolsinc/mcp-registry) - an open source collection of production-ready MCP servers. For enterprise deployment, check out [NimbleBrain](https://www.nimblebrain.ai).

- [OpenWeather Map API](https://openweathermap.org/api)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Documentation](https://modelcontextprotocol.io)