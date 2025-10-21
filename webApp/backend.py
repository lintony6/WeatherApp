from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import requests
from dotenv import load_dotenv
import os
from collections import defaultdict, Counter
from datetime import datetime, timedelta

# =========================
# Env & constants
# =========================
if os.path.exists(".env"):
    load_dotenv()

VISUALCROSSING_KEY = os.getenv("VisualCrossingKey")
LOCATIONIQ_KEY = os.getenv("LocationIQKey")

VC_TIMELINE      = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
LI_AUTOCOMP      = "https://api.locationiq.com/v1/autocomplete"

# =========================
# Flask app
# =========================
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.after_request
def after_request(resp):
    resp.headers.add("Access-Control-Allow-Origin", "*")
    resp.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    resp.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return resp

@app.route("/api/<path:any_path>", methods=["OPTIONS"])
def handle_options(any_path):
    r = make_response(jsonify({"message": "CORS preflight OK"}), 200)
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return r

@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "Weather API running"}), 200

# =========================
# HTTP helper
# =========================
def http_json(url, params, timeout=8):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        ct = r.headers.get("Content-Type", "")
        if "application/json" in ct or r.text.strip().startswith("{"):
            try:
                return r.status_code, r.json()
            except Exception:
                # last-ditch parse
                return r.status_code, {"text": r.text[:400]}
        return r.status_code, {"text": r.text[:400]}
    except requests.exceptions.RequestException as e:
        return 599, {"error": str(e)}

# =========================
# Coords helper
# =========================
def get_coords(body_or_city):
    if isinstance(body_or_city, dict):
        body = body_or_city
        if "lat" in body and "lon" in body:
            return float(body["lat"]), float(body["lon"]), body.get("label") or body.get("city") or "Unknown"
        city = body.get("city")
    else:
        city = str(body_or_city)

    if not city:
        raise ValueError("Please provide lat/lon or a city name.")

    s, j = http_json(LI_AUTOCOMP, {"key": LOCATIONIQ_KEY, "q": city, "limit": 1, "dedupe": 1}, timeout=6)
    if s == 200 and isinstance(j, list) and j:
        first = j[0]
        return float(first["lat"]), float(first["lon"]), first.get("display_name", city)
    raise ValueError("City not found")

# =========================
# Time helpers
# =========================
def local_today_date(tz_offset_sec: int):
    return (datetime.utcnow() + timedelta(seconds=tz_offset_sec)).date()

def local_day_bounds_utc(tz_offset_sec: int, ref_utc_ts: int | None = None):
    if ref_utc_ts is None:
        ref_utc_ts = int(datetime.utcnow().timestamp())
    local_now = datetime.utcfromtimestamp(ref_utc_ts + tz_offset_sec)
    start_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1) - timedelta(seconds=1)
    start_utc = int((start_local - timedelta(seconds=tz_offset_sec)).timestamp())
    end_utc = int((end_local - timedelta(seconds=tz_offset_sec)).timestamp())
    return start_utc, ref_utc_ts, end_utc

# =========================
# Visual Crossing caller
# =========================
def call_vc_timeline(lat, lon, date_range="", include="current,hours,days", units="metric"):
    """
    Call Visual Crossing Timeline API. Return (source, status, json)
    date_range: e.g., "today", "" for forecast, "2025-10-21/2025-10-25" for range
    """
    loc = f"{lat},{lon}"
    url = f"{VC_TIMELINE}{loc}"
    if date_range:
        url += f"/{date_range}"
    params = {
        "unitGroup": units,
        "key": VISUALCROSSING_KEY,
        "include": include,
        "contentType": "json",
    }
    s, j = http_json(url, params, timeout=8)
    return ("vc", s, j)

# =========================
# Today extremes computation (robust)
# =========================
def compute_today_extremes_metric(lat: float, lon: float):
    """
    Returns (min_c, max_c, tz_offset, source, vc_used) where vc_used is the timeline payload we can reuse.
    Uses Visual Crossing 'today' query with hourly data for true extremes (observed past + forecast future).
    """
    src, s_vc, vc = call_vc_timeline(lat, lon, "today", "current,hours,days")
    if s_vc != 200 or not isinstance(vc, dict):
        return (None, None, 0, "vc_error", {})

    tz_hours = vc.get("tzoffset", 0)
    tz = int(tz_hours * 3600)

    day_data = vc.get("days", [{}])[0]
    hours = day_data.get("hours", [])
    temps = [float(h["temp"]) for h in hours if "temp" in h and h["temp"] is not None]

    if temps:
        return (min(temps), max(temps), tz, f"{src}_hourly", vc)

    # Fallback to daily summary
    min_c = day_data.get("tempmin")
    max_c = day_data.get("tempmax")
    if min_c is not None and max_c is not None:
        return (float(min_c), float(max_c), tz, f"{src}_daily", vc)

    # Nothing usable
    return (None, None, tz, "insufficient_provider_data", vc)

