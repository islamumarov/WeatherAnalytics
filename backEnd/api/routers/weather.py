from typing import Optional
from fastapi import APIRouter, Query, Depends
from backEnd.services.weather_service import WeatherService
from backEnd.services.geo_service import GeoService
from backEnd.core.config import settings

router = APIRouter(prefix="/api/weather", tags=["weather"])

def get_weather_service() -> WeatherService:
    return WeatherService()

def get_geocoding_service() -> GeoService:
    return GeoService()

@router.get("/summary")
async def summary(
    q: Optional[str] = Query(None),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    wx: WeatherService = Depends(get_weather_service),
    geo: GeoService = Depends(get_geocoding_service),
):
    if q:
        resolved = await geo.resolve_coords_from_query(q)
        if resolved:
            lat, lon, place = resolved
        else:
            lat, lon = settings.default_lat, settings.default_lon
            place = None
    else:
        lat = lat or settings.default_lat
        lon = lon or settings.default_lon
        place = await geo.resolve_place_from_coords(lat, lon)

    data = await wx.fetch_data(lat, lon)
    ctx = wx.build_context(data)
    ctx["place"] = place or ctx.get("place") or f"{lat:.4f}, {lon:.4f}"
    return ctx
