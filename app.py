from pathlib import Path

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "sample_locations.csv"


st.set_page_config(
    page_title="PahadiSathi",
    page_icon="🏔️",
    layout="wide",
)


@st.cache_data(ttl=1800)
def get_weather(latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "weather_code,"
            "wind_speed_10m"
        ),
        "daily": (
            "precipitation_sum,"
            "precipitation_probability_max"
        ),
        "forecast_days": 7,
        "timezone": "Asia/Kolkata",
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=20,
        )

        if response.status_code == 429:
            return {
                "error": (
                    "Weather API rate limit reached. "
                    "Please try again after a few minutes."
                )
            }

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as error:
        return {
            "error": f"Weather API request failed: {error}"
        }
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "weather_code,"
            "wind_speed_10m"
        ),
        "daily": (
            "precipitation_sum,"
            "precipitation_probability_max"
        ),
        "forecast_days": 7,
        "timezone": "Asia/Kolkata",
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=20,
        )

        response.raise_for_status()
        return response.json()

    except Exception as error:
        return {
            "error": repr(error),
        }


def weather_name(code):
    names = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Heavy drizzle",
        56: "Freezing drizzle",
        57: "Heavy freezing drizzle",
        61: "Light rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Freezing rain",
        67: "Heavy freezing rain",
        71: "Light snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Rain showers",
        81: "Heavy rain showers",
        82: "Violent rain showers",
        85: "Snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }

    try:
        return names.get(int(code), "Unknown")
    except (TypeError, ValueError):
        return "Unknown"


def calculate_risk(
    rainfall_24h,
    rainfall_7d,
    slope,
    soil_moisture,
    previous_landslide,
):
    score = 0
    reasons = []

    if rainfall_24h >= 50:
        score += 2
        reasons.append("High rainfall in the next 24 hours")
    elif rainfall_24h >= 25:
        score += 1
        reasons.append("Moderate rainfall in the next 24 hours")

    if rainfall_7d >= 150:
        score += 2
        reasons.append("High rainfall over seven days")
    elif rainfall_7d >= 75:
        score += 1
        reasons.append("Moderate rainfall over seven days")

    if slope >= 35:
        score += 2
        reasons.append("Steep slope")
    elif slope >= 20:
        score += 1
        reasons.append("Moderate slope")

    if soil_moisture >= 75:
        score += 2
        reasons.append("High soil moisture")
    elif soil_moisture >= 50:
        score += 1
        reasons.append("Moderate soil moisture")

    if int(previous_landslide) == 1:
        score += 2
        reasons.append("Previous nearby landslide")

    if score >= 8:
        level = "Critical"
    elif score >= 5:
        level = "High"
    elif score >= 3:
        level = "Moderate"
    else:
        level = "Lower"

    return score, level, reasons


st.title("PahadiSathi")

st.subheader(
    "Live weather and landslide-risk dashboard for Uttarakhand"
)

st.warning(
    "Prototype only. This is not an official emergency-warning system."
)


if not DATA_PATH.exists():
    st.error(f"Missing file: {DATA_PATH}")
    st.stop()


try:
    locations = pd.read_csv(DATA_PATH)

except Exception as error:
    st.error(f"CSV read error: {error}")
    st.stop()


required_columns = [
    "location",
    "district",
    "latitude",
    "longitude",
    "rainfall_24h",
    "rainfall_7d",
    "slope",
    "elevation",
    "soil_moisture",
    "road_distance",
    "previous_landslide",
    "risk",
]


missing_columns = [
    column
    for column in required_columns
    if column not in locations.columns
]


if missing_columns:
    st.error("CSV mein required columns missing hain:")
    st.write(missing_columns)
    st.stop()


left, right = st.columns([1, 2])


