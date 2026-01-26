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

- **Hybrid Tool Design**: 5 tools balancing convenience with LLM reasoning capability
- **Graceful Degradation**: Automatically uses One Call API when available, falls back to free tier
- **Smart Fallback Pattern**: When location lookup fails, error message guides LLM to use `search_location`
- **Flexible Input**: All weather tools accept either location string OR direct lat/lon coordinates
- **Strongly Typed**: All responses use Pydantic models with full type safety
- **HTTP & Stdio Transport**: Supports both streamable-http and stdio for Claude Desktop
- **Async/Await**: Built on aiohttp for high performance
- **Type Safe**: Full mypy strict mode compliance
- **Comprehensive Tests**: Full coverage with pytest + AsyncMock

## Architecture

```
src/mcp_openweathermap/
├── __init__.py          # Package exports
├── server.py            # FastMCP server with 4 intent-based tools
├── api_client.py        # OpenWeatherMapClient with graceful degradation
├── api_models.py        # Pydantic models for type safety
└── utils.py             # Helper functions

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

### 1. `search_location`

Resolve location query to coordinates. Use when direct location lookup fails or for ambiguous queries.

**Parameters:**
- `query` (str): Location search query (city name, landmark, etc.)
- `limit` (int, default=5): Max results to return

**Returns:** List of matching locations with name, state, country, lat, lon

**Example:**
```python
# Disambiguate "Springfield" (exists in many US states)
search_location(query="Springfield")
# Returns multiple candidates - LLM picks the right one

# Find Waimea in Hawaii (direct lookup fails for "Waimea, HI")
search_location(query="Waimea")
# Returns candidates in Hawaii and elsewhere
```

### 2. `check_weather`

Get current weather conditions. Pass location string OR lat/lon coordinates.

**Parameters:**
- `location` (str, optional): City name (e.g., 'London', 'Tokyo')
- `lat` (float, optional): Latitude (use with lon instead of location)
- `lon` (float, optional): Longitude (use with lat instead of location)
- `units` (str, default='metric'): Temperature units ('metric', 'imperial', 'standard')

**Returns:** Current temperature, humidity, wind, weather conditions, and location info

**Example:**
```python
# By city name (fast path)
check_weather(location="London")

# By coordinates (precise path - use after search_location)
check_weather(lat=20.02, lon=-155.66)

# With imperial units
check_weather(location="Tokyo", units="imperial")
```

**Fallback Pattern:** If location lookup fails, error suggests using `search_location` first.

### 3. `get_forecast`

Get weather forecast. Pass location string OR lat/lon coordinates.

**Parameters:**
- `location` (str, optional): City name
- `lat` (float, optional): Latitude
- `lon` (float, optional): Longitude
- `units` (str, default='metric'): Temperature units

**Returns:** Forecast data with `source` field indicating tier:
- `one_call`: Hourly (48h) + daily (8-day) forecasts with weather alerts
- `free_tier`: 5-day forecast with 3-hour intervals (automatic fallback)

**Example Response (One Call):**
```json
{
  "source": "one_call",
  "hourly": [...],
  "daily": [...],
  "alerts": [],
  "timezone": "Europe/London"
}
```

**Example Response (Free Tier Fallback):**
```json
{
  "source": "free_tier",
  "forecast_list": [...],
  "city": {"name": "London"},
  "alerts": [],
  "note": "Hourly forecast and alerts require One Call API subscription"
}
```

### 4. `check_air_quality`

Get air quality index and pollutant levels. Pass location string OR lat/lon coordinates.

**Parameters:**
- `location` (str, optional): City name
- `lat` (float, optional): Latitude
- `lon` (float, optional): Longitude

**Returns:** Air Quality Index (1=Good to 5=Very Poor) and concentrations of CO, NO, NO2, O3, SO2, PM2.5, PM10, NH3

### 5. `get_historical_weather`

Get historical weather data for a past date. Requires One Call API subscription.

**Parameters:**
- `date` (str, required): Date in YYYY-MM-DD format (within approximately last 5 days)
- `location` (str, optional): City name
- `lat` (float, optional): Latitude
- `lon` (float, optional): Longitude
- `units` (str, default='metric'): Temperature units

**Returns:** Historical weather data or helpful error if subscription not available

**Example Response (Success):**
```json
{
  "source": "one_call",
  "lat": 51.5,
  "lon": -0.1,
  "timezone": "Europe/London",
  "current": {"temp": 12.5, ...}
}
```

**Example Response (No Subscription):**
```json
{
  "error": "Historical weather requires One Call API subscription",
  "subscription_url": "https://openweathermap.org/api/one-call-3"
}
```

## LLM Fallback Pattern

The tools are designed so that when direct location lookup fails, the LLM can reason about alternatives:

1. **Try direct**: `check_weather(location="Waimea, HI")` → fails with hint
2. **Search**: `search_location(query="Waimea")` → returns candidates
3. **Pick & retry**: `check_weather(lat=20.02, lon=-155.66)` → succeeds

This pattern handles:
- US state abbreviations ("HI" vs "Hawaii")
- Country code variations ("UK" vs "GB")
- Ambiguous locations (multiple "Springfield"s)

## API Tiers

| Feature | Free Tier | One Call API |
|---------|-----------|--------------|
| Current weather | Yes | Yes |
| 5-day/3-hour forecast | Yes | Yes |
| Hourly forecast (48h) | No | Yes |
| Daily forecast (8 days) | No | Yes |
| Weather alerts | No | Yes |
| Historical data | No | Yes |
| Air quality | Yes | Yes |
| Rate limit | 1M calls/month | 1000 free/day |

The server automatically detects your API tier and uses the best available data.

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

## API Documentation

For detailed OpenWeatherMap API documentation:
- [API Overview](https://openweathermap.org/api)
- [Current Weather](https://openweathermap.org/current)
- [5-day Forecast](https://openweathermap.org/forecast5)
- [One Call API 3.0](https://openweathermap.org/api/one-call-3)
- [Air Pollution API](https://openweathermap.org/api/air-pollution)

## Requirements

- Python >=3.10
- aiohttp >=3.12.15
- fastapi >=0.117.1
- fastmcp >=2.12.4
- pydantic >=2.0.0
- uvicorn >=0.32.1

## Rate Limits

- **Free Tier**: 1,000,000 calls/month, 60 calls/minute
- **One Call API**: 1,000 free calls/day, then pay-per-call

For pricing details, see [OpenWeatherMap pricing](https://openweathermap.org/price).

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