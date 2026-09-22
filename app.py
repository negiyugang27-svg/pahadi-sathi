from pathlib import Path
from datetime import datetime
import uuid

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "sample_locations.csv"
REPORTS_PATH = BASE_DIR / "data" / "reports.csv"
ROAD_BLOCKAGES_PATH = BASE_DIR / "data" / "road_blockages.csv"


st.set_page_config(
    page_title="PahadiSathi",
    page_icon="🏔️",
    layout="wide",
)


@st.cache_data(ttl=300)
def get_weather(latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "weather_code,"
            "wind_speed_10m"
        ),
        "hourly": "precipitation",
        "daily": "precipitation_sum",
        "timezone": "Asia/Kolkata",
        "forecast_days": 5,
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def load_locations():
    if not DATA_PATH.exists():
        return pd.DataFrame(
            columns=[
                "place_name",
                "district",
                "latitude",
                "longitude",
                "elevation",
                "slope",
                "soil_type",
                "landslide_history",
            ]
        )
    df = pd.read_csv(DATA_PATH)
    # Normalize column names to lowercase
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def load_reports():
    if not REPORTS_PATH.exists():
        return pd.DataFrame(
            columns=[
                "id",
                "report_type",
                "place_name",
                "latitude",
                "longitude",
                "severity",
                "status",
                "description",
                "reporter_name",
                "reporter_contact",
                "reported_at",
            ]
        )
    df = pd.read_csv(REPORTS_PATH)
    if not df.empty:
        df.columns = [c.strip().lower() for c in df.columns]
    return df


