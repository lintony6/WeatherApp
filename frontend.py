import tkinter as tk
from tkinter import messagebox
import requests
from PIL import Image, ImageTk
import urllib.request
from io import BytesIO
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class WeatherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Weather Dashboard")
        self.root.geometry("400x550")
        self.root.configure(bg="#f0f0f0")

        # City input
        self.label = tk.Label(root, text="Enter City:", bg="#f0f0f0", font=("Arial", 12))
        self.label.pack(pady=10)
        self.city_entry = tk.Entry(root, font=("Arial", 12), width=20)
        self.city_entry.pack(pady=5)
        # Bind Enter key to fetch_weather
        self.city_entry.bind("<Return>", lambda event: self.fetch_weather())

        # Submit button
        self.submit_btn = tk.Button(
            root, text="Get Weather", command=self.fetch_weather,
            bg="#007bff", fg="white", font=("Arial", 12)
        )
        self.submit_btn.pack(pady=5)

        # Weather display
        self.result_label = tk.Label(root, text="", bg="#f0f0f0", font=("Arial", 12), wraplength=350)
        self.result_label.pack(pady=10)

        # Weather icon
        self.icon_label = tk.Label(root, bg="#f0f0f0")
        self.icon_label.pack(pady=5)

        # Map display
        self.map_label = tk.Label(root, bg="#f0f0f0")
        self.map_label.pack(pady=10)

    def fetch_weather(self):
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showerror("Error", "Please enter a city name")
            return

        try:
            # --- Call Flask backend API ---
            response = requests.post("http://localhost:5000/api/weather", json={"city": city})
            data = response.json()

            if response.status_code != 200:
                messagebox.showerror("Error", data.get("error", "Unknown error"))
                return

            # --- Convert Celsius to Fahrenheit ---
            celsius = data['temp']
            fahrenheit = (celsius * 9/5) + 32

            # --- Display weather info ---
            result = (
                f"{data['city']}\n"
                f"Temperature: {fahrenheit:.1f}°F\n"
                f"Humidity: {data['humidity']}%\n"
                f"Description: {data['description'].capitalize()}"
            )
            self.result_label.config(text=result)

            # --- Weather icon ---
            icon_url = f"http://openweathermap.org/img/wn/{data['icon']}@2x.png"
            with urllib.request.urlopen(icon_url) as u:
                raw_data = u.read()
            img = Image.open(BytesIO(raw_data)).resize((50, 50), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.icon_label.config(image=photo)
            self.icon_label.image = photo

            # --- Fetch coordinates from API response ---
            lat = data.get("lat")
            lon = data.get("lon")

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