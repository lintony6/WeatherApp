document.addEventListener('DOMContentLoaded', () => {
    // Select all the necessary HTML elements from the page
    const cityInput = document.getElementById('city-input');
    const submitBtn = document.getElementById('submit-btn');
    const autocompleteList = document.getElementById('autocomplete-list');
    const errorMessageDiv = document.getElementById('error-message');
    const resultsContainer = document.getElementById('results-container');
    const currentWeatherDiv = document.getElementById('current-weather');
    const forecastContainer = document.getElementById('forecast-container');
    const weatherMapImg = document.getElementById('weather-map');

    // Variables for managing autocomplete state
    let debounceTimer;
    let suggestionCache = {};
    let activeSuggestionIndex = -1;

    // --- Event Listeners ---
    submitBtn.addEventListener('click', fetchWeather);
    cityInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            if (autocompleteList.childElementCount > 0 && activeSuggestionIndex > -1) {
                return;
            }
            fetchWeather();
        }
    });

    // --- Autocomplete Logic ---
    cityInput.addEventListener('input', () => {
        const query = cityInput.value.trim();
        clearTimeout(debounceTimer);
        closeAllLists();
        if (query.length < 2) return;
        debounceTimer = setTimeout(() => {
            fetchAutocomplete(query);
        }, 300);
    });

    async function fetchAutocomplete(query) {
        if (suggestionCache[query]) {
            updateAutocomplete(suggestionCache[query]);
            return;
        }
        const url = `/api/autocomplete?q=${query}`;
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
        suggestions.forEach((suggestion) => {
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
        let items = autocompleteList.getElementsByTagName('div');
        if (items.length === 0) return;
        if (e.key === 'ArrowDown') {
            activeSuggestionIndex++;
            if (activeSuggestionIndex >= items.length) activeSuggestionIndex = 0;
            addActive(items);
        } else if (e.key === 'ArrowUp') {
            activeSuggestionIndex--;
            if (activeSuggestionIndex < 0) activeSuggestionIndex = items.length - 1;
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
        for (let i = 0; i < items.length; i++) {
            items[i].classList.remove('autocomplete-active');
        }
    }

    function closeAllLists() {
        autocompleteList.innerHTML = '';
    }
    
    document.addEventListener('click', (e) => {
        if (e.target !== cityInput) {
            closeAllLists();
        }
    });

    // --- Weather Fetching and Display Logic ---
    async function fetchWeather() {
        const city = cityInput.value.trim();
        if (!city) {
            showError("Please enter a city name");
            return;
        }
        closeAllLists();
        clearResults();

        try {
            const weatherResponse = await fetch('/api/weather', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ city }),
            });
            const weatherData = await weatherResponse.json();
            if (!weatherResponse.ok) throw new Error(weatherData.error || 'Unknown weather error');
            displayCurrentWeather(weatherData);

            // --- THIS LINE IS NOW FIXED ---
            const forecastResponse = await fetch('/api/forecast', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ city }),
            });
            if (forecastResponse.ok) {
                const forecastData = await forecastResponse.json();
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

    function displayCurrentWeather(data) {
        const fahrenheit = (data.temp * 9/5) + 32;
        const description = data.description.replace(/[^\w\s,.]/g, '').replace(/^\w/, c => c.toUpperCase());
        currentWeatherDiv.innerHTML = `
            <h2>${data.city}</h2>
            <p><strong>Temperature:</strong> ${fahrenheit.toFixed(1)} °F</p>
            <p><strong>Humidity:</strong> ${data.humidity}%</p>
            <p><strong>Description:</strong> ${description}</p>
        `;
    }

    function displayForecast(forecast) {
        forecastContainer.innerHTML = '';
        forecast.forEach(item => {
            const minTempF = (item.min_temp * 9/5) + 32;
            const maxTempF = (item.max_temp * 9/5) + 32;
            const desc = item.description.replace(/[^\w\s,.]/g, '').replace(/^\w/, c => c.toUpperCase());
            const card = document.createElement('div');
            card.className = 'card forecast-card';
            card.innerHTML = `
                <strong>${item.day}</strong><br>
                <small>${item.date}</small><br>
                ${minTempF.toFixed(1)}–${maxTempF.toFixed(1)} °F<br>
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