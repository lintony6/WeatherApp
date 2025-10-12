WeatherApp

WeatherApp provides current weather information and a 5-day forecast for any city, with both desktop and web versions.
It uses the OpenWeatherMap and LocationIQ APIs to display real-time weather data and maps.

Desktop App:
A Python-based application with a Tkinter GUI and Flask backend.

Web App:
A browser-based version built with HTML, CSS, and JavaScript, using a Flask backend deployed to AWS Lambda (via Zappa) and hosted with AWS Amplify.

✨ Features

Both Versions:

Current weather display: temperature (°F), humidity, and description

5-day forecast: day, date, min–max temperature, and weather summary

Map display centered on the selected city

Web App Only:

Fully serverless, cloud-hosted backend

🧰 Requirements
Desktop App

OS: Linux

Python: 3.6+

Dependencies:

Python packages: flask, requests, python-dotenv, Pillow, tkinter

System package: python3-tkinter

Web App

Frontend: HTML, CSS, JavaScript

Backend: Flask (Python 3.11), deployed with Zappa on AWS Lambda

Hosting: AWS Amplify (static site hosting)

🔑 API Keys

Both versions require:

OpenWeatherMap API Key — weather and forecast data

LocationIQ API Key — static map and autocomplete data

Get your keys from:

https://home.openweathermap.org/api_keys