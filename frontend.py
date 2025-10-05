import tkinter as tk
from tkinter import messagebox
import requests
from PIL import Image, ImageTk
import urllib.request
from io import BytesIO
from dotenv import load_dotenv
import os
import re

# Load environment variables from .env file
load_dotenv()

class WeatherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Weather Dashboard")
        self.root.geometry("600x600")  # Increased height for extra line
        self.root.configure(bg="#f0f0f0")

        # City input
        self.label = tk.Label(root, text="Enter City:", bg="#f0f0f0", font=("Arial", 12))
        self.label.pack(pady=10)
        self.city_entry = tk.Entry(root, font=("Arial", 12), width=20)
        self.city_entry.pack(pady=5)
        self.city_entry.bind("<Return>", lambda event: self.fetch_weather())
        self.city_entry.focus_set()

        # Submit button
        self.submit_btn = tk.Button(
            root, text="Get Weather", command=self.fetch_weather,
            bg="#007bff", fg="white", font=("Arial", 12)
        )
        self.submit_btn.pack(pady=5)

        # Weather display
        self.result_label = tk.Label(root, text="", bg="#f0f0f0", font=("Arial", 12), wraplength=550)
        self.result_label.pack(pady=10)

        # Forecast frame for horizontal layout
        self.forecast_frame = tk.Frame(root, bg="#f0f0f0")
        self.forecast_frame.pack(pady=10)
        self.forecast_labels = []  # Store labels for dynamic updates

        # Map display
        self.map_label = tk.Label(root, bg="#f0f0f0")
        self.map_label.pack(pady=10)

    def fetch_weather(self):
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showerror("Error", "Please enter a city name")
            return

        try:
            # --- Call Flask backend API for current weather ---
            response = requests.post("http://localhost:5000/api/weather", json={"city": city})
            data = response.json()

            if response.status_code != 200:
                messagebox.showerror("Error", data.get("error", "Unknown error"))
                return

            # --- Convert Celsius to Fahrenheit ---
            celsius = data['temp']
            fahrenheit = (celsius * 9/5) + 32
            # Sanitize description to remove any special characters
            description = re.sub(r'[^\w\s,.]', '', data['description']).capitalize()

            # --- Display current weather ---
            result = (
                f"{data['city']}\n"
                f"Temperature: {fahrenheit:.1f} F\n"
                f"Humidity: {data['humidity']}%\n"
                f"Description: {description}"
            )
            self.result_label.config(text=result)

            # --- Clear previous forecast labels ---
            for label in self.forecast_labels:
                label.destroy()
            self.forecast_labels.clear()

            # --- Call Flask backend API for 5-day forecast ---
            forecast_response = requests.post("http://localhost:5000/api/forecast", json={"city": city})
            print(f"Forecast response: {forecast_response.status_code}, {forecast_response.text}")  # Debug
            if forecast_response.status_code == 200:
                forecast_data = forecast_response.json()
                for i, item in enumerate(forecast_data['forecast']):
                    min_temp_f = (item['min_temp'] * 9/5) + 32
                    max_temp_f = (item['max_temp'] * 9/5) + 32
                    desc = re.sub(r'[^\w\s,.]', '', item['description']).capitalize()
                    # Include day of the week
                    forecast_text = f"{item['day']}\n{item['date']}\n{min_temp_f:.1f}-{max_temp_f:.1f} F\n{desc}"
                    label = tk.Label(
                        self.forecast_frame,
                        text=forecast_text,
                        bg="#ffffff",
                        font=("Arial", 9),
                        width=15,
                        height=5,  # Increased for extra line
                        relief="raised",
                        bd=1,
                        padx=5,
                        pady=5
                    )
                    label.grid(row=0, column=i, padx=5)
                    self.forecast_labels.append(label)
            else:
                error_label = tk.Label(
                    self.forecast_frame,
                    text=f"Forecast unavailable: {forecast_response.status_code} {forecast_response.text}",
                    bg="#f0f0f0",
                    font=("Arial", 9),
                    wraplength=550
                )
                error_label.grid(row=0, column=0, columnspan=5)
                self.forecast_labels.append(error_label)

            # --- Fetch coordinates from API response ---
            lat = data.get("lat")
            lon = data.get("lon")
            self.last_lat, self.last_lon = lat, lon

            # --- Fetch map image using LocationIQ Static Maps API ---
            if lat and lon:
                api_key = os.getenv("LocationIQKey")
                if not api_key:
                    raise ValueError("LocationIQ API key not found in .env file")
                map_url = (
                    f"https://maps.locationiq.com/v3/staticmap?"
                    f"key={api_key}&"
                    f"center={lat},{lon}&"
                    f"zoom=13&"
                    f"size=350x200&"
                    f"format=png&"
                    f"markers=icon:default|{lat},{lon}"
                )
                try:
                    req = urllib.request.Request(
                        map_url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    )
                    with urllib.request.urlopen(req) as u:
                        if u.getcode() == 401:
                            raise Exception("401 Unauthorized: Check your LocationIQ API key or restrictions.")
                        map_data = u.read()
                        map_img = Image.open(BytesIO(map_data)).resize((350, 200), Image.LANCZOS)
                        map_photo = ImageTk.PhotoImage(map_img)
                        self.map_label.config(image=map_photo)
                    self.map_label.image = map_photo
                except urllib.error.HTTPError as e:
                    if e.code == 401:
                        self.map_label.config(text="Map error: Invalid API key (401). Check dashboard.")
                    else:
                        self.map_label.config(text=f"Map error: {e.code}")
                except Exception as e:
                    self.map_label.config(text=f"Map unavailable: {str(e)}")
            else:
                self.map_label.config(text="Map unavailable (missing coordinates).")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch weather or map: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = WeatherApp(root)
    root.mainloop()