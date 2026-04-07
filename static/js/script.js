"use strict";

const cityInput = document.getElementById("city-input");
const errorMsg = document.getElementById("error-message");
const landingContent = document.getElementById("landing-content");
const weatherContent = document.getElementById("weather-content");
const forecastContainer = document.getElementById("forecast-container");
const loadingIndicator = document.getElementById("loading-indicator");

// Stats mappings
const resultCity = document.getElementById("result-city");
const resultDatetime = document.getElementById("result-datetime");
const resultIconEmoji = document.getElementById("result-icon-emoji");
const resultTemp = document.getElementById("result-temp");
const resultDesc = document.getElementById("result-desc");

const resultWind = document.getElementById("result-wind");
const resultHumidity = document.getElementById("result-humidity");
const resultTime = document.getElementById("result-time");
const langToggle = document.getElementById("lang-toggle");
const suggestionsDropdown = document.getElementById("suggestions-dropdown");

let currentLang = localStorage.getItem("weather_lang") || "mr";
let searchTimeout;
let isFetching = false;

const TRANSLATIONS = {
    en: {
        nav_home: "Home", nav_dashboard: "Dashboard", nav_cities: "Cities", nav_about: "About",
        welcome_to: "Welcome to", app_title: "Maharashtra<br>Weather App", 
        app_desc: "Get real-time weather updates and 7-day forecasts for 30 major cities of Maharashtra.",
        search_title: "Search Weather", search_placeholder: "Enter city name...", search_btn: "Search",
        popular_cities: "Popular Cities", loading: "Loading...", today: "Today",
        wind: "Wind", humidity: "Humidity", local_time: "Local Time",
        forecast_title: "7-Day Forecast", empty_state: "Search for a city or click a popular city tag to see the weather dashboard.",
        footer_text: "Maharashtra Weather App | Built with ❤️ using Flask & Open-Meteo API",
        updated: "Updated", just_now: "Just now", min_ago: "min ago", hr_ago: "hr ago",
        network_err: "Network Error",
        cities: {
            "Mumbai": "Mumbai", "Pune": "Pune", "Nagpur": "Nagpur", "Nashik": "Nashik",
            "Chhatrapati Sambhaji Nagar": "Chhatrapati Sambhaji Nagar", "Shirdi": "Shirdi",
            "Solapur": "Solapur", "Amravati": "Amravati", "Kolhapur": "Kolhapur",
            "Sangli": "Sangli", "Jalgaon": "Jalgaon", "Akola": "Akola", "Latur": "Latur",
            "Dhule": "Dhule", "Ahmednagar": "Ahmednagar", "Chandrapur": "Chandrapur",
            "Parbhani": "Parbhani", "Nanded": "Nanded", "Beed": "Beed", "Ratnagiri": "Ratnagiri",
            "Satara": "Satara", "Wardha": "Wardha", "Yavatmal": "Yavatmal", "Gondia": "Gondia",
            "Bhandara": "Bhandara", "Hingoli": "Hingoli", "Osmanabad": "Osmanabad",
            "Palghar": "Palghar", "Thane": "Thane", "Panvel": "Panvel"
        }
    },
    mr: {
        nav_home: "मुख्यपृष्ठ", nav_dashboard: "डॅशबोर्ड", nav_cities: "शहरे", nav_about: "माहिती",
        welcome_to: "स्वागत आहे", app_title: "महाराष्ट्र<br>हवामान ॲप",
        app_desc: "महाराष्ट्रातील ३० प्रमुख शहरांचे रिअल-टाइम हवामान अपडेट्स आणि ७ दिवसांचा अंदाज मिळवा.",
        search_title: "हवामान शोधा", search_placeholder: "शहराचे नाव प्रविष्ट करा...", search_btn: "शोधा",
        popular_cities: "लोकप्रिय शहरे", loading: "लोड होत आहे...", today: "आज",
        wind: "वारा", humidity: "आर्द्रता", local_time: "स्थानिक वेळ",
        forecast_title: "७ दिवसांचा अंदाज", empty_state: "हवामानाचा डॅशबोर्ड पाहण्यासाठी शहर शोधा किंवा लोकप्रिय शहराच्या टॅगवर क्लिक करा.",
        footer_text: "महाराष्ट्र हवामान ॲप | Flask आणि Open-Meteo API वापरून ❤️ सह तयार केले",
        updated: "अपडेट", just_now: "आत्ताच", min_ago: "मिनीटांपूर्वी", hr_ago: "तासांपूर्वी",
        network_err: "नेटवर्क त्रुटी",
        cities: {
            "Mumbai": "मुंबई", "Pune": "पुणे", "Nagpur": "नागपूर", "Nashik": "नाशिक",
            "Chhatrapati Sambhaji Nagar": "छत्रपती संभाजी नगर", "Shirdi": "शिर्डी",
            "Solapur": "सोलापूर", "Amravati": "अमरावती", "Kolhapur": "कोल्हापूर",
            "Sangli": "सांगली", "Jalgaon": "जळगाव", "Akola": "अकोला", "Latur": "लातूर",
            "Dhule": "धुळे", "Ahmednagar": "अहमदनगर", "Chandrapur": "चंद्रपूर",
            "Parbhani": "परभणी", "Nanded": "नांदेड", "Beed": "बीड", "Ratnagiri": "रत्नागिरी",
            "Satara": "सातारा", "Wardha": "वर्धा", "Yavatmal": "यवतमाळ", "Gondia": "गोंदिया",
            "Bhandara": "भंडारा", "Hingoli": "हिंगोली", "Osmanabad": "उस्मानाबाद",
            "Palghar": "पालघर", "Thane": "ठाणे", "Panvel": "पनवेल"
        }
    }
};