def save_report(report_dict):
    df = load_reports()
    new_row = pd.DataFrame([report_dict])
    df = pd.concat([df, new_row], ignore_index=True)
    # Ensure consistent column order
    expected_cols = [
        "id",
        "report_type",
        "place_name",
        "latitude",
        "longitude",
        "severity",
        "status",
        "description",
        "reporter_name",
        "reporter_contact",
        "reported_at",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None
    df = df[expected_cols]
    df.to_csv(REPORTS_PATH, index=False)


def load_road_blockages():
    if not ROAD_BLOCKAGES_PATH.exists():
        return pd.DataFrame(
            columns=[
                "road_name",
                "district",
                "latitude",
                "longitude",
                "blockage_type",
                "status",
                "severity",
                "verified",
                "reported_at",
                "reporter",
                "description",
            ]
        )
    df = pd.read_csv(ROAD_BLOCKAGES_PATH)
    if not df.empty:
        df.columns = [c.strip().lower() for c in df.columns]
    return df


st.title("🏔️ PahadiSathi – Landslide Risk & Incident Reporter")

st.write(
    "AI-assisted landslide risk dashboard and incident reporting for Uttarakhand. "
    "This is a student prototype for decision support, not an official warning system."
)


locations_df = load_locations()
reports_df = load_reports()
blockages_df = load_road_blockages()


# -------------------------
# Live weather section
# -------------------------
st.header("🌦️ Live weather")

default_lat = float(locations_df.iloc[0]["latitude"]) if not locations_df.empty else 30.35
default_lon = float(locations_df.iloc[0]["longitude"]) if not locations_df.empty else 79.10

try:
    weather_data = get_weather(default_lat, default_lon)
    current = weather_data.get("current", {})
    rain_now = current.get("precipitation", 0)
    temp = current.get("temperature_2m", 0)
    humidity = current.get("relative_humidity_2m", 0)
    wind = current.get("wind_speed_10m", 0)
    weather_code = current.get("weather_code", 0)

    st.metric("Temperature", f"{temp} °C")
    st.metric("Rainfall (current)", f"{rain_now} mm")
    st.metric("Humidity", f"{humidity} %")
    st.metric("Wind speed", f"{wind} km/h")
    st.write(f"Weather code: {weather_code}")
except Exception:
    st.warning("Live weather could not be loaded. Showing fallback values.")
    rain_now = 0
    temp = 15
    humidity = 60
    wind = 5
    weather_code = 0


# -------------------------
# Map section
# -------------------------
st.header("🗺️ Landslide risk & incidents map")

map_view = folium.Map(
    location=[30.35, 79.10],
    zoom_start=8,
    tiles=None,
)

folium.TileLayer(
    tiles=(
        "https://server.arcgisonline.com/"
        "ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    ),
    attr="Tiles © Esri",
    name="Satellite",
).add_to(map_view)

folium.TileLayer(
    tiles="OpenStreetMap",
    attr="© OpenStreetMap",
    name="Street Map",
).add_to(map_view)

folium.LayerControl(position="topright").add_to(map_view)


def calculate_risk_level(rain_mm, slope_deg, elevation_m, soil_factor, history_factor):
    score = 0
    reasons = []

    if rain_mm >= 80:
        score += 40
        reasons.append("Very high rainfall (≥80 mm)")
    elif rain_mm >= 50:
        score += 25
        reasons.append("High rainfall (50–80 mm)")
    elif rain_mm >= 20:
        score += 10
        reasons.append("Moderate rainfall (20–50 mm)")

    if slope_deg >= 35:
        score += 30
        reasons.append("Steep slope (≥35°)")
    elif slope_deg >= 20:
        score += 15
        reasons.append("Moderate slope (20–35°)")

    if elevation_m >= 2500:
        score += 15
        reasons.append("High elevation (≥2500 m)")
    elif elevation_m >= 1500:
        score += 8
        reasons.append("Moderate elevation (1500–2500 m)")

    if soil_factor == "Loose / unconsolidated":
        score += 15
        reasons.append("Loose or unconsolidated soil")
    elif soil_factor == "Moderate":
        score += 8
        reasons.append("Moderate soil stability")

    if history_factor == "Yes":
        score += 20
        reasons.append("Past landslide events recorded")

    if score >= 80:
        level = "High"
        color = "red"
    elif score >= 50:
        level = "Moderate"
        color = "orange"
    elif score >= 25:
        level = "Lower"
        color = "yellow"
    else:
        level = "Low"
        color = "green"

    return level, color, score, reasons


# Risk markers from sample_locations.csv
for _, row in locations_df.iterrows():
    lat = float(row.get("latitude", 30.35))
    lon = float(row.get("longitude", 79.10))
    elev = float(row.get("elevation", 1500))
    slope = float(row.get("slope", 25))
    soil = str(row.get("soil_type", "Moderate"))
    history = str(row.get("landslide_history", "No"))

    place = str(row.get("place_name", "Unknown location"))
    district = str(row.get("district", "N/A"))

    level, color, score, reasons = calculate_risk_level(
        rain_now, slope, elev, soil, history
    )

    popup_text = (
        f"<b>{place}</b><br>"
        f"District: {district}<br>"
        f"Risk level: {level}<br>"
        f"Risk score: {score}<br>"
        f"Contributing factors:<br>"
        + "<br>".join(f"• {r}" for r in reasons)
    )

    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_text, max_width=300),
        icon=folium.Icon(color=color, icon="exclamation-sign", prefix="fa"),
    ).add_to(map_view)


# Citizen incident reports (new Report Area)
for _, row in reports_df.iterrows():
    if pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")):
        continue

    lat = float(row.get("latitude", 0))
    lon = float(row.get("longitude", 0))
    status = str(row.get("status", "Unverified"))
    rep_type = str(row.get("report_type", "Incident"))
    place = str(row.get("place_name", "Unknown"))
    severity = str(row.get("severity", "Moderate"))
    desc = str(row.get("description", ""))
    reported_at = str(row.get("reported_at", ""))

    if status == "Resolved":
        color = "green"
    elif status == "Verified":
        color = "orange"
    else:
        color = "red"

    popup_text = (
        f"<b>{rep_type} – {place}</b><br>"
        f"Severity: {severity}<br>"
        f"Status: {status}<br>"
        f"Reported at: {reported_at}<br>"
        f"Description: {desc}"
    )

    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_text, max_width=300),
        icon=folium.Icon(color=color, icon="info-sign", prefix="fa"),
    ).add_to(map_view)


