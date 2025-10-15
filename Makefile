IMAGE_NAME = mcp-openweathermap
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
	uv pip install -e . --group dev

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
	uv run pytest tests/ -v --cov=src/mcp_openweathermap --cov-report=term-missing

clean: ## Clean up artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true

run: ## Run the MCP server with stdio
	uv run python -m mcp_openweathermap.server

run-http: ## Run the MCP server with HTTP transport
	uv run uvicorn mcp_openweathermap.server:app --host 0.0.0.0 --port 8000

check: lint typecheck test ## Run all checks

all: clean install format lint typecheck test ## Full workflow

# Docker targets
docker-build: ## Build Docker image
	docker build -t $(IMAGE_NAME):$(VERSION) .

docker-run: ## Run Docker container
	docker run -p 8000:8000 -e OPENWEATHERMAP_API_KEY=$(OPENWEATHERMAP_API_KEY) $(IMAGE_NAME):$(VERSION)

docker-test: ## Run tests in Docker
	docker build -t $(IMAGE_NAME):test --target test .

# Aliases
fmt: format
t: test
l: lint