# =========================
# Autocomplete
# =========================
@app.route("/api/autocomplete", methods=["GET"])
def get_autocomplete():
    q = request.args.get("q")
    if not q or len(q) < 2:
        return jsonify({"error": "Query parameter 'q' is required."}), 400
    try:
        r = requests.get(LI_AUTOCOMP, params={"key": LOCATIONIQ_KEY, "q": q, "limit": 5}, timeout=5)
        r.raise_for_status()
        return jsonify(r.json())
    except requests.exceptions.RequestException as e:
        print("LocationIQ error:", e)
        return jsonify([]), 500

# =========================
# /api/weather
# =========================
@app.route("/api/weather", methods=["POST"])
def get_weather():
    try:
        body = request.get_json(silent=True) or {}
        city = body.get("city")
        lat, lon, label = get_coords(body if body else city)

        # Compute today's full-day extremes (or best-effort)
        today_min, today_max, tz, today_src, vc_used = compute_today_extremes_metric(lat, lon)

        # Current conditions
        cur = vc_used.get("currentConditions", {})
        day_data = vc_used.get("days", [{}])[0]

        current_temp = float(cur.get("temp", 0.0))
        feels_like = float(cur.get("feelslike", current_temp))
        humidity = cur.get("humidity", 0)
        pressure = cur.get("pressure", 0)
        wind_speed = cur.get("windspeed", 0)  # km/h in metric
        sunrise = day_data.get("sunriseEpoch")
        sunset = day_data.get("sunsetEpoch")
        desc = cur.get("conditions", "N/A")
        icon = cur.get("icon", "")

        # Always bound today's extremes with current
        if today_min is None or today_max is None:
            today_min = current_temp
            today_max = current_temp
            if today_src == "vc_error":
                today_src = "current_only_vc_failed"
            elif today_src == "insufficient_provider_data":
                today_src = "current_only_no_daily_no_history"
        else:
            today_min = min(today_min, current_temp)
            today_max = max(today_max, current_temp)

        map_url = (
            f"https://maps.locationiq.com/v3/staticmap"
            f"?key={LOCATIONIQ_KEY}&center={lat},{lon}&zoom=12&size=600x400&format=png"
            f"&markers=icon:large-red-cutout|{lat},{lon}"
        )

        return jsonify({
            "units": "metric",
            "city": label,
            "lat": lat,
            "lon": lon,
            "description": desc,
            "icon": icon,
            "temp": round(current_temp, 1),
            "feels_like": round(feels_like, 1),
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,  # km/h
            "sunrise": sunrise,
            "sunset": sunset,
            "daily_low": round(float(today_min), 1),
            "daily_high": round(float(today_max), 1),
            "today_source": today_src,
            "map_url": map_url
        }), 200

    except Exception as e:
        print("Error in /api/weather:", e)
        return jsonify({"error": "Error fetching weather data"}), 500

# =========================
# /api/forecast
# =========================
@app.route("/api/forecast", methods=["POST"])
def get_forecast():
    try:
        body = request.get_json(silent=True) or {}
        city = body.get("city")
        lat, lon, label = get_coords(body if body else city)

        # Compute today's true extremes and tz once
        true_today_min, true_today_max, tz, today_src, vc_used = compute_today_extremes_metric(lat, lon)
        today_key = local_today_date(tz).strftime("%Y-%m-%d")

        # Compute date range for 5 days including today
        end_date = local_today_date(tz) + timedelta(days=4)
        date_range = f"{today_key}/{end_date.strftime('%Y-%m-%d')}"

        # Fetch daily forecast for the range
        src, s_vc, vc = call_vc_timeline(lat, lon, date_range, "days")

        forecast = []

        if s_vc == 200 and isinstance(vc, dict) and vc.get("days"):
            for d in vc["days"]:
                date_key = d["datetime"]
                local_dt = datetime.strptime(date_key, "%Y-%m-%d")
                min_t = d.get("tempmin")
                max_t = d.get("tempmax")

                # If this is today, fold in the corrected extremes
                if date_key == today_key:
                    if true_today_min is not None:
                        min_t = min(min_t, true_today_min)
                    if true_today_max is not None:
                        max_t = max(max_t, true_today_max)

                forecast.append({
                    "date": date_key,
                    "day": local_dt.strftime("%A"),
                    "min_temp": round(float(min_t), 1),
                    "max_temp": round(float(max_t), 1),
                    "description": d.get("conditions", ""),
                    "icon": d.get("icon"),
                })

        else:
            # Last resort: return only today with extremes
            only_today = {
                "date": today_key,
                "day": datetime.strptime(today_key, "%Y-%m-%d").strftime("%A"),
                "min_temp": round(float(true_today_min or 0.0), 1),
                "max_temp": round(float(true_today_max or 0.0), 1),
                "description": "",
                "icon": None
            }
            return jsonify({"units": "metric", "city": label, "forecast": [only_today]}), 200

        return jsonify({"units": "metric", "city": label, "forecast": forecast}), 200

    except Exception as e:
        print("Error in /api/forecast:", e)
        return jsonify({"error": "Error fetching forecast data"}), 500

# =========================
# Local dev
# =========================
if __name__ == "__main__":
    app.run(port=5000, debug=True)