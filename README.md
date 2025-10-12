# WeatherApp

WeatherApp provides current weather information and a 5-day forecast for any city, with both desktop and web versions.  
It uses the OpenWeatherMap and LocationIQ APIs to display real-time weather data and maps.

---

## Versions

**Desktop App:**  
A Python-based application with a Tkinter GUI and Flask backend.  

**Web App:**  
A browser-based version built with HTML, CSS, and JavaScript, using a Flask backend deployed to AWS Lambda (via Zappa) and hosted with AWS Amplify.  
Link: https://main.d2itnc7lavde7x.amplifyapp.com/
---

## Features

**Both Versions:**
- Current weather display: temperature (°F), humidity, and description  
- 5-day forecast: day, date, min–max temperature, and weather summary  
- Map display centered on the selected city  

**Web App Only:**
- Autocomplete city search suggestions  
- Fully serverless, cloud-hosted backend  

---

## Requirements

### Desktop App
- **OS:** Linux  
- **Python:** 3.6+  
- **Dependencies:**  
  - Python packages: flask, requests, python-dotenv, Pillow, tkinter  
  - System package: python3-tkinter

### Web App
- **Frontend:** HTML, CSS, JavaScript  
- **Backend:** Flask (Python 3.11), deployed with Zappa on AWS Lambda  
- **Hosting:** AWS Amplify (static site hosting)  

---

## API Keys
Both versions require:
- OpenWeatherMap API Key — weather and forecast data  
- LocationIQ API Key — static map and autocomplete data  

Get your keys from:
- https://home.openweathermap.org/api_keys  
- https://locationiq.com  

Add them to a `.env` file in each app directory:
```
OpenWeatherMapAPIKey=your_openweather_key
LocationIQKey=your_locationiq_key
```

---

## Setup Instructions

### Desktop App

1. Navigate to the desktop folder:
   ```
   cd desktopapp
   ```
2. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the backend:
   ```
   python backend.py
   ```
5. Run the frontend:
   ```
   python frontend.py
   ```
6. Enter a city name (e.g., “New York”) and view current weather, forecast, and map.

---

### Web App

1. Navigate to the web folder:
   ```
   cd webapp
   ```
2. Create a virtual environment and install dependencies:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Deploy the backend to AWS Lambda:
   ```
   zappa deploy dev
   ```
4. Note the API URL printed in the terminal (example):
   ```
   https://xxxxx.execute-api.us-east-1.amazonaws.com/dev
   ```
5. Set that URL in `script.js`:
   ```
   const BACKEND_URL = "https://xxxxx.execute-api.us-east-1.amazonaws.com/dev";
   ```
6. Push your code to GitHub — Amplify will automatically build and host your site.

---

## Project Structure
```
WeatherApp/
├── desktopapp/
│   ├── frontend.py
│   ├── backend.py
│   ├── requirements.txt
│   ├── .env
│   └── venv/
│
├── webapp/
│   ├── backend.py
│   ├── index.html
│   ├── script.js
│   ├── style.css
│   ├── requirements.txt
│   ├── .env
│   └── zappa_settings.json
│
├── .gitignore
├── amplify.yml
└── README.md
```

---

## APIs Used
- OpenWeatherMap: Current weather & 5-day forecast  
- LocationIQ: Autocomplete & static map images  

---

## Notes
- Both versions share similar logic but are deployed differently.  
- The web version is optimized for AWS free tier (1M requests/month).  

---

## License
This project is licensed under the MIT License.