# Road blockage markers (existing feature)
for _, row in blockages_df.iterrows():
    if pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")):
        continue

    lat = float(row.get("latitude", 0))
    lon = float(row.get("longitude", 0))
    status = str(row.get("status", "Completely blocked"))
    verified = str(row.get("verified", "No"))
    rep_type = str(row.get("blockage_type", "Road blockage"))
    road_name = str(row.get("road_name", "Unknown road"))
    severity = str(row.get("severity", "Moderate"))
    desc = str(row.get("description", ""))
    reported_at = str(row.get("reported_at", ""))

    if verified == "Yes":
        color = "orange"
    else:
        color = "red"

    popup_text = (
        f"<b>{rep_type} – {road_name}</b><br>"
        f"Status: {status}<br>"
        f"Severity: {severity}<br>"
        f"Verified: {verified}<br>"
        f"Reported at: {reported_at}<br>"
        f"Description: {desc}"
    )

    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_text, max_width=300),
        icon=folium.Icon(color=color, icon="road", prefix="fa"),
    ).add_to(map_view)


st_folium(map_view, width=900, height=600, key="main_risk_report_map")


# -------------------------
# Report an Incident (NEW)
# -------------------------
st.divider()
st.header("📍 Report an Incident")

st.write(
    "Use this form to report landslides, road blockages, rockfalls, flash floods, or other hazards. "
    "Reports will appear on the map and in the reports dashboard."
)

with st.form("incident_report_form", clear_on_submit=True):
    rep_type = st.selectbox(
        "Incident type",
        [
            "Landslide",
            "Road blocked",
            "Rockfall",
            "Flash flood",
            "Bridge damage",
            "Other",
        ],
    )

    place_name = st.text_input("Place / location name", "")

    col1, col2 = st.columns(2)
    with col1:
        lat_input = st.number_input("Latitude", value=30.35, format="%.6f")
    with col2:
        lon_input = st.number_input("Longitude", value=79.10, format="%.6f")

    severity = st.selectbox(
        "Severity",
        ["Low", "Moderate", "High", "Critical"],
    )

    description = st.text_area("Description (what happened, impact, etc.)", "")

    reporter_name = st.text_input("Your name (optional)", "")
    reporter_contact = st.text_input("Your contact (optional)", "")

    submitted = st.form_submit_button("Submit report")

    if submitted:
        if not place_name.strip():
            st.error("Please enter a place / location name.")
        else:
            report_id = str(uuid.uuid4())[:8]
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            report_dict = {
                "id": report_id,
                "report_type": rep_type,
                "place_name": place_name.strip(),
                "latitude": lat_input,
                "longitude": lon_input,
                "severity": severity,
                "status": "Unverified",
                "description": description.strip(),
                "reporter_name": reporter_name.strip(),
                "reporter_contact": reporter_contact.strip(),
                "reported_at": now_str,
            }

            save_report(report_dict)
            st.success("Report submitted successfully. It will appear on the map and in the dashboard.")


# -------------------------
# Reports Dashboard (NEW)
# -------------------------
st.divider()
st.header("📋 Reports Dashboard")

if reports_df.empty:
    st.info("No reports submitted yet.")
else:
    st.write("All incident reports submitted via PahadiSathi.")

    filter_status = st.multiselect(
        "Filter by status",
        options=["Unverified", "Verified", "Resolved"],
        default=["Unverified", "Verified", "Resolved"],
    )

    filtered = reports_df[reports_df["status"].isin(filter_status)]

    display_cols = [
        c
        for c in [
            "id",
            "report_type",
            "place_name",
            "severity",
            "status",
            "reported_at",
            "description",
        ]
        if c in filtered.columns
    ]

    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
    )


# -------------------------
# Road blockage reporting (existing)
# -------------------------
st.divider()
st.header("🚧 Road blockage reporting")

st.write(
    "Report blocked, partially blocked, or reopened roads for faster response planning. "
    "This complements the general incident reports above."
)


