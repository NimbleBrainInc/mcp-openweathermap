# S-Tier MCP Server Architecture Prompt

Transform a simple MCP server.py into a production-ready, well-architected MCP server following enterprise-grade best practices.

## 🎯 Reference Architecture

Based on the battle-tested mcp-server-ipinfo structure that implements the complete MCP specification with strong typing, comprehensive testing, and production deployment support.

---

## 📁 Project Structure

Create the following directory structure:

```
.
├── src/
│   └── mcp_{package_name}/
│       ├── __init__.py
│       ├── server.py          # FastMCP server with tool definitions
│       ├── api_client.py      # Dedicated async API client class
│       └── api_models.py      # Pydantic models for type safety
├── tests/
│   ├── __init__.py
│   ├── test_server.py         # Server tool tests
│   └── test_api_client.py     # API client tests
├── pyproject.toml             # Project config with uv, ruff, mypy
├── Makefile                   # Development workflow commands
├── Dockerfile                 # Container deployment
├── pytest.ini                 # Pytest configuration
├── .gitignore                 # Comprehensive ignores
├── .python-version            # Python version (3.13)
├── README.md                  # Documentation
└── .env                       # Environment variables (gitignored)
```

---

## 🏗️ Core Architecture Patterns

### 1. **API Client Layer** (`api_client.py`)

**Purpose:** Encapsulate ALL HTTP communication in a dedicated, reusable async client class.

**Key Requirements:**
- Use `aiohttp` for async HTTP (NOT httpx)
- Implement context manager protocol (`__aenter__`, `__aexit__`)
- Single `_request()` method handles all HTTP calls
- Session management with `_ensure_session()`
- Custom exception class for API errors
- Strict type hints on ALL methods
- Bearer token or API key authentication
- Proper timeout handling
- Response parsing (JSON/text/error handling)

**Template Structure:**

```python
import os
from typing import Any
import aiohttp
from aiohttp import ClientError
from .api_models import *


class {Service}APIError(Exception):
    """Custom exception for API errors."""
    def __init__(self, status: int, message: str, details: dict[str, Any] | None = None) -> None:
        self.status = status
        self.message = message
        self.details = details
        super().__init__(f"{Service} API Error {status}: {message}")


class {Service}Client:
    """Async API client for {Service} API."""

    def __init__(
        self,
        api_token: str | None = None,
        base_url: str = "https://api.{service}.com",
        timeout: float = 30.0,
    ) -> None:
        self.api_token = api_token or os.environ.get("{SERVICE}_API_TOKEN")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "{Service}Client":
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def _ensure_session(self) -> None:
        """Create session if it doesn't exist."""
        if not self._session:
            headers = {
                "User-Agent": "mcp-server-{package}/1.0",
                "Accept": "application/json"
            }
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )

    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: Any | None = None,
        data: str | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with error handling."""
        await self._ensure_session()

        url = f"{self.base_url}{path}"

        # Add API key to params if needed
        if self.api_token and params is None:
            params = {}
        if self.api_token and params is not None:
            params["api_key"] = self.api_token

        kwargs = {}
        if json_data is not None:
            kwargs["json"] = json_data
        elif data is not None:
            kwargs["data"] = data
            if content_type:
                kwargs["headers"] = {"Content-Type": content_type}

        try:
            if not self._session:
                raise RuntimeError("Session not initialized")

            async with self._session.request(method, url, params=params, **kwargs) as response:
                content_type = response.headers.get("Content-Type", "")

                if "application/json" in content_type:
                    result = await response.json()
                elif "text/plain" in content_type:
                    text = await response.text()
                    return {"result": text}
                else:
                    text = await response.text()
                    # Try to parse as JSON
                    if text.startswith("{") or text.startswith("["):
                        import json
                        try:
                            result = json.loads(text)
                        except json.JSONDecodeError:
                            result = {"result": text}
                    else:
                        result = {"result": text}

                # Check for errors
                if response.status >= 400:
                    error_msg = "Unknown error"
                    if isinstance(result, dict):
                        error_msg = (
                            result.get("error", {}).get("message") or
                            result.get("message") or
                            result.get("title") or
                            str(result.get("error", error_msg))
                        )
                    raise {Service}APIError(response.status, error_msg, result)

                return result  # type: ignore[no-any-return]

        except ClientError as e:
            raise {Service}APIError(500, f"Network error: {str(e)}") from e

    # API endpoint methods
    async def get_{resource}(self, id: str) -> {Resource}Response:
        """Get resource by ID."""
        data = await self._request("GET", f"/{resource}/{id}")
        return {Resource}Response(**data)
```

