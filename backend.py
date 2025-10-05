from flask import Flask, jsonify, request
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get API key from .env
API_KEY = os.getenv("OpenWeatherMapAPIKey")
if not API_KEY:
    raise ValueError("OpenWeatherMapAPIKey not found in .env file")

BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

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
        print("Error:", e)
        return jsonify({"error": "Error fetching weather data"}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
