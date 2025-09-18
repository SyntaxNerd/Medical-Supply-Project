# delivery_service.py
import joblib
import os
import requests
import datetime
import math
from dotenv import load_dotenv

# credentials   
load_dotenv()
openWeather_api_key = os.getenv("YOUR_OPENWEATHERMAP_KEY")
tomtom_api_key = os.getenv("TOMTOM_API_KEY")

# Load models
priority_model = joblib.load("priority_model.pkl")
eta_model = joblib.load("eta_model.pkl")
traffic_encoder = joblib.load("traffic_encoder.pkl")
weather_encoder = joblib.load("weather_encoder.pkl")

BASE_LAT, BASE_LON = 26.1445, 91.7362
DRONE_SPEED_KM = 80

# List of Assam districts/cities   
ASSAM_LOCATIONS = [
    "dibrugarh", "guwahati", "tezpur", "silchar", "nagaon",
    "jorhat", "sivasagar", "barpeta", "golaghat", "teok",
    "rangiya", "pathshala", "kokrajhar", "amingaon"
]

class DeliveryService:
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c * 1.18  # 18% buffer

    def geocode_area(self, area_name):
        url = f"https://api.tomtom.com/search/2/geocode/{area_name}.json"
        params = {"key": tomtom_api_key}
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("results"):
                result = data["results"][0]
                # Check state
                state = result.get("address", {}).get("countrySubdivision", "").lower()
                city = result.get("address", {}).get("municipality", "").lower()
                
                if state != "assam" and city not in ASSAM_LOCATIONS:
                    return None, None

                pos = result["position"]
                return pos["lat"], pos["lon"]
        except:
            return None, None
        return None, None

    def get_weather(self, lat, lon):
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={openWeather_api_key}"
        try:
            data = requests.get(url).json()
            weather_main = data["weather"][0]["main"].capitalize()
            if weather_main in ["Clear", "Clouds"]:
                return "Clear"
            elif weather_main in ["Rain", "Drizzle"]:
                return "Rainy"
            elif weather_main in ["Thunderstorm", "Snow"]:
                return "Storm"
            else:
                return "Clear"
        except:
            return "Clear"

    def estimate_traffic(self):
        hour = datetime.datetime.now().hour
        if 6 <= hour <= 9 or 17 <= hour <= 20:
            return "High"
        elif 10 <= hour <= 16:
            return "Medium"
        else:
            return "Low"

    def predict_delivery(self, request_text):
        return priority_model.predict([request_text.lower()])[0]

    def compute_drone_eta(self, distance_km):
        return distance_km / DRONE_SPEED_KM * 60

    def estimate_road_eta(self, distance_km, traffic, base_speed=40):
        if traffic == "Low":
            effective_speed = base_speed
        elif traffic == "Medium":
            effective_speed = base_speed * 0.7
        else:
            effective_speed = base_speed * 0.5
        return distance_km / effective_speed

    def get_road_eta_with_traffic(self, start_lat, start_lon, end_lat, end_lon):
        url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_lat},{start_lon}:{end_lat},{end_lon}/json"
        params = {
            "key": tomtom_api_key,
            "traffic": "true",
            "routeType": "fastest",
            "computeTravelTimeFor": "all"
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if "routes" in data:
                summary = data["routes"][0]["summary"]
                travel_time = summary["travelTimeInSeconds"] / 3600  # hours
                distance = summary["lengthInMeters"] / 1000  # km
                return travel_time, distance
        except:
            return None, None
        return None, None

    def format_eta_hours_to_hhmm(self, hours):
        h = int(hours)
        m = int(round((hours - h) * 60))
        return f"{h}h {m}m"

    def process_request(self, request_text, area_name):
        lat, lon = self.geocode_area(area_name)
        if lat is None:
            raise ValueError("Area not found or not in Assam")

        distance = self.haversine_distance(BASE_LAT, BASE_LON, lat, lon)
        weather = self.get_weather(lat, lon)
        traffic = self.estimate_traffic()
        priority = self.predict_delivery(request_text)

        road_eta, road_distance = self.get_road_eta_with_traffic(BASE_LAT, BASE_LON, lat, lon)
        if road_eta is None:
            road_eta = self.estimate_road_eta(distance, "Medium")  # fallback in hours

        drone_eta_mins = self.compute_drone_eta(distance)
        drone_eta_hours = drone_eta_mins / 60

        recommended_method = "Drone" if weather == "Clear" else "Road"

        return {
            "request_text": request_text,
            "area": area_name,
            "coordinates": {"lat": lat, "lon": lon},
            "distance_km": round(distance, 2),
            "priority": priority,
            "drone_eta": self.format_eta_hours_to_hhmm(drone_eta_hours),
            "road_eta": self.format_eta_hours_to_hhmm(road_eta),
            "recommended_method": recommended_method,
            "weather": weather,
            "traffic": traffic
        }
