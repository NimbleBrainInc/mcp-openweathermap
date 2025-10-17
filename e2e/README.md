# End-to-End Tests

This directory contains end-to-end (e2e) tests for the OpenWeatherMap MCP server running in Docker.

## Overview

The e2e tests verify the complete Docker deployment workflow:

1. Building the Docker image
2. Running the container with proper configuration
3. Testing the health endpoint
4. Testing MCP tool listing via the MCP SDK client
5. Testing tool execution (when API key is provided)
6. Graceful container shutdown

## Running the Tests

### Prerequisites

- Docker installed and running
- Python 3.10+ with pytest
- MCP Python SDK and requests library

### Install Dependencies

```bash
# Install e2e test dependencies
uv pip install --group e2e

# Or with pip
pip install mcp requests pytest pytest-asyncio
```

### Run the Tests

```bash
# Basic run
pytest e2e/test_e2e_docker.py -v

# With API key for full tool execution tests
OPENWEATHERMAP_API_KEY=your_api_key_here pytest e2e/test_e2e_docker.py -v

# Run specific test
pytest e2e/test_e2e_docker.py::test_health_endpoint -v
```

## Test Structure

### `test_e2e_docker.py`

Main e2e test file containing:

- **`docker_container` fixture**: Module-scoped fixture that builds the Docker image, starts the container, waits for it to be ready, and cleans up after tests complete.

- **`test_health_endpoint`**: Verifies the `/health` endpoint returns a 200 status with correct health information.

- **`test_mcp_tools_list`**: Uses the MCP Python SDK to connect to the server and verify all expected tools are registered with proper schemas.

- **`test_mcp_tool_execution`**: Tests actual tool execution (requires valid `OPENWEATHERMAP_API_KEY`).

- **`test_container_shutdown`**: Ensures the container stops gracefully.

## Configuration

The tests use these default values (defined in `test_e2e_docker.py`):

- **Image Name**: `mcp-openweathermap`
- **Container Name**: `mcp-openweathermap-test`
- **Port**: `8000`
- **Base URL**: `http://localhost:8000`

## Expected Tools

The tests verify these MCP tools are registered:

- `get_current_weather`
- `get_forecast`
- `get_hourly_forecast`
- `get_weather_alerts`
- `get_air_quality`
- `get_weather_by_zip`
- `search_city`
- `get_historical_weather`
- `get_uv_index`
- `get_weather_map`

## Troubleshooting

### Container fails to start

Check Docker logs:
```bash
docker logs mcp-openweathermap-test
```

### Tests timeout waiting for container

Increase the `max_attempts` value in the `docker_container` fixture (default: 30 seconds).

### API key errors

Make sure to set `OPENWEATHERMAP_API_KEY` environment variable:
```bash
export OPENWEATHERMAP_API_KEY=your_key_here
```

### Port conflicts

If port 8000 is already in use, change the `PORT` constant in `test_e2e_docker.py`.

## Cleanup

The tests automatically clean up containers after running. If a test fails and leaves containers behind:

```bash
# Stop and remove test container
docker stop mcp-openweathermap-test
docker rm mcp-openweathermap-test
```
