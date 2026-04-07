import sqlite3
import os
import sys
import requests
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import json
import random
import traceback

# ─────────────────────────────────────────────────────────────
# Safe Windows Timestamp (avoids [Errno 22] from strftime locale bug)
# ─────────────────────────────────────────────────────────────
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def safe_timestamp(dt=None):
    """Build a human-readable timestamp without locale-dependent strftime."""
    if dt is None:
        dt = datetime.now()
    day_name = DAYS[dt.weekday()]
    month_name = MONTHS[dt.month - 1]
    hour = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{day_name}, {dt.day:02d} {month_name} {dt.year} | {hour:02d}:{dt.minute:02d} {ampm}"

def safe_day_abbr(dt):
    """Return 3-letter day abbreviation without locale strftime."""
    return DAYS[dt.weekday()][:3]

# ─────────────────────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)

# 🔑 No API key required for Open-Meteo!
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

DATABASE = os.path.join(os.path.dirname(__file__), "weather.db")

def decode_weathercode(code):
    """Convert open-meteo WMO codes to Marathi descriptions and emojis."""
    if code == 0: return ("स्वच्छ आकाश", "☀️")
    if code in [1, 2, 3]: return ("ढगाळ वातावरण", "☁️")
    if code in [45, 48]: return ("धुके", "🌫️")
    if code in [51, 53, 55, 56, 57]: return ("हलका पाऊस", "🌧️")
    if code in [61, 63, 65, 66, 67]: return ("पाऊस", "🌧️")
    if code in [71, 73, 75, 77]: return ("बर्फ", "❄️")
    if code in [80, 81, 82]: return ("मध्यम पाऊस", "🌦️")
    if code in [85, 86]: return ("बर्फाचा वर्षाव", "🌨️")
    if code in [95, 96, 99]: return ("गडगडाटासह पाऊस", "⚡")
    return ("अज्ञात", "🌤️")


# ─────────────────────────────────────────────────────────────
# Database Helper Functions
# ─────────────────────────────────────────────────────────────

