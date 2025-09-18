from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client
import os
from dotenv import load_dotenv
from main import DeliveryService

load_dotenv()

# Supabase client
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

app = FastAPI()
service = DeliveryService()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DeliveryRequest(BaseModel):
    request_text: str
    area: str

@app.post("/delivery")
async def create_delivery(req: DeliveryRequest):
    try:
        result = service.process_request(req.request_text, req.area)

        delivery = {
            "request_text": req.request_text,
            "area": req.area,
            "lat": result["coordinates"]["lat"],
            "lon": result["coordinates"]["lon"],
            "drone_eta": result["drone_eta"],
            "road_eta": result["road_eta"],
            "status": "Queued",
            "progress": 0,
            "priority": result["priority"],
            "recommended_method": result["recommended_method"],
            "weather": result["weather"],
            "traffic": result["traffic"],
            "distance_km": result["distance_km"],
        }

        supabase.table("deliveries").insert(delivery).execute()
        return {"message": "Delivery created successfully", "data": delivery}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.get("/deliveries")
async def get_deliveries():
    try:
        res = supabase.table("deliveries").select("*").execute()
        deliveries = res.data if res and hasattr(res, "data") else []
        return deliveries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching deliveries: {e}")

@app.get("/deliveries/{delivery_id}")
async def get_delivery(delivery_id: str):
    try:
        res = supabase.table("deliveries").select("*").eq("id", delivery_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Delivery not found")
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching delivery: {e}")