---

### 2. **Data Models Layer** (`api_models.py`)

**Purpose:** Provide strong typing and validation for ALL API responses.

**Key Requirements:**
- Use Pydantic `BaseModel` for all data structures
- Use `Field()` with descriptions
- Type ALL fields properly (`str`, `int`, `bool`, `list`, etc.)
- Use `| None` for optional fields (NOT `Optional[]`)
- Create `Enum` classes for constants
- Add docstrings to model classes

**Template Structure:**

```python
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class {Resource}Type(str, Enum):
    """Enum for resource types."""
    TYPE_A = "type_a"
    TYPE_B = "type_b"


class {Resource}Response(BaseModel):
    """Response model for {resource} endpoint."""
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Resource name")
    type: {Resource}Type = Field(..., description="Resource type")
    created_at: str | None = Field(None, description="Creation timestamp")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class ErrorResponse(BaseModel):
    """Error response model."""
    status: int | None = None
    error: dict[str, str] | None = None
    message: str | None = None
```

---

### 3. **Server Layer** (`server.py`)

**Purpose:** Define MCP tools using FastMCP, inject dependencies, handle errors.

**Key Requirements:**
- Use `FastMCP` from `fastmcp`
- Global client instance with getter function
- Context injection: `ctx: Context[Any, Any, Any]`
- Use `ctx.error()`, `ctx.warning()` for logging
- Custom routes for health checks
- Export ASGI app: `app = mcp.streamable_http_app()`
- Comprehensive docstrings with Args/Returns
- Type hints everywhere
- Error handling with try/except

**Template Structure:**

```python
import os
from typing import Any
from fastapi import Request
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import Context, FastMCP

from .api_client import {Service}APIError, {Service}Client
from .api_models import *

# Create MCP server
mcp = FastMCP("{ServiceName}")

# Global client instance
_client: {Service}Client | None = None


def get_client(ctx: Context[Any, Any, Any]) -> {Service}Client:
    """Get or create the API client instance."""
    global _client
    if _client is None:
        api_token = os.environ.get("{SERVICE}_API_TOKEN")
        if not api_token:
            ctx.warning("{SERVICE}_API_TOKEN is not set - some features may be limited")
        _client = {Service}Client(api_token=api_token)
    return _client


# Health endpoint for HTTP transport
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring."""
    return JSONResponse({"status": "healthy"})


# MCP Tools
@mcp.tool()
async def get_{resource}_info(id: str, ctx: Context[Any, Any, Any]) -> {Resource}Response:
    """Get comprehensive information about a resource.

    Args:
        id: Resource identifier to lookup
        ctx: MCP context

    Returns:
        Complete resource information
    """
    client = get_client(ctx)
    try:
        return await client.get_{resource}(id)
    except {Service}APIError as e:
        ctx.error(f"API error: {e.message}")
        raise


# Create ASGI application for uvicorn
app = mcp.streamable_http_app()
```

---

## ⚙️ Configuration Files

### `pyproject.toml`

**Key Requirements:**
- Python 3.13+
- Dependencies: `aiohttp`, `fastapi`, `fastmcp`, `pydantic`
- Dev dependencies: `mypy`, `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`
- Ruff config: line-length 100, strict linting
- Mypy config: strict mode, all warnings enabled
- Use `uv` for package management