def save_road_blockage(row_dict):
    df = load_road_blockages()
    new_row = pd.DataFrame([row_dict])
    df = pd.concat([df, new_row], ignore_index=True)
    expected_cols = [
        "road_name",
        "district",
        "latitude",
        "longitude",
        "blockage_type",
        "status",
        "severity",
        "verified",
        "reported_at",
        "reporter",
        "description",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None
    df = df[expected_cols]
    df.to_csv(ROAD_BLOCKAGES_PATH, index=False)


with st.form("road_blockage_form", clear_on_submit=True):
    road_name = st.text_input("Road / highway name", "")
    district = st.text_input("District", "")

    col_lat1, col_lon1 = st.columns(2)
    with col_lat1:
        lat_rb = st.number_input("Latitude", value=30.35, format="%.6f", key="rb_lat")
    with col_lon1:
        lon_rb = st.number_input("Longitude", value=79.10, format="%.6f", key="rb_lon")

    blockage_type = st.selectbox(
        "Blockage type",
        [
            "Landslide debris",
            "Boulder fall",
            "Road subsidence",
            "Bridge damage",
            "Water logging",
            "Other",
        ],
    )

    status_rb = st.selectbox(
        "Current status",
        [
            "Completely blocked",
            "Partially blocked",
            "Single lane open",
            "Reopened",
        ],
    )

    severity_rb = st.selectbox(
        "Severity",
        ["Low", "Moderate", "High", "Critical"],
    )

    desc_rb = st.text_area("Description (optional)", "")
    reporter_rb = st.text_input("Reporter name (optional)", "")

    submitted_rb = st.form_submit_button("Submit road blockage report")

    if submitted_rb:
        if not road_name.strip():
            st.error("Please enter a road / highway name.")
        else:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rb_dict = {
                "road_name": road_name.strip(),
                "district": district.strip(),
                "latitude": lat_rb,
                "longitude": lon_rb,
                "blockage_type": blockage_type,
                "status": status_rb,
                "severity": severity_rb,
                "verified": "No",
                "reported_at": now_str,
                "reporter": reporter_rb.strip(),
                "description": desc_rb.strip(),
            }
            save_road_blockage(rb_dict)
            st.success("Road blockage report submitted. It will appear on the map.")


# Road blockage table
st.subheader("Active road blockages")

if blockages_df.empty:
    st.info("No road blockage reports yet.")
else:
    st.dataframe(
        blockages_df[
            [
                "road_name",
                "district",
                "blockage_type",
                "status",
                "severity",
                "verified",
                "reported_at",
            ]
        ],
        use_container_width=True,
    )


# -------------------------
# Risk calculator (existing)
# -------------------------
st.divider()
st.header("🧮 Manual risk calculator")

st.write(
    "Enter local parameters to estimate landslide risk at a specific location. "
    "This uses a transparent rule-based scoring system."
)

col_r1, col_r2 = st.columns(2)

with col_r1:
    rain_input = st.number_input(
        "Recent rainfall (mm)",
        min_value=0.0,
        value=float(rain_now),
        step=5.0,
    )
    slope_input = st.number_input(
        "Slope (degrees)",
        min_value=0.0,
        max_value=90.0,
        value=25.0,
        step=1.0,
    )

with col_r2:
    elev_input = st.number_input(
        "Elevation (m)",
        min_value=0,
        value=1500,
        step=50,
    )
    soil_input = st.selectbox(
        "Soil / rock condition",
        [
            "Stable / rocky",
            "Moderate",
            "Loose / unconsolidated",
        ],
    )
    history_input = st.selectbox(
        "Past landslide history here?",
        ["No", "Yes"],
    )

level_r, color_r, score_r, reasons_r = calculate_risk_level(
    rain_input,
    slope_input,
    elev_input,
    soil_input,
    history_input,
)

st.write(f"**Estimated risk level:** {level_r}")
st.write(f"**Risk score:** {score_r}")

if reasons_r:
    st.write("**Main contributing factors:**")
    for r in reasons_r:
        st.write(f"- {r}")
else:
    st.write("No strong risk factors detected with the current inputs.")


# -------------------------
# Footer / disclaimer
# -------------------------
st.divider()
st.write(
    "⚠️ **Disclaimer:** PahadiSathi is a student prototype for decision support. "
    "Do not rely on it as an official early-warning or emergency system. "
    "Always follow guidance from local authorities and disaster-management agencies."
)
