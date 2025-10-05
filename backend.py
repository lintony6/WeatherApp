from flask import Flask, jsonify, request
import requests
from dotenv import load_dotenv
import os
from collections import defaultdict
from datetime import datetime

# Load environment variables
load_dotenv()

# Get API key from .env
API_KEY = os.getenv("OpenWeatherMapAPIKey")
if not API_KEY:
    raise ValueError("OpenWeatherMapAPIKey not found in .env file")
print("Backend started with API_KEY:", API_KEY[:4] + "..." + API_KEY[-4:])  # Debug

BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast"

app = Flask(__name__)

@app.route("/api/weather", methods=["POST"])
def get_weather():
    city = request.json.get("city")
    if not city:
        return jsonify({"error": "Please enter a city name"}), 400

    try:
        response = requests.get(BASE_URL, params={
            "q": city,
            "appid": API_KEY,
            "units": "metric"  # Celsius
        })
        data = response.json()

        if data.get("cod") != 200:
            return jsonify({"error": data.get("message", "City not found")}), 404

        weather = {
            "city": data["name"],
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"],
            "lat": data["coord"]["lat"],
            "lon": data["coord"]["lon"]
        }
        return jsonify(weather), 200

    except Exception as e:
        print("Error in /api/weather:", e)
        return jsonify({"error": "Error fetching weather data"}), 500

@app.route("/api/forecast", methods=["POST"])
def get_forecast():
    city = request.json.get("city")
    if not city:
        return jsonify({"error": "Please enter a city name"}), 400

    try:
        response = requests.get(FORECAST_URL, params={
            "q": city,
            "appid": API_KEY,
            "units": "metric"  # Celsius
        })
        data = response.json()

        if data.get("cod") != "200":
            return jsonify({"error": data.get("message", "City not found")}), 404

        # Group 3-hourly data by date
        daily_data = defaultdict(lambda: {"temps": [], "descriptions": []})
        for item in data['list']:
            date = item['dt_txt'][:10]  # YYYY-MM-DD
            daily_data[date]["temps"].append(item['main']['temp'])
            daily_data[date]["descriptions"].append(item['weather'][0]['description'])

        # Create forecast with min/max temps, day of week, and most common description
        forecast = []
        for date in sorted(daily_data.keys())[:5]:  # Up to 5 days
            temps = daily_data[date]["temps"]
            descriptions = daily_data[date]["descriptions"]
            description = max(set(descriptions), key=descriptions.count)
            # Calculate day of the week
            day_of_week = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
            forecast.append({
                "date": date,
                "day": day_of_week,
                "min_temp": min(temps),
                "max_temp": max(temps),
                "description": description,
                "icon": data['list'][0]['weather'][0]['icon']
            })

        return jsonify({
            "city": data['city']['name'],
            "forecast": forecast
        }), 200

    except Exception as e:
        print("Error in /api/forecast:", e)
        return jsonify({"error": "Error fetching forecast data"}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)