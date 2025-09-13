from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from main import DeliveryService

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