```toml
[project]
name = "mcp-{package}"
version = "0.1.0"
description = "{Service} MCP Server with OpenAPI support"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "aiohttp>=3.12.15",
    "fastapi>=0.117.1",
    "fastmcp>=2.12.4",
    "pydantic>=2.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mcp_{package}"]

[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long - handled by formatter
    "B008",  # do not perform function calls in argument defaults
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"

[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_unimported = false
ignore_missing_imports = true
no_implicit_reexport = true
check_untyped_defs = true
show_error_codes = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
disable_error_code = ["unused-coroutine", "misc"]

[dependency-groups]
dev = [
    "mypy>=1.18.2",
    "pytest>=8.4.2",
    "pytest-asyncio>=1.2.0",
    "pytest-cov>=7.0.0",
    "ruff>=0.13.1",
]
```

---

### `Makefile`

**Purpose:** Standardize development workflow commands.

```makefile
IMAGE_NAME = yourorg/mcp-{package}
VERSION ?= latest

.PHONY: help install dev-install format lint test clean run check all

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	uv pip install -e .

dev-install: ## Install with dev dependencies
	uv pip install -e ".[dev]"

format: ## Format code with ruff
	uv run ruff format src/ tests/

lint: ## Lint code with ruff
	uv run ruff check src/ tests/

lint-fix: ## Lint and fix code with ruff
	uv run ruff check --fix src/ tests/

typecheck: ## Type check with mypy
	uv run mypy src/

test: ## Run tests with pytest
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage
	uv run pytest tests/ -v --cov=src/mcp_{package} --cov-report=term-missing

clean: ## Clean up artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true

run: ## Run the MCP server
	uv run python -m mcp_{package}.server

check: lint typecheck test ## Run all checks

all: clean install format lint typecheck test ## Full workflow

# Aliases
fmt: format
t: test
l: lint
```

---

### `pytest.ini`

```ini
[tool:pytest]
asyncio_mode = auto
testpaths = tests
```

---

### `Dockerfile`

**Purpose:** Production-ready container deployment.

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN apt-get update && apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml ./
COPY README.md ./
COPY src/ ./src/

# Install dependencies
RUN uv pip install --system --no-cache .

# Create non-root user
RUN groupadd -g 1000 mcpuser && \
    useradd -m -u 1000 -g 1000 mcpuser && \
    chown -R mcpuser:mcpuser /app

USER mcpuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "mcp_{package}.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### `.gitignore`

**Comprehensive ignores for Python/MCP projects:**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
build/
dist/
*.egg-info/
.Python

# Virtual environments
.env
.venv
env/
venv/
ENV/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Type checking
.mypy_cache/
.dmypy.json
.pytype/

# Linting
.ruff_cache/

# IDEs
.idea/
.vscode/
*.code-workspace

# OS
.DS_Store
Thumbs.db

# MCP/Claude
.claude/

# Package managers
uv.lock
.uv/
poetry.lock
Pipfile.lock

