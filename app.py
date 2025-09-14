from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from main import DeliveryService
import random
import time

# load app
app = FastAPI(title = "Medical Supply Drone API")

class DeliveryRequest(BaseModel):
    request_text : str
    area_name : str

service = DeliveryService()

@app.get("/")
def root():
    return {"message": "Medical Supply Project API is running!"}

@app.post("/delivery")
def calculate_delivery(request: DeliveryRequest):
    try:
        result = service.process_request(request.request_text, request.area_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code = 400, detail = str(e))

# Drone live location simulation
drone_location = {}
class DroneLocation(BaseModel):
    drone_id: str
    latitude: float
    longitude: float

@app.get("/live_location{}")
def get_live_location(drone_id: str):
    lat = 26.1234 + random.uniform(-0.01, 0.01)
    lon = 91.4567 + random.uniform(-0.01, 0.01)

    return {
        "drone_id": drone_id,
        "latitude": lat,
        "longitude": lon,
        "timestamp": time.time()
    }
