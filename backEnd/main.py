"""Primary FastAPI application instance."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import weather
from core.database import engine, Base

app = FastAPI(title="Weather API")

# Enable CORS so the front end can call the API independently.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Narrow this in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wire up API routers.
app.include_router(weather.router)


@app.on_event("startup")
def on_startup() -> None:
    """Create database tables on startup during local development."""
    Base.metadata.create_all(bind=engine)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Weather API is running", "docs": "/docs"}


__all__ = ["app"]
