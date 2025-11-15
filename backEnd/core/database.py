from typing import Generator, Optional
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

"""
Database URL configurable via env var. Default to a local SQLite file for easy development.
Default path: <project_root>/db/weather.db (two levels up from this file).
"""

# Resolve project root and ensure db directory exists
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DB_DIR = os.path.join(_PROJECT_ROOT, "db")
try:
	# Try to create the repo-local db directory (works in local dev)
	os.makedirs(_DB_DIR, exist_ok=True)
except Exception:
	# If that fails (read-only package filesystem like AWS Lambda),
	# fall back to a writable runtime directory (default: /tmp).
	# Allow overriding with DB_DIR environment variable.
	import logging

	logging.warning("Could not create project db dir '%s' - falling back to writable DB_DIR", _DB_DIR)
	_DB_DIR = os.getenv("DB_DIR", "/tmp/weather_analytics_db")
	os.makedirs(_DB_DIR, exist_ok=True)

# Build default SQLite URL to <project_root>/db/weather.db
DEFAULT_SQLITE_URL = "sqlite:///" + os.path.join(_DB_DIR, "weather.db")


def _normalize_db_url(raw: str | None) -> str:

	if not raw:
		return DEFAULT_SQLITE_URL
	if "://" not in raw:

		abs_path = os.path.abspath(raw)
		return "sqlite:///" + abs_path
	return raw


DATABASE_URL: str = _normalize_db_url(os.getenv("DATABASE_URL"))

# For SQLite we need to pass connect_args to avoid thread check issues.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
	"""Dependency that provides a SQLAlchemy Session (sync).

	Use in FastAPI endpoints with Depends(get_db).
	"""
	db: Optional[Session] = None
	try:
		db = SessionLocal()
		yield db
	finally:
		if db:
			db.close()
