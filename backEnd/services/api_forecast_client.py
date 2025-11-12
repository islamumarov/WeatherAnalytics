from typing import Optional, Dict, Any

import httpx
from fastapi import logger

class ApiForecastClient:

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize API-Football client.

        Args:
            api_key: API-Football API key (defaults to settings)
            base_url: Base URL for API (defaults to settings)
        """
        #self.api_key = api_key or settings.api_football_key
        self.base_url = 'https://api.openweathermap.org/data/2.5'  #base_url or settings.api_football_base_url
        #self.timeout = settings.api_football_timeout

        # if not self.api_key:
        #     raise ValueError("API_FOOTBALL_KEY must be set in environment variables or passed to client")

    async def _make_request(self, endpoint = str, params: Optional[Dict[str, Any]] = None):
        url = f"{self.base_url}/{endpoint}"

        try:
            async with httpx.AsyncClient() as client:
                #logger.info(f"API Request: GET {url} params={params}")

                response = await client.get(url, params=params)


                response.raise_for_status()
                data = response.json()


                # logger.info(f"API Response: {data.get('results', 0)} results")

                return data

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
