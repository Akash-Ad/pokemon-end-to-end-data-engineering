"""
This file defines configuration for the project.
It keeps the database location and basic network settings that other modules import.
"""
from __future__ import annotations
import os
from typing import Final
from dotenv import load_dotenv

# To load environment variables from .env
load_dotenv

# Database configuration
DB_PATH: Final[str] = os.getenv("DB_PATH", "pokemon.db") # os.getenv is applied so the path can still be overridden if needed.
DB_URL: Final[str] = f"sqlite:///{DB_PATH}"  # connection string built for SQLite

# External API base URL
POKEAPI_BASE: Final[str] = "https://pokeapi.co/api/v2"

# Network settings
HTTP_TIMEOUT_SECONDS: Final[float] = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
MAX_CONCURRENCY: Final[int] = int(os.getenv("MAX_CONCURRENCY", "8"))
MAX_RETRIES: Final[int] = int(os.getenv("MAX_RETRIES", "3"))