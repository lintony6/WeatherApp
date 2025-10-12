document.addEventListener('DOMContentLoaded', () => {
    // ✅ Updated to the new live backend URL
    const BACKEND_URL = "https://n1zpcn6yw3.execute-api.us-east-1.amazonaws.com/dev";

    // --- Select HTML elements ---
    const cityInput = document.getElementById('city-input');
    const submitBtn = document.getElementById('submit-btn');
    const autocompleteList = document.getElementById('autocomplete-list');
    const errorMessageDiv = document.getElementById('error-message');
    const resultsContainer = document.getElementById('results-container');
    const currentWeatherDiv = document.getElementById('current-weather');
    const forecastContainer = document.getElementById('forecast-container');
    const weatherMapImg = document.getElementById('weather-map');
    const unitToggle = document.getElementById('unit-toggle');
    const unitLabel = document.getElementById('unit-label');

    // --- State ---
    let debounceTimer;
    let suggestionCache = {};
    let activeSuggestionIndex = -1;
    let useFahrenheit = false;
    let currentWeatherData = null;
    let forecastData = null;

    // --- Event Listeners ---
    submitBtn.addEventListener('click', fetchWeather);
    cityInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            if (autocompleteList.childElementCount > 0 && activeSuggestionIndex > -1) return;
            fetchWeather();
        }
    });

    unitToggle.addEventListener('change', () => {
        useFahrenheit = unitToggle.checked;
        unitLabel.textContent = useFahrenheit ? "°F" : "°C";
        if (currentWeatherData) displayCurrentWeather(currentWeatherData);
        if (forecastData) displayForecast(forecastData.forecast);
    });

    // --- Autocomplete ---
    cityInput.addEventListener('input', () => {
        const query = cityInput.value.trim();
        clearTimeout(debounceTimer);
        closeAllLists();
        if (query.length < 2) return;
        debounceTimer = setTimeout(() => fetchAutocomplete(query), 300);
    });

    async function fetchAutocomplete(query) {
        if (suggestionCache[query]) {
            updateAutocomplete(suggestionCache[query]);
            return;
        }
        const url = `${BACKEND_URL}/api/autocomplete?q=${encodeURIComponent(query)}`;
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            const suggestions = data.map(item => item.display_name);
            suggestionCache[query] = suggestions;
            updateAutocomplete(suggestions);
        } catch (error) {
            console.error('Autocomplete fetch error:', error);
        }
    }

    function updateAutocomplete(suggestions) {
        closeAllLists();
        activeSuggestionIndex = -1;
        if (!suggestions.length) return;
        suggestions.forEach(suggestion => {
            const item = document.createElement('div');
            item.textContent = suggestion;
            item.addEventListener('click', () => {
                cityInput.value = suggestion;
                closeAllLists();
                fetchWeather();
            });
            autocompleteList.appendChild(item);
        });
    }

    cityInput.addEventListener('keydown', (e) => {
        const items = autocompleteList.getElementsByTagName('div');
        if (items.length === 0) return;
        if (e.key === 'ArrowDown') {
            activeSuggestionIndex = (activeSuggestionIndex + 1) % items.length;
            addActive(items);
        } else if (e.key === 'ArrowUp') {
            activeSuggestionIndex = (activeSuggestionIndex - 1 + items.length) % items.length;
            addActive(items);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (activeSuggestionIndex > -1) {
                items[activeSuggestionIndex].click();
            }
        } else if (e.key === 'Escape') {
            closeAllLists();
        }
    });

    function addActive(items) {
        if (!items) return;
        removeActive(items);
        if (activeSuggestionIndex > -1) {
            items[activeSuggestionIndex].classList.add('autocomplete-active');
        }
    }

    function removeActive(items) {
        for (const item of items) item.classList.remove('autocomplete-active');
    }

    function closeAllLists() {
        autocompleteList.innerHTML = '';
    }

    document.addEventListener('click', (e) => {
        if (e.target !== cityInput) closeAllLists();
    });

    // --- Weather Fetching ---
    async function fetchWeather() {
        const city = cityInput.value.trim();
        if (!city) {
            showError("Please enter a city name");
            return;
        }
        closeAllLists();
        clearResults();

        try {
            const weatherResponse = await fetch(`${BACKEND_URL}/api/weather`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ city }),
            });

            const weatherData = await weatherResponse.json();
            if (!weatherResponse.ok) throw new Error(weatherData.error || 'Unknown weather error');
            currentWeatherData = weatherData;
            displayCurrentWeather(weatherData);

            const forecastResponse = await fetch(`${BACKEND_URL}/api/forecast`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ city }),
            });

            if (forecastResponse.ok) {
                forecastData = await forecastResponse.json();
                displayForecast(forecastData.forecast);
            } else {
                throw new Error('Forecast unavailable');
            }

            displayMap(weatherData.map_url);
            resultsContainer.classList.remove('hidden');
        } catch (error) {
            showError(`Failed to fetch weather: ${error.message}`);
        }
    }

    // --- Display Current Weather ---
    function displayCurrentWeather(data) {
        if (!data) return;
        const tempC = data.temp;
        const feelsLikeC = data.feels_like ?? data.temp;
        const humidity = data.humidity;
        const pressure = data.pressure;
        const windSpeedMs = data.wind_speed;
        const description = data.description.replace(/[^\w\s,.]/g, '').replace(/^\w/, c => c.toUpperCase());
        const sunrise = data.sunrise ? new Date(data.sunrise * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';
        const sunset = data.sunset ? new Date(data.sunset * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';

        const temp = useFahrenheit ? (tempC * 9/5) + 32 : tempC;
        const feelsLike = useFahrenheit ? (feelsLikeC * 9/5) + 32 : feelsLikeC;
        const windSpeed = useFahrenheit ? (windSpeedMs * 2.237).toFixed(1) : windSpeedMs.toFixed(1);

        const tempUnit = useFahrenheit ? '°F' : '°C';
        const windUnit = useFahrenheit ? 'mph' : 'm/s';

        currentWeatherDiv.innerHTML = `
            <h2>${data.city}</h2>
            <p><strong>${description}</strong></p>
            <p><strong>Temperature:</strong> ${temp.toFixed(1)} ${tempUnit}</p>
            <p><strong>Feels Like:</strong> ${feelsLike.toFixed(1)} ${tempUnit}</p>
            <p><strong>Humidity:</strong> ${humidity}%</p>
            <p><strong>Pressure:</strong> ${pressure} hPa</p>
            <p><strong>Wind:</strong> ${windSpeed} ${windUnit}</p>
            <p><strong>Sunrise:</strong> ${sunrise}</p>
            <p><strong>Sunset:</strong> ${sunset}</p>
        `;
    }

    // --- Display Forecast ---
    function displayForecast(forecast) {
        if (!forecast) return;
        forecastContainer.innerHTML = '';
        forecast.forEach(item => {
            const minC = item.min_temp;
            const maxC = item.max_temp;
            const desc = item.description.replace(/[^\w\s,.]/g, '').replace(/^\w/, c => c.toUpperCase());

            const minTemp = useFahrenheit ? (minC * 9/5) + 32 : minC;
            const maxTemp = useFahrenheit ? (maxC * 9/5) + 32 : maxC;
            const unit = useFahrenheit ? '°F' : '°C';

            const card = document.createElement('div');
            card.className = 'card forecast-card';
            card.innerHTML = `
                <strong>${item.day}</strong><br>
                <small>${item.date}</small><br>
                ${minTemp.toFixed(1)}–${maxTemp.toFixed(1)} ${unit}<br>
                ${desc}
            `;
            forecastContainer.appendChild(card);
        });
    }

    function displayMap(mapUrl) {
        if (mapUrl) {
            weatherMapImg.src = mapUrl;
            weatherMapImg.style.display = 'block';
        } else {
            weatherMapImg.style.display = 'none';
        }
    }

    // --- Helpers ---
    function showError(message) {
        errorMessageDiv.textContent = message;
        resultsContainer.classList.add('hidden');
    }

    function clearResults() {
        errorMessageDiv.textContent = '';
        resultsContainer.classList.add('hidden');
        currentWeatherDiv.innerHTML = '';
        forecastContainer.innerHTML = '';
        weatherMapImg.src = '';
    }
});
