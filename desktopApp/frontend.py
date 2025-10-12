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

class AutocompleteEntry(tk.Entry):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.listbox = None
        self.suggestions = []
        self.suggestion_cache = {}  # Cache for query -> suggestions
        self.debounce_id = None  # For debouncing API calls
        self.debounce_delay = 300  # Milliseconds to wait before API call
        self.bind("<KeyRelease>", self.on_keyrelease)
        self.bind("<FocusOut>", self.hide_listbox)
        self.bind("<Return>", self.on_return)
        self.bind("<Down>", self.move_to_listbox)
        self.locationiq_key = os.getenv("LocationIQKey")
        if not self.locationiq_key:
            raise ValueError("LocationIQ API key not found in .env file")

    def on_keyrelease(self, event):
        """Handle key release events with debouncing."""
        if event.keysym in ("Up", "Down", "Return", "Escape"):
            return

        query = self.get().strip()
        if len(query) < 2:  # Minimum characters to trigger autocomplete
            self.hide_listbox()
            return

        # Cancel any pending debounce
        if self.debounce_id:
            self.after_cancel(self.debounce_id)

        # Schedule new API call with debounce
        self.debounce_id = self.after(self.debounce_delay, lambda: self.fetch_and_update(query))

    def fetch_and_update(self, query):
        """Fetch suggestions and update listbox."""
        # Check cache first
        if query in self.suggestion_cache:
            self.suggestions = self.suggestion_cache[query]
        else:
            # Fetch from API and cache result
            self.suggestions = self.fetch_suggestions(query)
            self.suggestion_cache[query] = self.suggestions
        self.update_listbox()

    def fetch_suggestions(self, query):
        """Fetch city suggestions from LocationIQ autocomplete API."""
        try:
            url = f"https://api.locationiq.com/v1/autocomplete?key={self.locationiq_key}&q={query}&limit=5"
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                # Extract city names (and country for clarity)
                suggestions = [f"{item['display_name']}" for item in data]
                return suggestions
            else:
                return []
        except Exception:
            return []

    def update_listbox(self):
        """Update the dropdown listbox with current suggestions."""
        self.hide_listbox()

        if not self.suggestions:
            return

        # Create listbox
        self.listbox = tk.Listbox(
            self.parent,
            height=len(self.suggestions),
            width=self.winfo_width() // 8,
            font=("Arial", 12),
            selectmode=tk.SINGLE,  # Ensure single selection
            selectbackground="#007bff",  # Highlight color
            selectforeground="white"  # Text color when highlighted
        )
        self.listbox.place(x=self.winfo_x(), y=self.winfo_y() + self.winfo_height())

        # Populate listbox
        for suggestion in self.suggestions:
            self.listbox.insert(tk.END, suggestion)

        # Bind listbox events
        self.listbox.bind("<Button-1>", self.on_select)  # Handle mouse click
        self.listbox.bind("<<ListboxSelect>>", self.on_select)  # Handle keyboard selection
        self.listbox.bind("<Return>", self.on_select)
        self.listbox.bind("<Escape>", lambda e: self.hide_listbox())
        self.listbox.bind("<Motion>", self.on_motion)  # Handle mouse hover

    def on_motion(self, event):
        """Highlight the item under the cursor."""
        if self.listbox:
            # Get the index of the item under the cursor
            index = self.listbox.nearest(event.y)
            if index >= 0:  # Ensure valid index
                self.listbox.selection_clear(0, tk.END)  # Clear previous selection
                self.listbox.selection_set(index)  # Highlight new item
                self.listbox.activate(index)  # Set active item for visual feedback

    def hide_listbox(self, event=None):
        """Hide the listbox if it exists."""
        if self.listbox:
            self.listbox.destroy()
            self.listbox = None

    def on_select(self, event=None):
        """Handle selection from listbox."""
        if self.listbox and self.listbox.curselection():
            index = self.listbox.curselection()[0]  # Get the index of the selected item
            selection = self.listbox.get(index)  # Get the text at the selected index
            self.delete(0, tk.END)
            self.insert(0, selection)
            self.hide_listbox()
            self.focus_set()
            self.parent.event_generate("<Return>")

    def on_return(self, event):
        """Pass Return event to parent for weather fetching."""
        self.hide_listbox()
        self.parent.event_generate("<Return>")

    def move_to_listbox(self, event):
        """Move focus to listbox when Down arrow is pressed."""
        if self.listbox:
            self.listbox.focus_set()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(0)
            self.listbox.activate(0)
class WeatherApp:
    # ... (Your existing WeatherApp class remains unchanged)
    def __init__(self, root):
        self.root = root
        self.root.title("Weather Dashboard")
        self.root.geometry("600x600")
        self.root.configure(bg="#f0f0f0")

        self.label = tk.Label(root, text="Enter City:", bg="#f0f0f0", font=("Arial", 12))
        self.label.pack(pady=10)
        self.city_entry = AutocompleteEntry(root, font=("Arial", 12), width=20)
        self.city_entry.pack(pady=5)
        self.city_entry.bind("<Return>", lambda event: self.fetch_weather())
        self.city_entry.focus_set()

        self.submit_btn = tk.Button(
            root, text="Get Weather", command=self.fetch_weather,
            bg="#007bff", fg="white", font=("Arial", 12)
        )
        self.submit_btn.pack(pady=5)

        self.result_label = tk.Label(root, text="", bg="#f0f0f0", font=("Arial", 12), wraplength=550)
        self.result_label.pack(pady=10)

        self.forecast_frame = tk.Frame(root, bg="#f0f0f0")
        self.forecast_frame.pack(pady=10)
        self.forecast_labels = []

        self.map_label = tk.Label(root, bg="#f0f0f0")
        self.map_label.pack(pady=10)

    def fetch_weather(self):
        # ... (Your existing fetch_weather method remains unchanged)
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showerror("Error", "Please enter a city name")
            return

        try:
            response = requests.post("http://localhost:5000/api/weather", json={"city": city})
            data = response.json()

            if response.status_code != 200:
                messagebox.showerror("Error", data.get("error", "Unknown error"))
                return

            celsius = data['temp']
            fahrenheit = (celsius * 9/5) + 32
            description = re.sub(r'[^\w\s,.]', '', data['description']).capitalize()

            result = (
                f"{data['city']}\n"
                f"Temperature: {fahrenheit:.1f} F\n"
                f"Humidity: {data['humidity']}%\n"
                f"Description: {description}"
            )
            self.result_label.config(text=result)

            for label in self.forecast_labels:
                label.destroy()
            self.forecast_labels.clear()

            forecast_response = requests.post("http://localhost:5000/api/forecast", json={"city": city})
            if forecast_response.status_code == 200:
                forecast_data = forecast_response.json()
                for i, item in enumerate(forecast_data['forecast']):
                    min_temp_f = (item['min_temp'] * 9/5) + 32
                    max_temp_f = (item['max_temp'] * 9/5) + 32
                    desc = re.sub(r'[^\w\s,.]', '', item['description']).capitalize()
                    forecast_text = f"{item['day']}\n{item['date']}\n{min_temp_f:.1f}-{max_temp_f:.1f} F\n{desc}"
                    label = tk.Label(
                        self.forecast_frame,
                        text=forecast_text,
                        bg="#ffffff",
                        font=("Arial", 9),
                        width=15,
                        height=5,
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

            lat = data.get("lat")
            lon = data.get("lon")
            self.last_lat, self.last_lon = lat, lon

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