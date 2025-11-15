from typing import Generator, Optional
import logging
import os
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

"""
Database URL configurable via env var. Default to a local SQLite file for easy development.
Default path: <project_root>/db/weather.db (two levels up from this file).
"""

# Resolve project root and capture bundled/runtime SQLite locations
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BUNDLED_DB_PATH = os.path.join(_PROJECT_ROOT, "db", "weather.db")
_BUNDLED_DIR = os.path.dirname(_BUNDLED_DB_PATH)

try:
	os.makedirs(_BUNDLED_DIR, exist_ok=True)
except Exception:
	logging.debug("Skipping creation of bundled DB dir '%s' (likely read-only).", _BUNDLED_DIR)

_RUNTIME_DB_DIR = os.getenv("DB_DIR")
if not _RUNTIME_DB_DIR:
	tmp_base = os.getenv("TMPDIR", "/tmp")
	_RUNTIME_DB_DIR = os.path.join(tmp_base, "weather_analytics_db")

try:
	os.makedirs(_RUNTIME_DB_DIR, exist_ok=True)
except Exception:
	logging.debug("Could not ensure runtime DB dir '%s' exists.", _RUNTIME_DB_DIR, exc_info=True)

_RUNTIME_DB_PATH = os.path.join(_RUNTIME_DB_DIR, "weather.db")


def _default_sqlite_path() -> str:
	"""Resolve a usable SQLite file path across local and serverless runs."""
	if os.path.exists(_BUNDLED_DB_PATH):
		bundle_writable = os.access(_BUNDLED_DB_PATH, os.W_OK)
		dir_writable = os.access(_BUNDLED_DIR, os.W_OK)
		if bundle_writable and dir_writable:
			return _BUNDLED_DB_PATH
		try:
			if not os.path.exists(_RUNTIME_DB_PATH):
				shutil.copyfile(_BUNDLED_DB_PATH, _RUNTIME_DB_PATH)
			return _RUNTIME_DB_PATH
		except Exception:
			logging.debug("Failed to copy bundled DB to runtime path '%s'.", _RUNTIME_DB_PATH, exc_info=True)
			return _BUNDLED_DB_PATH
	if os.access(_BUNDLED_DIR, os.W_OK):
		return _BUNDLED_DB_PATH
	return _RUNTIME_DB_PATH


DEFAULT_SQLITE_PATH = _default_sqlite_path()
DEFAULT_SQLITE_URL = "sqlite:///" + DEFAULT_SQLITE_PATH


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
