"""End-to-end tests for Docker container deployment."""

import subprocess
import time

import pytest
import requests
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Test configuration
IMAGE_NAME = "mcp-openweathermap"
CONTAINER_NAME = "mcp-openweathermap-test"
PORT = 8000
BASE_URL = f"http://localhost:{PORT}"


@pytest.fixture(scope="module")
def docker_container():
    """Build and run Docker container for testing."""
    # Clean up any existing test container
    print("Cleaning up any existing test containers...")
    subprocess.run(["docker", "stop", CONTAINER_NAME], check=False, capture_output=True)
    subprocess.run(["docker", "rm", CONTAINER_NAME], check=False, capture_output=True)

    # Build the image
    print("Building Docker image...")
    build_result = subprocess.run(
        ["docker", "build", "-t", IMAGE_NAME, "."],
        capture_output=True,
        text=True,
    )
    if build_result.returncode != 0:
        print(f"Build stdout: {build_result.stdout}")
        print(f"Build stderr: {build_result.stderr}")
    assert build_result.returncode == 0, f"Docker build failed: {build_result.stderr}"

    # Run the container with OpenWeatherMap API key from environment
    print("Starting Docker container...")
    import os

    api_key = os.getenv("OPENWEATHERMAP_API_KEY", "test_key")

    run_result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER_NAME,
            "-p",
            f"{PORT}:{PORT}",
            "-e",
            f"OPENWEATHERMAP_API_KEY={api_key}",
            IMAGE_NAME,
        ],
        capture_output=True,
        text=True,
    )

    if run_result.returncode != 0:
        print(f"Failed to start container: {run_result.stderr}")
        # Try to find what's using the port
        port_check = subprocess.run(
            ["docker", "ps", "--filter", f"publish={PORT}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        if port_check.stdout.strip():
            pytest.fail(f"Port {PORT} is already in use by container: {port_check.stdout.strip()}")
        pytest.fail(f"Failed to start container: {run_result.stderr}")

    print(f"Container {CONTAINER_NAME} started successfully")

    # Wait for container to be ready
    print("Waiting for container to be ready...")
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                service_name = data.get("service", "")
                print(f"Container is ready! Service: {service_name}")
                # Verify we're connecting to the right service
                if "mcp-openweathermap" not in service_name.lower():
                    print(f"Warning: Connected to unexpected service: {service_name}")
                    print("Checking if correct container is running...")
                    subprocess.run(["docker", "logs", "--tail", "20", CONTAINER_NAME])
                break
        except requests.RequestException:
            if attempt % 5 == 0:  # Print every 5 attempts
                print(f"Waiting... (attempt {attempt + 1}/{max_attempts})")
        time.sleep(1)
    else:
        # Print container logs for debugging
        print("Container logs:")
        subprocess.run(["docker", "logs", "--tail", "50", CONTAINER_NAME])
        # Cleanup on failure
        subprocess.run(["docker", "stop", CONTAINER_NAME], check=False)
        subprocess.run(["docker", "rm", CONTAINER_NAME], check=False)
        pytest.fail("Container failed to start within timeout")

    yield

    # Cleanup
    print("Stopping and removing container...")
    subprocess.run(["docker", "stop", CONTAINER_NAME], check=True)
    subprocess.run(["docker", "rm", CONTAINER_NAME], check=True)


def test_health_endpoint(docker_container):
    """Test that the health endpoint returns successfully."""
    response = requests.get(f"{BASE_URL}/health", timeout=5)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

    # Verify service name
    service_name = data.get("service", "")
    print(f"Health check returned service: {service_name}")
    assert "mcp-openweathermap" in service_name.lower(), (
        f"Expected 'mcp-openweathermap' in service name, got: {service_name}"
    )


@pytest.mark.asyncio
async def test_mcp_tools_list(docker_container):
    """Test that the MCP tools/list endpoint returns all expected tools using MCP client."""
    # Use the official MCP Python SDK client
    async with streamablehttp_client(f"{BASE_URL}/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # List all tools
            tools_response = await session.list_tools()
            tools_list = tools_response.tools

            assert tools_list, "No tools returned from MCP server"

            tool_names = {tool.name for tool in tools_list}
            print(f"Found {len(tool_names)} tools: {sorted(tool_names)}")

            # Verify all expected tools are registered
            expected_tools = {
                "get_current_weather",
                "get_forecast",
                "get_hourly_forecast",
                "get_weather_alerts",
                "get_air_quality",
                "get_weather_by_zip",
                "search_city",
                "get_historical_weather",
                "get_uv_index",
                "get_weather_map",
            }

            missing_tools = expected_tools - tool_names
            extra_tools = tool_names - expected_tools

            if missing_tools:
                print(f"Missing expected tools: {missing_tools}")
            if extra_tools:
                print(f"Found extra tools (not expected): {extra_tools}")

            assert expected_tools.issubset(tool_names), (
                f"Missing tools: {missing_tools}. "
                f"Available tools: {sorted(tool_names)}"
            )

            # Verify each tool has required fields
            for tool in tools_list:
                assert tool.name
                assert tool.description
                assert tool.inputSchema

            print(f"✓ Successfully verified {len(expected_tools)} expected MCP tools")


@pytest.mark.asyncio
async def test_mcp_tool_execution(docker_container):
    """Test executing a tool through the MCP client."""
    import os

    # Skip if no API key
    if not os.getenv("OPENWEATHERMAP_API_KEY") or os.getenv(
        "OPENWEATHERMAP_API_KEY"
    ) == "test_key":
        pytest.skip("Skipping tool execution test - no valid API key provided")

    async with streamablehttp_client(f"{BASE_URL}/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Test search_city tool (doesn't require coordinates)
            result = await session.call_tool(
                "search_city",
                arguments={"city_name": "London", "limit": 1},
            )

            assert result.content, "No content in tool execution result"
            print("✓ Successfully executed search_city tool")


def test_container_shutdown(docker_container):
    """Test that container shuts down gracefully."""
    # Stop container
    result = subprocess.run(
        ["docker", "stop", CONTAINER_NAME],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, "Container did not stop gracefully"

    # Verify container is stopped
    result = subprocess.run(
        ["docker", "ps", "-a", "-f", f"name={CONTAINER_NAME}", "--format", "{{.Status}}"],
        capture_output=True,
        text=True,
    )

    assert "Exited" in result.stdout, "Container is not in exited state"
    print("✓ Container shut down gracefully")