with left:
    st.header("Risk assessment")

    selected_location = st.selectbox(
        "Select location",
        locations["location"].tolist(),
    )

    selected = locations[
        locations["location"] == selected_location
    ].iloc[0]

    latitude = float(selected["latitude"])
    longitude = float(selected["longitude"])

    st.subheader("Live weather")

    if st.button("Refresh weather"):
        get_weather.clear()
        st.rerun()

    with st.spinner("Loading live weather..."):
        weather = get_weather(
            latitude,
            longitude,
        )

    if "error" in weather:
        st.error("Live weather unavailable.")
        st.code(weather["error"])

        current = {}
        daily = {}

        st.info(
            "The exact API error is shown above."
        )

    else:
        st.success("Live weather loaded.")

        current = weather.get("current", {})
        daily = weather.get("daily", {})

    temperature = current.get("temperature_2m", 0)
    humidity = current.get("relative_humidity_2m", 0)

    # Correct Open-Meteo current rain field
    rain_now = current.get("precipitation", 0)

    wind = current.get("wind_speed_10m", 0)
    code = current.get("weather_code", 0)

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Temperature",
            f"{temperature} °C",
        )

    with col2:
        st.metric(
            "Humidity",
            f"{humidity}%",
        )

    col3, col4 = st.columns(2)

    with col3:
        st.metric(
            "Rain now",
            f"{rain_now} mm",
        )

    with col4:
        st.metric(
            "Wind",
            f"{wind} km/h",
        )

    st.write(
        f"Condition: **{weather_name(code)}**"
    )

    dates = daily.get("time", [])
    rain_values = daily.get(
        "precipitation_sum",
        [],
    )

    rain_probability = daily.get(
        "precipitation_probability_max",
        [],
    )

    forecast = pd.DataFrame(
        {
            "Date": dates,
            "Rainfall (mm)": rain_values,
            "Rain probability (%)": rain_probability,
        }
    )

    if not forecast.empty:
        st.subheader("Seven-day forecast")

        st.dataframe(
            forecast,
            use_container_width=True,
            hide_index=True,
        )

        chart = forecast[
            ["Date", "Rainfall (mm)"]
        ].copy()

        chart["Date"] = pd.to_datetime(
            chart["Date"]
        )

        chart = chart.set_index("Date")

        st.subheader("Rainfall line graph")

        st.line_chart(
            chart,
            y="Rainfall (mm)",
            height=300,
        )

        st.subheader("Rainfall bar graph")

        st.bar_chart(
            chart,
            y="Rainfall (mm)",
            height=300,
        )

        rainfall_24h = float(
            rain_values[0]
        )

        rainfall_7d = sum(
            float(value)
            for value in rain_values[:7]
        )

    else:
        rainfall_24h = float(
            selected["rainfall_24h"]
        )

        rainfall_7d = float(
            selected["rainfall_7d"]
        )

        st.info(
            "Forecast unavailable. "
            "CSV data use ho raha hai."
        )

    st.divider()

    st.subheader("Risk inputs")

    slope = st.slider(
        "Slope (degrees)",
        0.0,
        70.0,
        float(selected["slope"]),
    )

    elevation = st.number_input(
        "Elevation (metres)",
        min_value=0.0,
        value=float(selected["elevation"]),
    )

    soil_moisture = st.slider(
        "Soil moisture (%)",
        0.0,
        100.0,
        float(selected["soil_moisture"]),
    )

    road_distance = st.number_input(
        "Distance from road (km)",
        min_value=0.0,
        value=float(selected["road_distance"]),
    )

    previous_landslide = st.selectbox(
        "Previous landslide nearby?",
        [0, 1],
        format_func=lambda value: (
            "Yes" if value == 1 else "No"
        ),
        index=int(selected["previous_landslide"]),
    )

    if st.button(
        "Calculate risk",
        type="primary",
    ):
        score, level, reasons = calculate_risk(
            rainfall_24h,
            rainfall_7d,
            slope,
            soil_moisture,
            previous_landslide,
        )

        st.metric(
            "Risk score",
            f"{score}/10",
        )

        if level == "Critical":
            st.error("Critical risk")

        elif level == "High":
            st.error("High risk")

        elif level == "Moderate":
            st.warning("Moderate risk")

        else:
            st.success("Lower risk")

        st.write(
            f"Risk level: **{level}**"
        )

        if reasons:
            st.write("### Contributing factors")

            for reason in reasons:
                st.write(f"- {reason}")

        else:
            st.write(
                "No major risk factors detected."
            )


with right:
    st.header("Uttarakhand risk map")

    map_view = folium.Map(
        location=[30.35, 79.10],
        zoom_start=8,
        tiles="OpenStreetMap",
    )

    folium.Marker(
        location=[
            latitude,
            longitude,
        ],
        tooltip=selected_location,
        popup=selected_location,
        icon=folium.Icon(
            color="blue",
            icon="cloud",
            prefix="fa",
        ),
    ).add_to(map_view)

    for _, item in locations.iterrows():
        if int(item["risk"]) == 1:
            color = "red"
            risk_text = "High"
        else:
            color = "green"
            risk_text = "Lower"

        folium.CircleMarker(
            location=[
                float(item["latitude"]),
                float(item["longitude"]),
            ],
            radius=9,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            popup=(
                f"{item['location']}<br>"
                f"District: {item['district']}<br>"
                f"Risk: {risk_text}"
            ),
        ).add_to(map_view)

    st_folium(
        map_view,
        width=900,
        height=600,
        key="risk_map",
    )


st.caption(
    "PahadiSathi is a prototype. "
    "Follow official warnings during emergencies."
)