const WEATHER_CODE_MAP = {
    0: { en: "Clear sky", mr: "स्वच्छ आकाश", emoji: "☀️" },
    1: { en: "Cloudy", mr: "ढगाळ वातावरण", emoji: "☁️" },
    2: { en: "Cloudy", mr: "ढगाळ वातावरण", emoji: "☁️" },
    3: { en: "Cloudy", mr: "ढगाळ वातावरण", emoji: "☁️" },
    45: { en: "Fog", mr: "धुके", emoji: "🌫️" },
    48: { en: "Fog", mr: "धुके", emoji: "🌫️" },
    51: { en: "Drizzle", mr: "हलका पाऊस", emoji: "🌧️" },
    53: { en: "Drizzle", mr: "हलका पाऊस", emoji: "🌧️" },
    55: { en: "Drizzle", mr: "हलका पाऊस", emoji: "🌧️" },
    61: { en: "Rain", mr: "पाऊस", emoji: "🌧️" },
    63: { en: "Rain", mr: "पाऊस", emoji: "🌧️" },
    65: { en: "Rain", mr: "पाऊस", emoji: "🌧️" },
    71: { en: "Snow", mr: "बर्फ", emoji: "❄️" },
    80: { en: "Rain Showers", mr: "मध्यम पाऊस", emoji: "🌦️" },
    95: { en: "Thunderstorm", mr: "गडगडाटासह पाऊस", emoji: "⚡" }
};

function getWeatherText(code, lang) {
    return (WEATHER_CODE_MAP[code] || { en: "Unknown", mr: "अज्ञात" })[lang];
}

function applyTranslations() {
    const t = TRANSLATIONS[currentLang];
    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        if (t[key]) el.innerHTML = t[key];
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
        const key = el.getAttribute("data-i18n-placeholder");
        if (t[key]) el.placeholder = t[key];
    });
    if (langToggle) {
        langToggle.textContent = currentLang === "mr" ? "मराठी / EN" : "EN / मराठी";
    }
}

function timeAgo(dateStr) {
    const t = TRANSLATIONS[currentLang];
    if (!dateStr) return t.just_now;
    const date = new Date(dateStr.replace(" ", "T"));
    const diff = Math.floor((new Date() - date) / 60000);
    if (diff <= 0) return t.just_now;
    if (diff < 60) return `${diff} ${t.min_ago}`;
    const hours = Math.floor(diff / 60);
    return `${hours} ${t.hr_ago}`;
}

function showError(msg) {
    if(!errorMsg) return;
    errorMsg.textContent = msg;
    errorMsg.classList.remove("hidden");
    setTimeout(() => errorMsg.classList.add("hidden"), 5000);
}

