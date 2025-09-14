from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import math

app = FastAPI(title="Medical Supply Drone API")

# Store active deliveries
active_deliveries = {}

class DeliveryRoute(BaseModel):
    drone_id: str
    source_lat: float
    source_lon: float
    dest_lat: float
    dest_lon: float
    speed_kmph: float  # drone speed


def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c  # distance in km


@app.post("/start_delivery")
def start_delivery(route: DeliveryRoute):
    distance = haversine(route.source_lat, route.source_lon,
                         route.dest_lat, route.dest_lon)
    duration_hr = distance / route.speed_kmph

    active_deliveries[route.drone_id] = {
        "source": (route.source_lat, route.source_lon),
        "dest": (route.dest_lat, route.dest_lon),
        "distance": distance,
        "speed": route.speed_kmph,
        "start_time": time.time(),
        "duration": duration_hr * 3600  # in seconds
    }

    return {
        "drone_id": route.drone_id,
        "distance_km": distance,
        "eta_hr": duration_hr
    }


@app.get("/live_location/{drone_id}")
def live_location(drone_id: str):
    if drone_id not in active_deliveries:
        raise HTTPException(status_code = 404, detail = "Delivery not started")

    delivery = active_deliveries[drone_id]
    elapsed = time.time() - delivery["start_time"]
    progress = min(elapsed / delivery["duration"], 1.0)

    # interpolate lat/lon
    lat = (delivery["source"][0] +
           (delivery["dest"][0] - delivery["source"][0]) * progress)
    lon = (delivery["source"][1] +
           (delivery["dest"][1] - delivery["source"][1]) * progress)

    return {
        "drone_id": drone_id,
        "latitude": lat,
        "longitude": lon,
        "progress_percent": round(progress * 100, 2)
    }