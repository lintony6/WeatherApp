from flask import Flask, jsonify, request
import requests
from dotenv import load_dotenv
import os
from collections import defaultdict
from datetime import datetime

# Load environment variables
load_dotenv()

# --- Load BOTH API keys from your .env file ---
OPENWEATHER_KEY = os.getenv("OpenWeatherMapAPIKey")
LOCATIONIQ_KEY = os.getenv("LocationIQKey")

if not OPENWEATHER_KEY:
    raise ValueError("OpenWeatherMapAPIKey not found in .env file")
if not LOCATIONIQ_KEY:
    raise ValueError("LocationIQKey not found in .env file")

BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast"

app = Flask(__name__)

# --- NEW: Secure endpoint for autocomplete suggestions ---
@app.route("/api/autocomplete", methods=["GET"])
def get_autocomplete():
    query = request.args.get("q")
    if not query or len(query) < 2:
        return jsonify({"error": "Query parameter 'q' is required."}), 400

    try:
        url = f"https://api.locationiq.com/v1/autocomplete?key={LOCATIONIQ_KEY}&q={query}&limit=5"
        response = requests.get(url, timeout=3)
        response.raise_for_status() # Raise an error for bad status codes
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Error calling LocationIQ: {e}")
        return jsonify([]), 500

# --- MODIFIED: Weather endpoint now also generates the map URL ---
@app.route("/api/weather", methods=["POST"])
def get_weather():
    city = request.json.get("city")
    if not city:
        return jsonify({"error": "Please enter a city name"}), 400

    try:
        response = requests.get(BASE_URL, params={
            "q": city,
            "appid": OPENWEATHER_KEY,
            "units": "metric"  # Celsius
        })
        data = response.json()

        if data.get("cod") != 200:
            return jsonify({"error": data.get("message", "City not found")}), 404

        lat = data["coord"]["lat"]
        lon = data["coord"]["lon"]
        
        # Construct the secure map URL on the backend
        map_url = (
            f"https://maps.locationiq.com/v3/staticmap?"
            f"key={LOCATIONIQ_KEY}&"
            f"center={lat},{lon}&"
            f"zoom=13&size=600x400&format=png&"
            f"markers=icon:default|{lat},{lon}"
        )

        weather = {
            "city": data["name"],
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"],
            "lat": lat,
            "lon": lon,
            "map_url": map_url
        }
        return jsonify(weather), 200

    except Exception as e:
        print("Error in /api/weather:", e)
        return jsonify({"error": "Error fetching weather data"}), 500

# --- Forecast endpoint ---
@app.route("/api/forecast", methods=["POST"])
def get_forecast():
    city = request.json.get("city")
    if not city:
        return jsonify({"error": "Please enter a city name"}), 400

    try:
        response = requests.get(FORECAST_URL, params={
            "q": city,
            "appid": OPENWEATHER_KEY,
            "units": "metric"
        })
        data = response.json()

        if data.get("cod") != "200":
            return jsonify({"error": data.get("message", "City not found")}), 404

        daily_data = defaultdict(lambda: {"temps": [], "descriptions": []})
        for item in data['list']:
            date = item['dt_txt'][:10]
            daily_data[date]["temps"].append(item['main']['temp'])
            daily_data[date]["descriptions"].append(item['weather'][0]['description'])

        forecast = []
        for date in sorted(daily_data.keys())[:5]:
            temps = daily_data[date]["temps"]
            descriptions = daily_data[date]["descriptions"]
            description = max(set(descriptions), key=descriptions.count)
            day_of_week = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
            forecast.append({
                "date": date, "day": day_of_week, "min_temp": min(temps),
                "max_temp": max(temps), "description": description,
                "icon": data['list'][0]['weather'][0]['icon']
            })

        return jsonify({"city": data['city']['name'], "forecast": forecast}), 200

    except Exception as e:
        print("Error in /api/forecast:", e)
        return jsonify({"error": "Error fetching forecast data"}), 500

# --- This block makes the server run ---
if __name__ == "__main__":
    print("🚀 Starting Flask backend server at http://127.0.0.1:5000")
    app.run(port=5000, debug=True)