def get_db_connection():
    """Create and return a database connection with row_factory."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Allows dict-like row access
    return conn

MAHARASHTRA_CITIES = [
    ("Mumbai", 19.07, 72.87),
    ("Pune", 18.52, 73.85),
    ("Nagpur", 21.15, 79.09),
    ("Nashik", 19.99, 73.79),
    ("Chhatrapati Sambhaji Nagar", 19.87, 75.34),
    ("Shirdi", 19.76, 74.48),
    ("Solapur", 17.67, 75.91),
    ("Amravati", 20.93, 77.75),
    ("Kolhapur", 16.70, 74.24),
    ("Sangli", 16.85, 74.56),
    ("Jalgaon", 21.01, 75.56),
    ("Akola", 20.71, 77.00),
    ("Latur", 18.40, 76.56),
    ("Dhule", 20.90, 74.77),
    ("Ahmednagar", 19.09, 74.74),
    ("Chandrapur", 19.96, 79.30),
    ("Parbhani", 19.27, 76.78),
    ("Nanded", 19.14, 77.32),
    ("Beed", 18.99, 75.76),
    ("Ratnagiri", 16.99, 73.31),
    ("Satara", 17.68, 74.02),
    ("Wardha", 20.75, 78.60),
    ("Yavatmal", 20.39, 78.13),
    ("Gondia", 21.46, 80.20),
    ("Bhandara", 21.17, 79.65),
    ("Hingoli", 19.72, 77.14),
    ("Osmanabad", 18.18, 76.04),
    ("Palghar", 19.70, 72.76),
    ("Thane", 19.22, 72.97),
    ("Panvel", 18.99, 73.10)
]

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            latitude REAL,
            longitude REAL,
            temperature REAL,
            windspeed REAL,
            weather_json TEXT,
            last_updated TEXT
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM cities")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO cities (name, latitude, longitude) VALUES (?, ?, ?)",
            MAHARASHTRA_CITIES
        )
        print(f"[ SUCCESS ] Inserted {len(MAHARASHTRA_CITIES)} default cities into DB.")

    conn.commit()
    conn.close()

def get_all_cities():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cities ORDER BY name ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[ ERROR ] DB Error: {e}")
        return []

def get_city_by_name(name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cities WHERE name COLLATE NOCASE = ?", (name.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_city_to_db(name, lat, lon):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO cities (name, latitude, longitude) VALUES (?, ?, ?)",
            (name, lat, lon)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        return False

def update_city_weather(city_id, temp, wind, weather_json=None):
    """Update a specific city with fresh weather data."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE cities 
            SET temperature = ?, windspeed = ?, weather_json = ?, last_updated = ?
            WHERE id = ?
        """, (temp, wind, json.dumps(weather_json) if weather_json else None, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), city_id))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"[ ERROR ] DB Update Error: {e}")

def update_all_cities_weather_loop():
    """Background task to update weather for a subset (5 cities) every 10 mins."""
    last_index = 0
    while True:
        print("[ UPDATE ] Background cycle: Fetching fresh weather for a batch of cities...")
        cities = get_all_cities()
        if not cities:
            time.sleep(60)
            continue
            
        # Select next 5 cities to update
        batch_size = 5
        batch = []
        for i in range(batch_size):
            batch.append(cities[(last_index + i) % len(cities)])
        last_index = (last_index + batch_size) % len(cities)
        
        print(f"[ UPDATE ] Updating batch: {[c['name'] for c in batch]}")
        
        for city in batch:
            try:
                # Full weather fetch logic for background update to populate JSON
                # Calling fetch_weather(city['name']) would be an easy shortcut,
                # but we'll implement a slightly lighter version to be safe.
                params = {
                    "latitude": city["latitude"],
                    "longitude": city["longitude"],
                    "current_weather": "true",
                    "daily": "weathercode,temperature_2m_max,temperature_2m_min",
                    "timezone": "auto",
                    "forecast_days": 8
                }
                res = requests.get(WEATHER_URL, params=params, timeout=10)
                if res.status_code == 200:
                    w_data = res.json()
                    current = w_data["current_weather"]
                    daily = w_data["daily"]
                    
                    desc, emoji = decode_weathercode(current["weathercode"])
                    forecast = []
                    for i in range(0, 7):
                        try:
                            d_obj = datetime.strptime(daily["time"][i], "%Y-%m-%d")
                            f_desc, f_emoji = decode_weathercode(daily["weathercode"][i])
                            forecast.append({
                                "day": safe_day_abbr(d_obj),
                                "emoji": f_emoji,
                                "max": round(daily["temperature_2m_max"][i]),
                                "min": round(daily["temperature_2m_min"][i]),
                                "weathercode": daily["weathercode"][i]
                            })
                        except: pass
                        
                    weather = {
                        "city": city["name"],
                        "temp": round(current["temperature"], 1),
                        "wind_speed": current["windspeed"],
                        "condition": desc,
                        "icon": emoji,
                        "weathercode": current["weathercode"],
                        "timestamp": safe_timestamp(),
                        "forecast": forecast
                    }
                    update_city_weather(city["id"], weather["temp"], weather["wind_speed"], weather)
                elif res.status_code == 429:
                    print(f"[ WARNING ] Rate limited during update of {city['name']}. Backing off.")
                    time.sleep(60) # Longer backoff
            except Exception as e:
                print(f"[ WARNING ] Error updating {city['name']}: {e}")
            # Space out requests within batch
            time.sleep(5) 
        
        print("[ SUCCESS ] Batch update complete. Sleeping for 10 minutes.")
        time.sleep(600) # 10 minutes

# ─────────────────────────────────────────────────────────────
# Weather API Helper
# ─────────────────────────────────────────────────────────────

def fetch_weather(city_name):
    """
    Fetch weather data using Open-Meteo API.
    Bypasses geocoding if lat/lon is found in SQLite.
    """
    try:
        db_city = get_city_by_name(city_name)
        
        # Check cache (15 mins)
        if db_city and db_city["weather_json"] and db_city["last_updated"]:
            try:
                last_updated = datetime.strptime(db_city["last_updated"], "%Y-%m-%d %H:%M:%S")
                diff = (datetime.now() - last_updated).total_seconds() / 60
                if diff < 10:
                    print(f"[ CACHE ] Serving {db_city['name']} from database (updated {round(diff)} mins ago).")
                    return {"success": True, "data": json.loads(db_city["weather_json"])}
            except Exception as e:
                print(f"[ CACHE ERROR ] {e}")

        if db_city:
            lat = db_city["latitude"]
            lon = db_city["longitude"]
            city_clean = db_city["name"]
            city_id = db_city["id"]
        else:
            # Not in DB -> Geocode it (Restrict to India context)
            search_query = f"{city_name},India"
            geo_params = {"name": search_query, "count": 5}
            geo_res = requests.get(GEOCODING_URL, params=geo_params, timeout=10)
            
            if geo_res.status_code != 200:
                if geo_res.status_code == 429:
                    return {"success": False, "error": "Geocoding API rate limited. Try again later."}
                return {"success": False, "error": "Geocoding API error"}
            
            geo_data = geo_res.json()
            if not geo_data.get("results"):
                return {"success": False, "error": "City not found ❌"}
                
            india_results = [r for r in geo_data["results"] if r.get("country_code", "").upper() == "IN"]
            
            if not india_results:
                 return {"success": False, "error": "City not found in India ❌"}

            location = india_results[0]
            lat = location["latitude"]
            lon = location["longitude"]
            city_clean = location["name"]
            
            add_city_to_db(city_clean, lat, lon)
            # Re-fetch to get ID
            db_city = get_city_by_name(city_clean)
            city_id = db_city["id"] if db_city else None

        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
            "daily": "weathercode,temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
            "forecast_days": 8
        }
        weather_res = requests.get(WEATHER_URL, params=weather_params, timeout=10)
        
        if weather_res.status_code != 200:
            print(f"[ API ERROR ] Weather API failed with status {weather_res.status_code}: {weather_res.text}")
            
            # RESILIENCY: Fallback to STALE cache if API is rate-limited or fails
            if db_city and db_city["weather_json"]:
                print(f"[ FALLBACK ] Serving STALE data for {db_city['name']} due to API error {weather_res.status_code}")
                stale_data = json.loads(db_city["weather_json"])
                # Note: We keep the original timestamp so user knows it's old
                return {"success": True, "data": stale_data, "note": "Showing cached data due to API limits."}

            if weather_res.status_code == 429:
                return {"success": False, "error": "Weather API rate limited. Try again in a few minutes."}
            return {"success": False, "error": f"Weather API error (Status: {weather_res.status_code})"}
            
        w_data = weather_res.json()
        current = w_data["current_weather"]
        daily = w_data["daily"]

        condition_desc, condition_emoji = decode_weathercode(current["weathercode"])

        forecast = []
        for i in range(0, 7):
            try:
                date_obj = datetime.strptime(daily["time"][i], "%Y-%m-%d")
                f_desc, f_emoji = decode_weathercode(daily["weathercode"][i])
                forecast.append({
                    "day": safe_day_abbr(date_obj),
                    "emoji": f_emoji,
                    "max": round(daily["temperature_2m_max"][i]),
                    "min": round(daily["temperature_2m_min"][i]),
                    "weathercode": daily["weathercode"][i]
                })
            except (IndexError, KeyError):
                pass

        weather = {
            "city": city_clean,
            "temp": round(current["temperature"], 1),
            "wind_speed": current["windspeed"],
            "condition": condition_desc,
            "icon": condition_emoji,
            "weathercode": current["weathercode"],
            "timestamp": safe_timestamp(),
            "forecast": forecast
        }

        # Save to cache
        if city_id:
            update_city_weather(city_id, weather["temp"], weather["wind_speed"], weather)

        return {"success": True, "data": weather}

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[ FATAL ERROR ] fetch_weather crashed:\n{tb}")
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

# ─────────────────────────────────────────────────────────────
# Flask Routes
# ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/weather", methods=["POST"])
def get_weather():
    data = request.get_json()
    city_name = data.get("city", "").strip()

    if not city_name:
        return jsonify({"success": False, "error": "Please enter a city name."})

    result = fetch_weather(city_name)
    return jsonify(result)

@app.route("/api/cities", methods=["GET"])
def api_get_cities():
    cities = get_all_cities()
    return jsonify({"success": True, "cities": cities})

@app.route("/api/suggestions")
def get_suggestions():
    query = request.args.get("q", "").strip()
    print(f"DEBUG: Suggestion query: '{query}'")
    if not query:
        return jsonify([])
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM cities WHERE name LIKE ? LIMIT 10", (f"{query}%",))
        matches = [row["name"] for row in cursor.fetchall()]
        conn.close()
        print(f"DEBUG: Found {len(matches)} matches: {matches}")
        return jsonify(matches)
    except sqlite3.Error as e:
        print(f"DEBUG: SQL Error: {e}")
        return jsonify([])

@app.route("/add_city", methods=["POST"])
def api_add_city():
    data = request.get_json()
    city_name = data.get("city", "").strip()
    if not city_name:
        return jsonify({"success": False, "error": "City name is required"})
        
    result = fetch_weather(city_name)
    return jsonify(result)

if __name__ == "__main__":
    init_db()
    # Background update RE-ENABLED with staggered logic (5 cities every 10 min)
    threading.Thread(target=update_all_cities_weather_loop, daemon=True).start()
    app.run(debug=True, use_reloader=False) # use_reloader=False prevents double thread start
