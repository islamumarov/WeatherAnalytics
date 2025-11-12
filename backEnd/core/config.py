# """
# Application configuration management using environment variables.
# """
# import os
# from pathlib import Path
#
# try:
#     # Load .env early so os.getenv and pydantic BaseSettings can pick up values
#     from dotenv import load_dotenv
#
#     # Search for .env in the project root and backEnd folder
#     env_paths = [Path(__file__).resolve().parents[1] / '.env', Path(__file__).resolve().parents[0] / '.env']
#     for p in env_paths:
#         if p.exists():
#             load_dotenv(dotenv_path=p)
#             break
# except Exception:
#     # If python-dotenv isn't installed or loading fails, we still continue
#     pass
# from functools import lru_cache
# from typing import Optional, Union
# import json
#
# from pydantic import field_validator
# from pydantic_settings import BaseSettings
#
#
# class Settings(BaseSettings):
#     """Application settings loaded from environment variables."""
#
#     # Application
#     app_name: str = "Weather Analytics API"
#     debug: bool = False
#     version: str = "1.0.0"
#
#     # Database
#     database_url: str = os.getenv(
#         "DATABASE_URL",
#         "postgresql+psycopg2://postgres:postgres@db:5432/weather_db"
#     )
#
#     # Database pool settings
#     db_pool_size: int = 5
#     db_max_overflow: int = 10
#     db_pool_pre_ping: bool = True
#
#     # CORS
#     cors_origins: Union[list[str], str] = ["*"]
#     cors_credentials: bool = True
#     cors_methods: Union[list[str], str] = ["*"]
#     cors_headers: Union[list[str], str] = ["*"]
#
#     @field_validator("cors_origins", "cors_methods", "cors_headers", mode="before")
#     @classmethod
#     def parse_cors_list(cls, v):
#         """Parse CORS configuration from environment variable."""
#         if isinstance(v, str):
#             # Handle empty string
#             if not v or v.strip() == "":
#                 return ["*"]
#             # Try to parse as JSON
#             try:
#                 parsed = json.loads(v)
#                 return parsed if isinstance(parsed, list) else [parsed]
#             except json.JSONDecodeError:
#                 # If not JSON, treat as comma-separated string
#                 return [item.strip() for item in v.split(",") if item.strip()]
#         return v
#
#     # API-Football Configuration
#     api_football_key: str = os.getenv("API_FOOTBALL_KEY", "")
#     api_football_base_url: str = os.getenv(
#         "API_FOOTBALL_BASE_URL",
#         "https://v3.football.api-sports.io"
#     )
#     api_football_rate_limit: int = 10  # requests per minute (free tier)
#     api_football_timeout: int = 30  # seconds
#
#     # Caching
#     cache_ttl_seconds: int = 300  # 5 minutes default cache
#
#     class Config:
#         env_file = ".env"
#         case_sensitive = False
#
#
# @lru_cache()
# def get_settings() -> Settings:
#     """Get cached settings instance."""
#     return Settings()
