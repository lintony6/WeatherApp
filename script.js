document.addEventListener('DOMContentLoaded', () => {
  const BACKEND_URL = "https://n1zpcn6yw3.execute-api.us-east-1.amazonaws.com/dev";

  const cityInput = document.getElementById('city-input');
  const submitBtn = document.getElementById('submit-btn');
  const autocompleteList = document.getElementById('autocomplete-list');
  const errorMessageDiv = document.getElementById('error-message');
  const resultsContainer = document.getElementById('results-container');
  const currentWeatherDiv = document.getElementById('current-weather');
  const forecastContainer = document.getElementById('forecast-container');
  const weatherMapImg = document.getElementById('weather-map');
  const metricBtn = document.getElementById('metric-btn');
  const imperialBtn = document.getElementById('imperial-btn');

  let useFahrenheit = false;   // backend returns metric
  let currentWeatherData = null;
  let forecastData = null;
  let tempChart = null;
  let suggestionCache = {};
  let debounceTimer;
  let activeSuggestionIndex = -1;
  let currentSuggestions = [];
  let selectedPlace = null;    // {lat, lon, label}

  // Units toggle
  metricBtn.addEventListener('click', () => setUnits(false));
  imperialBtn.addEventListener('click', () => setUnits(true));
  function setUnits(toImperial) {
    useFahrenheit = toImperial;
    metricBtn.classList.toggle('active', !toImperial);
    imperialBtn.classList.toggle('active', toImperial);
    if (currentWeatherData && forecastData) {
      displayCurrentWeather(currentWeatherData);
      displayForecast(forecastData.forecast);
      renderChart(forecastData.forecast);
    }
  }

  // Autocomplete
  cityInput.addEventListener('input', () => {
    const query = cityInput.value.trim();
    selectedPlace = null; // typing invalidates previous selection
    clearTimeout(debounceTimer);
    closeSuggestions();
    if (query.length < 2) return;
    debounceTimer = setTimeout(() => fetchAutocomplete(query), 300);
  });

  async function fetchAutocomplete(query) {
    if (suggestionCache[query]) {
      updateAutocomplete(suggestionCache[query]);
      return;
    }
    try {
      const res = await fetch(`${BACKEND_URL}/api/autocomplete?q=${encodeURIComponent(query)}`);
      if (!res.ok) throw new Error(`Status: ${res.status}`);
      const data = await res.json();
      const suggestions = Array.isArray(data) ? data : (data.suggestions || []);
      suggestionCache[query] = suggestions;
      updateAutocomplete(suggestions);
    } catch (err) {
      console.error('Autocomplete error:', err);
      showError('Failed to load city suggestions: ' + err.message);
    }
  }

  function updateAutocomplete(suggestions) {
    closeSuggestions();
    currentSuggestions = suggestions;
    if (!suggestions.length) return;
    suggestions.forEach((s, idx) => {
      const label = s.display_name || String(s);
      const item = document.createElement('div');
      item.textContent = label;
      item.dataset.index = String(idx);
      item.addEventListener('click', () => {
        if (s.lat && s.lon) {
          selectedPlace = { lat: parseFloat(s.lat), lon: parseFloat(s.lon), label };
          cityInput.value = label;
          closeSuggestions();
          fetchWeather();
        } else {
          showError('This suggestion has no coordinates.');
        }
      });
      autocompleteList.appendChild(item);
    });
  }

  cityInput.addEventListener('keydown', (e) => {
    const items = autocompleteList.getElementsByTagName('div');
    if (e.key === 'ArrowDown' && items.length) {
      e.preventDefault(); activeSuggestionIndex = (activeSuggestionIndex + 1) % items.length; setActive(items); return;
    }
    if (e.key === 'ArrowUp' && items.length) {
      e.preventDefault(); activeSuggestionIndex = (activeSuggestionIndex - 1 + items.length) % items.length; setActive(items); return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      if (items.length) (items[activeSuggestionIndex > -1 ? activeSuggestionIndex : 0]).click();
      else showError('Please choose a location from the autocomplete list.');
      return;
    }
    if (e.key === 'Escape') { closeSuggestions(); return; }
  });

  function setActive(items) {
    for (const i of items) i.classList.remove('autocomplete-active');
    if (activeSuggestionIndex > -1) items[activeSuggestionIndex].classList.add('autocomplete-active');
  }
  function closeSuggestions() { autocompleteList.innerHTML = ''; activeSuggestionIndex = -1; currentSuggestions = []; }
  document.addEventListener('click', (e) => { if (!e.target.closest('.autocomplete-wrapper')) closeSuggestions(); });

  // Fetch Weather + Forecast
  submitBtn.addEventListener('click', fetchWeather);

  async function fetchWeather() {
    clearResults();
    if (!selectedPlace) {
      const q = cityInput.value.trim();
      if (!q) return showError('Please enter a city name.');
      return showError('Please choose a location from the autocomplete list so we can use exact coordinates.');
    }
    const payload = { lat: selectedPlace.lat, lon: selectedPlace.lon, label: selectedPlace.label };

    try {
      const [wRes, fRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/weather`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)}),
        fetch(`${BACKEND_URL}/api/forecast`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)})
      ]);

      let weatherData, forecastResponse;

      if (!wRes.ok) {
        const errData = await wRes.json().catch(() => ({}));
        throw new Error(errData.error || `Weather fetch failed (${wRes.status})`);
      }
      weatherData = await wRes.json();
      if (weatherData.error) throw new Error(weatherData.error);

      if (!fRes.ok) {
        const errData = await fRes.json().catch(() => ({}));
        throw new Error(errData.error || `Forecast fetch failed (${fRes.status})`);
      }
      forecastResponse = await fRes.json();
      if (forecastResponse.error) throw new Error(forecastResponse.error);

      currentWeatherData = weatherData;
      forecastData = forecastResponse;

      displayCurrentWeather(weatherData);
      displayForecast(forecastResponse.forecast);
      displayMap(weatherData.map_url);
      resultsContainer.classList.remove('hidden');
    } catch (err) {
      console.error('Weather fetch error:', err);
      showError('Failed to fetch weather: ' + (err.message || err));
    }
  }

  // Weather icon mapping from Visual Crossing to OpenWeatherMap icon codes
  function getWeatherIconUrl(vcIcon) {
    const iconMap = {
      'clear-day': '01d',
      'clear-night': '01n',
      'partly-cloudy-day': '02d',
      'partly-cloudy-night': '02n',
      'cloudy': '04d',
      'rain': '10d',
      'showers-day': '09d',
      'showers-night': '09n',
      'snow': '13d',
      'snow-showers-day': '13d',
      'snow-showers-night': '13n',
      'fog': '50d',
      'wind': '50d',  // Using mist for wind as placeholder
      'thunder-rain': '11d',
      'thunder-showers-day': '11d',
      'thunder-showers-night': '11n'
      // Add more mappings if needed
    };
    const owmCode = iconMap[vcIcon] || '50d';  // Default to mist
    return `https://openweathermap.org/img/wn/${owmCode}@2x.png`;
  }

  // Conversions
  function tempToDisplay(v) {
    if (v == null) return v;
    return useFahrenheit ? (v * 9/5 + 32) : v;
  }
  function windToDisplay(v) {
    if (v == null) return v;
    return useFahrenheit ? (v * 0.621371) : v;
  }
  function tempUnit(){ return useFahrenheit ? '°F' : '°C'; }
  function windUnit(){ return useFahrenheit ? 'mph' : 'km/h'; }

  // Display current
  function displayCurrentWeather(weatherData) {
    const desc = (weatherData.description || '').toLowerCase();
    const iconUrl = getWeatherIconUrl(weatherData.icon);

    const t = tempToDisplay(Number(weatherData.temp));
    const f = tempToDisplay(Number(weatherData.feels_like ?? weatherData.temp));
    const minT = tempToDisplay(Number(weatherData.daily_low ?? weatherData.temp));
    const maxT = tempToDisplay(Number(weatherData.daily_high ?? weatherData.temp));
    const w = windToDisplay(Number(weatherData.wind_speed ?? 0));

    currentWeatherDiv.innerHTML = `
      <h2>${weatherData.city}</h2>
      <img src="${iconUrl}" alt="${desc} icon" style="width: 50px; height: 50px;">
      <p><strong>${desc}</strong></p>
      <p><strong>Current Temp:</strong> ${t.toFixed(1)} ${tempUnit()}</p>
      <p class="temp-range"><strong>Daily Low:</strong> ${minT.toFixed(1)} ${tempUnit()}</p>
      <p class="temp-range"><strong>Daily High:</strong> ${maxT.toFixed(1)} ${tempUnit()}</p>
      <p><strong>Feels Like:</strong> ${f.toFixed(1)} ${tempUnit()}</p>
      <p><strong>Humidity:</strong> ${weatherData.humidity}%</p>
      <p><strong>Pressure:</strong> ${weatherData.pressure} hPa</p>
      <p><strong>Wind:</strong> ${w.toFixed(1)} ${windUnit()}</p>
    `;
    updateMapOverlay(desc, weatherData.icon);
  }

  // Display forecast
  function displayForecast(forecast) {
    forecastContainer.innerHTML = '';
    forecast.forEach((d) => {
      const iconUrl = getWeatherIconUrl(d.icon);
      const minDisp = tempToDisplay(Number(d.min_temp));
      const maxDisp = tempToDisplay(Number(d.max_temp));
      const card = document.createElement('div');
      card.className = 'card forecast-card';
      card.innerHTML = `
        <strong>${d.day}</strong><br>
        <img src="${iconUrl}" alt="${d.description} icon" style="width: 40px; height: 40px;">
        <p class="temp-range"><strong>Low:</strong> ${minDisp.toFixed(1)} ${tempUnit()}</p>
        <p class="temp-range"><strong>High:</strong> ${maxDisp.toFixed(1)} ${tempUnit()}</p>
        <p>${d.description}</p>
      `;
      forecastContainer.appendChild(card);
    });
    renderChart(forecast);
  }

  // Chart (Chart.js assumed loaded in your page)
  function renderChart(forecast) {
    const labels = forecast.map(f => f.day);
    const minTemps = forecast.map(f => tempToDisplay(Number(f.min_temp)));
    const maxTemps = forecast.map(f => tempToDisplay(Number(f.max_temp)));
    const ctx = document.getElementById('tempChart').getContext('2d');
    if (tempChart) tempChart.destroy();
    tempChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: `Min Temp (${tempUnit()})`, data: minTemps, borderColor: '#007bff', borderWidth: 2, tension: 0.3, fill: false },
          { label: `Max Temp (${tempUnit()})`, data: maxTemps, borderColor: '#ff5733', borderWidth: 2, tension: 0.3, fill: false }
        ]
      },
      options: {
        plugins: { legend: { display: true } },
        responsive: true,
        scales: { y: { title: { display: true, text: `Temperature (${tempUnit()})` } } }
      }
    });
  }

  // Map helpers
  function displayMap(url) {
    if (!url) { weatherMapImg.style.display = 'none'; return; }
    weatherMapImg.onload = () => { weatherMapImg.style.display = 'block'; };
    weatherMapImg.onerror = () => { weatherMapImg.style.display = 'none'; };
    weatherMapImg.src = url;
  }
  function updateMapOverlay(desc, icon) {
    const overlay = document.getElementById('map-overlay');
    overlay.innerHTML = ''; // Clear previous content
    overlay.style.display = 'block';
    overlay.style.filter = '';
    overlay.style.background = '';

    const d = desc.toLowerCase();
    const i = icon.toLowerCase();

    if (i.includes('clear-day') || d.includes('clear')) {
      // Sunny glow
      overlay.style.background = 'radial-gradient(circle, rgba(255, 255, 0, 0.3), transparent)';
      overlay.style.filter = 'brightness(1.2) drop-shadow(0 0 10px yellow)';
    } else if (d.includes('cloud') || d.includes('overcast') || i.includes('cloudy')) {
      // Add clouds on the map
      for (let j = 0; j < 5; j++) {
        const cloud = document.createElement('div');
        cloud.style.position = 'absolute';
        cloud.style.background = 'white';
        cloud.style.borderRadius = '50%';
        cloud.style.width = `${Math.random() * 50 + 50}px`;
        cloud.style.height = `${Math.random() * 20 + 20}px`;
        cloud.style.opacity = '0.5';
        cloud.style.left = `${Math.random() * 100}%`;
        cloud.style.top = `${Math.random() * 80}%`;
        cloud.style.transform = 'translate(-50%, -50%)';
        overlay.appendChild(cloud);
      }
      overlay.style.filter = 'grayscale(0.5) brightness(0.8)';
    } else if (d.includes('rain')) {
      overlay.style.background = 'linear-gradient(transparent, rgba(0, 0, 255, 0.2))';
      overlay.style.filter = 'hue-rotate(-120deg) saturate(1.2)';
    } else if (d.includes('snow')) {
      overlay.style.filter = 'brightness(0.7) hue-rotate(300deg)';
    } else if (d.includes('storm') || d.includes('thunder')) {
      overlay.style.filter = 'contrast(1.5) sepia(0.8)';
    } else {
      overlay.style.display = 'none';
    }
  }

  // Errors & cleanup
  function showError(msg) { errorMessageDiv.textContent = msg; resultsContainer.classList.add('hidden'); }
  function clearResults() {
    errorMessageDiv.textContent = '';
    resultsContainer.classList.add('hidden');
    currentWeatherDiv.innerHTML = '';
    forecastContainer.innerHTML = '';
    weatherMapImg.src = ''; weatherMapImg.style.display = 'none';
    const overlay = document.getElementById('map-overlay');
    if (overlay) {
      overlay.innerHTML = '';
      overlay.style.display = 'none';
    }
    if (tempChart) { tempChart.destroy(); tempChart = null; }
  }
});