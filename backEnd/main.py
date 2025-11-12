from fastapi import FastAPI
from backEnd.services import api_forecast_client
from backEnd.services.api_forecast_client import ApiForecastClient

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

@app.get("/weather")
async def weather():
    params = {"lat": 47.6061, "lon": 122.3328, 'appid':'7f043836018ef59e851eaeb9fb2b3580'}
    forecast_service =ApiForecastClient()
    return await forecast_service._make_request('forecast', params)


#47.861694, -122.009278