function renderWeather(data) {
    // Hide empty state, show content
    landingContent.classList.add("hidden");
    weatherContent.classList.remove("hidden");

    // Cache the raw data globally for re-rendering on language switch
    window.lastWeatherData = data;

    const t = TRANSLATIONS[currentLang];
    resultCity.textContent = t.cities[data.city] || data.city;
    resultDatetime.innerHTML = `${data.timestamp}`;
    resultIconEmoji.textContent = data.icon;
    resultTemp.textContent = Math.round(data.temp);
    
    // Dynamic Description based on language
    resultDesc.textContent = getWeatherText(data.weathercode, currentLang);

    if(resultWind) resultWind.textContent = `${data.wind_speed} km/h`;
    if(resultHumidity) resultHumidity.textContent = `70%`;
    
    const tSplit = data.timestamp.split(", ");
    if (resultTime) {
        resultTime.textContent = tSplit.length > 1 ? tSplit[1] : data.timestamp;
    }

    const dayMap = {
        mr: { 'Mon': 'सोम', 'Tue': 'मंगळ', 'Wed': 'बुध', 'Thu': 'गुरु', 'Fri': 'शुक्र', 'Sat': 'शनी', 'Sun': 'रवी' },
        en: { 'Mon': 'Mon', 'Tue': 'Tue', 'Wed': 'Wed', 'Thu': 'Thu', 'Fri': 'Fri', 'Sat': 'Sat', 'Sun': 'Sun' }
    };

    if (forecastContainer && data.forecast && data.forecast.length > 0) {
        forecastContainer.innerHTML = data.forecast.slice(0, 7).map((day, index) => {
            // If it's the first day, show "Today" / "आज"
            let dayName = dayMap[currentLang][day.day] || day.day;
            if (index === 0) dayName = t.today;

            return `
                <div class="f-col">
                    <span class="f-day">${dayName}</span>
                    <span class="f-emoji">${day.emoji}</span>
                    <span class="f-max">${day.max}°</span>
                    <span class="f-min">${day.min}°</span>
                </div>
            `;
        }).join("");
    }
}

// Load cities and init logic on startup
document.addEventListener("DOMContentLoaded", () => {
    applyTranslations();

    // Language Toggle logic
    if (langToggle) {
        langToggle.addEventListener("click", () => {
            currentLang = currentLang === "mr" ? "en" : "mr";
            localStorage.setItem("weather_lang", currentLang);
            applyTranslations();
            if (window.lastWeatherData) {
                renderWeather(window.lastWeatherData);
            }
        });
    }

    // Suggestions Logic
    if (cityInput) {
        cityInput.addEventListener("input", (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();
            
            if (query.length < 1) {
                suggestionsDropdown.classList.add("hidden");
                return;
            }

            searchTimeout = setTimeout(async () => {
                try {
                    const response = await fetch(`/api/suggestions?q=${encodeURIComponent(query)}`);
                    const suggestions = await response.json();
                    
                    if (suggestions.length > 0) {
                        renderSuggestions(suggestions);
                    } else {
                        suggestionsDropdown.classList.add("hidden");
                    }
                } catch (err) {
                    console.error("Suggestions error:", err);
                }
            }, 200);
        });
    }
});

function renderSuggestions(list) {
    const t = TRANSLATIONS[currentLang];
    suggestionsDropdown.innerHTML = list.map(name => {
        const displayName = t.cities[name] || name;
        return `<div class="suggestion-item" onclick="selectSuggestion('${name}')">${displayName}</div>`;
    }).join("");
    suggestionsDropdown.classList.remove("hidden");
}

function selectSuggestion(name) {
    const t = TRANSLATIONS[currentLang];
    cityInput.value = t.cities[name] || name;
    suggestionsDropdown.classList.add("hidden");
    searchWeather(name);
}

// Hide suggestions when clicking outside
document.addEventListener("click", (e) => {
    if (suggestionsDropdown && !suggestionsDropdown.contains(e.target) && e.target !== cityInput) {
        suggestionsDropdown.classList.add("hidden");
    }
});


// Full Auto-Refresh Loop (Every 10 min)
setInterval(() => {
    console.log("🔄 10-minute auto-refresh triggered...");
    
    // If we're looking at a specific city, refresh its full card + forecast too
    const currentCity = resultCity.textContent;
    if (currentCity && currentCity !== "--") {
        searchWeather(currentCity);
    }
}, 600000);

async function searchWeather(cityName) {
    if (isFetching) return;
    const city = (cityName || cityInput.value).trim();
    if (!city) return;

    isFetching = true;
    if(loadingIndicator) loadingIndicator.classList.remove("hidden");

    try {
        // Because fetch_weather on backend inherently adds unknown cities to the DB,
        // calling /weather works exactly the same as adding a new city!
        const response = await fetch("/weather", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ city }),
        });

        const result = await response.json();

        if (result.success) {
            renderWeather(result.data);
            if(cityInput) cityInput.value = "";
        } else {
            showError(result.error);
        }
    } catch (err) {
        console.error(err);
        showError(TRANSLATIONS[currentLang].network_err);
    } finally {
        isFetching = false;
        if(loadingIndicator) loadingIndicator.classList.add("hidden");
    }
}

if (cityInput) {
    cityInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            searchWeather();
            // Reload pills just in case it was a NEW city that got added to the DB!
            setTimeout(loadPopularCities, 1000);
        }
    });
}
// Handle the Add/Search button click
document.querySelector(".search-btn").addEventListener("click", () => {
    searchWeather();
    setTimeout(loadPopularCities, 1000);
});

window.searchFromHistory = function(city) {
    searchWeather(city);
};
