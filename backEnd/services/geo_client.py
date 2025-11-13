from typing import Dict, Any, Optional, List
import httpx

class GeoClient:
    def __init__(self, base_url:str = "http://api.openweathermap.org/geo/1.0"):
        self.base_url = base_url
    async def get(self, path:str, params:Dict[str, Any]) ->Any:
        url = f"{self.base_url}/{path}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params = params)
            if response.status_code == 401:
                raise ValueError(
                    "OpenWeather API authentication failed (401 Unauthorized). "
                    "Please check that your API_WEATHER_KEY is set correctly in the .env file."
                )
            response.raise_for_status()
            return response.json()
    async def direct(self,q: str, appid:str, limit:int = 1) -> List[Dict[str, Any]]:
        return await self.get("direct", {"q": q, "limit":limit, "appid":appid})

    async def reverse(self, lat:float, lon:float, appid:str, limit:int = 1) -> List[Dict[str, Any]]:
        return await self.get("reverse",{"lat":lat, "lon":lon, "limit":limit, "appid":appid})