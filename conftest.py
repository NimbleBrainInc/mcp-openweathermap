"""Pytest configuration - loads .env file for all tests."""

from dotenv import load_dotenv

# Load .env file before any tests run
load_dotenv()