# Secrets
*.key
*.pem
credentials.json
.secrets/
```

---

## 🧪 Testing Pattern

### `tests/test_server.py`

**Key Requirements:**
- Use `pytest` with `pytest-asyncio`
- Mock the API client with `AsyncMock`
- Test each tool independently
- Test error handling
- Use fixtures for common setup

```python
"""Unit tests for the MCP server tools."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastmcp import Context

from mcp_{package}.server import (
    get_{resource}_info,
)


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    ctx = MagicMock(spec=Context)
    ctx.warning = MagicMock()
    ctx.error = MagicMock()
    return ctx


class TestMCPTools:
    """Test the MCP server tools."""

    @pytest.mark.asyncio
    async def test_get_{resource}_info(self, mock_context):
        """Test get_{resource}_info tool."""
        with patch("mcp_{package}.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.get_{resource}.return_value = MagicMock(
                id="123",
                name="Test Resource",
            )

            result = await get_{resource}_info("123", mock_context)

            assert result.id == "123"
            mock_client.get_{resource}.assert_called_once_with("123")
```

---

## 📚 README.md Template

```markdown
# MCP Server {Service}

MCP Server for {Service} API with comprehensive tooling and type safety.

## Features

- **Full API Coverage**: Complete implementation of {Service} API
- **Strongly Typed**: All responses use Pydantic models
- **HTTP Transport**: Supports streamable-http with health endpoint
- **Async/Await**: Built on aiohttp for performance
- **Type Safe**: Full mypy strict mode compliance

## Installation

\`\`\`bash
# Using uv (recommended)
uv pip install -e .
\`\`\`

## Configuration

Set your API token:

\`\`\`bash
export {SERVICE}_API_TOKEN=your_token_here
\`\`\`

## Running the Server

\`\`\`bash
# Development
uv run python -m mcp_{package}.server

# Production (Docker)
docker build -t mcp-{package} .
docker run -e {SERVICE}_API_TOKEN=xxx -p 8000:8000 mcp-{package}
\`\`\`

## Available MCP Tools

- \`get_{resource}_info(id)\` - Get resource information
- [List all tools here]

## Development

\`\`\`bash
make help          # Show all commands
make install       # Install dependencies
make format        # Format code
make lint          # Lint code
make typecheck     # Type check
make test          # Run tests
make check         # Run all checks
\`\`\`

## Requirements

- Python 3.13+
- aiohttp
- fastmcp
- pydantic

## License

MIT
```

---

## 🎯 Migration Steps

When transforming an existing `server.py`:

1. **Extract API logic** → Create `api_client.py` with client class
2. **Extract models** → Create `api_models.py` with Pydantic models
3. **Refactor tools** → Update server.py to use client + context
4. **Add type hints** → Ensure ALL functions/methods are typed
5. **Create structure** → Set up `src/mcp_{package}/` directory
6. **Add config files** → pyproject.toml, Makefile, Dockerfile, etc.
7. **Write tests** → Create comprehensive test coverage
8. **Run validation** → `make check` should pass (lint + typecheck + test)

---

## ✅ Quality Checklist

Before considering the migration complete:

- [ ] All code in `src/mcp_{package}/` structure
- [ ] Separate `api_client.py` with async client class
- [ ] Pydantic models in `api_models.py`
- [ ] All functions have type hints
- [ ] All tools have docstrings with Args/Returns
- [ ] Context injection with `ctx: Context[Any, Any, Any]`
- [ ] Error handling with custom exceptions
- [ ] Health endpoint at `/health`
- [ ] ASGI app exported: `app = mcp.streamable_http_app()`
- [ ] Tests written with pytest + AsyncMock
- [ ] `make format` runs successfully
- [ ] `make lint` passes with no errors
- [ ] `make typecheck` passes mypy strict mode
- [ ] `make test` passes all tests
- [ ] README.md with setup instructions
- [ ] Dockerfile for production deployment
- [ ] .gitignore with comprehensive ignores

---

## 💡 Key Principles

1. **Separation of Concerns**: API client, models, and server are separate
2. **Type Safety First**: Strong typing catches bugs at development time
3. **Async All the Way**: Use async/await for all I/O operations
4. **Error Handling**: Custom exceptions, context logging, graceful failures
5. **Testability**: Mock-friendly design with dependency injection
6. **Production Ready**: Docker, health checks, monitoring support
7. **Developer Experience**: Makefile commands, auto-formatting, fast feedback

---

## 🚀 Usage

**To use this prompt:**

1. Copy this entire prompt
2. Provide it to an AI coding assistant along with your `server.py`
3. Ask: "Please refactor my server.py following this architecture guide"
4. Review the generated code
5. Run `make check` to validate quality
6. Deploy with confidence!

**Example prompt to AI:**
```
I have a server.py MCP server. Please refactor it following the S-Tier MCP Server
Architecture guidelines I'm providing. Transform it into a production-ready server with:
- Proper directory structure (src/mcp_{package}/)
- Dedicated API client class
- Pydantic models for type safety
- Comprehensive tests
- All configuration files (pyproject.toml, Makefile, Dockerfile, etc.)

Here's my current server.py:
[paste server.py]

Here's the architecture guide:
[paste this document]
```

---

**End of S-Tier MCP Server Architecture Prompt**

*Reference: Based on mcp-server-ipinfo production architecture*
*Version: 1.0*
*Last Updated: 2025*
