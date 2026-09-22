from pathlib import Path
from datetime import datetime
import uuid
import json

import pandas as pd
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium


# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="PahadiSathi",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------
# Paths
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

LOCATIONS_FILE = DATA_DIR / "sample_locations.csv"
REPORTS_FILE = DATA_DIR / "reports.csv"
BLOCKAGES_FILE = DATA_DIR / "road_blockages.csv"


# -----------------------------
# Built-in Uttarakhand locations
# -----------------------------
DEFAULT_LOCATIONS = [
    {
        "place_name": "Dehradun",
        "district": "Dehradun",
        "latitude": 30.3165,
        "longitude": 78.0322,
        "elevation": 435,
        "slope": 12,
        "soil_type": "Moderate",
        "landslide_history": "No",
    },
    {
        "place_name": "Haridwar",
        "district": "Haridwar",
        "latitude": 29.9457,
        "longitude": 78.1642,
        "elevation": 310,
        "slope": 8,
        "soil_type": "Moderate",
        "landslide_history": "No",
    },
    {
        "place_name": "Rishikesh",
        "district": "Dehradun",
        "latitude": 30.0869,
        "longitude": 78.2676,
        "elevation": 370,
        "slope": 10,
        "soil_type": "Moderate",
        "landslide_history": "No",
    },
    {
        "place_name": "Roorkee",
        "district": "Haridwar",
        "latitude": 29.8543,
        "longitude": 77.8880,
        "elevation": 260,
        "slope": 6,
        "soil_type": "Stable",
        "landslide_history": "No",
    },
    {
        "place_name": "Haldwani",
        "district": "Nainital",
        "latitude": 29.2183,
        "longitude": 79.5130,
        "elevation": 424,
        "slope": 12,
        "soil_type": "Moderate",
        "landslide_history": "No",
    },
    {
        "place_name": "Nainital",
        "district": "Nainital",
        "latitude": 29.3919,
        "longitude": 79.4542,
        "elevation": 2084,
        "slope": 28,
        "soil_type": "Weak",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Almora",
        "district": "Almora",
        "latitude": 29.5971,
        "longitude": 79.6591,
        "elevation": 1650,
        "slope": 25,
        "soil_type": "Moderate",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Ranikhet",
        "district": "Almora",
        "latitude": 29.6434,
        "longitude": 79.4322,
        "elevation": 1869,
        "slope": 24,
        "soil_type": "Moderate",
        "landslide_history": "No",
    },
    {
        "place_name": "Pithoragarh",
        "district": "Pithoragarh",
        "latitude": 29.5829,
        "longitude": 80.2182,
        "elevation": 1650,
        "slope": 30,
        "soil_type": "Weak",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Champawat",
        "district": "Champawat",
        "latitude": 29.3364,
        "longitude": 80.0911,
        "elevation": 1615,
        "slope": 26,
        "soil_type": "Moderate",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Bageshwar",
        "district": "Bageshwar",
        "latitude": 29.8376,
        "longitude": 79.7724,
        "elevation": 1004,
        "slope": 24,
        "soil_type": "Moderate",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Joshimath",
        "district": "Chamoli",
        "latitude": 30.5560,
        "longitude": 79.5640,
        "elevation": 1875,
        "slope": 36,
        "soil_type": "Weak",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Gopeshwar",
        "district": "Chamoli",
        "latitude": 30.4100,
        "longitude": 79.3210,
        "elevation": 1550,
        "slope": 22,
        "soil_type": "Moderate",
        "landslide_history": "No",
    },
    {
        "place_name": "Badrinath",
        "district": "Chamoli",
        "latitude": 30.7433,
        "longitude": 79.4938,
        "elevation": 3133,
        "slope": 38,
        "soil_type": "Weak",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Karnaprayag",
        "district": "Chamoli",
        "latitude": 30.2597,
        "longitude": 79.2530,
        "elevation": 1451,
        "slope": 26,
        "soil_type": "Moderate",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Rudraprayag",
        "district": "Rudraprayag",
        "latitude": 30.2850,
        "longitude": 78.9810,
        "elevation": 895,
        "slope": 30,
        "soil_type": "Weak",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Kedarnath",
        "district": "Rudraprayag",
        "latitude": 30.7346,
        "longitude": 79.0669,
        "elevation": 3583,
        "slope": 40,
        "soil_type": "Weak",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Uttarkashi",
        "district": "Uttarkashi",
        "latitude": 30.7268,
        "longitude": 78.4354,
        "elevation": 1150,
        "slope": 29,
        "soil_type": "Weak",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Gangotri",
        "district": "Uttarkashi",
        "latitude": 30.9947,
        "longitude": 78.9398,
        "elevation": 3048,
        "slope": 37,
        "soil_type": "Weak",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Purola",
        "district": "Uttarkashi",
        "latitude": 30.9300,
        "longitude": 78.4300,
        "elevation": 1500,
        "slope": 21,
        "soil_type": "Moderate",
        "landslide_history": "No",
    },
    {
        "place_name": "Barkot",
        "district": "Uttarkashi",
        "latitude": 30.9100,
        "longitude": 78.2800,
        "elevation": 1100,
        "slope": 17,
        "soil_type": "Moderate",
        "landslide_history": "No",
    },
    {
        "place_name": "Tehri",
        "district": "Tehri Garhwal",
        "latitude": 30.3780,
        "longitude": 78.4800,
        "elevation": 1550,
        "slope": 28,
        "soil_type": "Weak",
        "landslide_history": "Yes",
    },
    {
        "place_name": "New Tehri",
        "district": "Tehri Garhwal",
        "latitude": 30.3753,
        "longitude": 78.4804,
        "elevation": 1950,
        "slope": 25,
        "soil_type": "Moderate",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Pauri",
        "district": "Pauri Garhwal",
        "latitude": 30.1460,
        "longitude": 78.7800,
        "elevation": 1814,
        "slope": 27,
        "soil_type": "Moderate",
        "landslide_history": "Yes",
    },
    {
        "place_name": "Lansdowne",
        "district": "Pauri Garhwal",
        "latitude": 29.8419,
        "longitude": 78.6871,
        "elevation": 1780,
        "slope": 23,
        "soil_type": "Moderate",
        "landslide_history": "No",
    },
    {
        "place_name": "Kotdwar",
        "district": "Pauri Garhwal",
        "latitude": 29.7460,
        "longitude": 78.5220,
        "elevation": 395,
        "slope": 10,
        "soil_type": "Stable",
        "landslide_history": "No",
    },
    {
        "place_name": "Vikasnagar",
        "district": "Dehradun",
        "latitude": 30.4690,
        "longitude": 77.7750,
        "elevation": 650,
        "slope": 12,
        "soil_type": "Moderate",
        "landslide_history": "No",
    },
]


# -----------------------------
# Utility functions
# -----------------------------
def clean_columns(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    return df


def make_location_dataframe(rows):
    df = pd.DataFrame(rows)
    df = clean_columns(df)

    required = [
        "place_name",
        "district",
        "latitude",
        "longitude",
        "elevation",
        "slope",
        "soil_type",
        "landslide_history",
    ]

    for column in required:
        if column not in df.columns:
            if column == "place_name" and "location" in df.columns:
                df["place_name"] = df["location"]
            else:
                df[column] = ""

    for column in ["latitude", "longitude", "elevation", "slope"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=["latitude", "longitude"])
    df["place_name"] = df["place_name"].astype(str).str.strip()
    df["district"] = df["district"].astype(str).str.strip()

    return df[required].drop_duplicates(subset=["place_name"])


@st.cache_data
def load_locations():
    if LOCATIONS_FILE.exists():
        try:
            csv_df = pd.read_csv(LOCATIONS_FILE)
            csv_df = clean_columns(csv_df)

            if "place_name" not in csv_df.columns and "location" in csv_df.columns:
                csv_df["place_name"] = csv_df["location"]

            csv_df = make_location_dataframe(csv_df.to_dict("records"))

            if len(csv_df) > 0:
                return csv_df

        except Exception:
            pass

    default_df = make_location_dataframe(DEFAULT_LOCATIONS)

    try:
        default_df.to_csv(LOCATIONS_FILE, index=False)
    except Exception:
        pass

    return default_df


def ensure_file(file_path, columns):
    if not file_path.exists():
        pd.DataFrame(columns=columns).to_csv(file_path, index=False)


def load_csv(file_path, columns):
    ensure_file(file_path, columns)

    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return pd.DataFrame(columns=columns)
        return df
    except Exception:
        return pd.DataFrame(columns=columns)


def calculate_risk(row, rainfall=0, soil_moisture=50):
    score = 0

    slope = float(row.get("slope", 0) or 0)
    elevation = float(row.get("elevation", 0) or 0)
    soil = str(row.get("soil_type", "")).lower()
    history = str(row.get("landslide_history", "")).lower()

    if slope >= 35:
        score += 35
    elif slope >= 25:
        score += 25
    elif slope >= 15:
        score += 15
    else:
        score += 5

    if elevation >= 2500:
        score += 20
    elif elevation >= 1500:
        score += 12
    else:
        score += 5

    if "weak" in soil:
        score += 20
    elif "moderate" in soil:
        score += 10
    else:
        score += 5

    if history in ["yes", "1", "true"]:
        score += 15

    rainfall = float(rainfall or 0)
    soil_moisture = float(soil_moisture or 0)

    if rainfall >= 100:
        score += 10
    elif rainfall >= 50:
        score += 6
    elif rainfall >= 20:
        score += 3

    if soil_moisture >= 80:
        score += 5
    elif soil_moisture >= 60:
        score += 3

    score = min(int(score), 100)

    if score >= 70:
        level = "High"
        color = "red"
    elif score >= 40:
        level = "Medium"
        color = "orange"
    else:
        level = "Low"
        color = "green"

    return score, level, color


@st.cache_data(ttl=900)
def get_weather(latitude, longitude):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        "&current=temperature_2m,relative_humidity_2m,precipitation,"
        "rain,wind_speed_10m"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("current", {})
    except Exception:
        return {}


def save_dataframe(df, path):
    df.to_csv(path, index=False)


def risk_popup(place, district, score, level):
    return (
        f"<b>{place}</b><br>"
        f"District: {district}<br>"
        f"Risk score: {score}/100<br>"
        f"Risk level: {level}"
    )


# -----------------------------
# Load data
# -----------------------------
locations_df = load_locations()

reports_df = load_csv(
    REPORTS_FILE,
    [
        "report_id",
        "created_at",
        "name",
        "phone",
        "location",
        "description",
        "severity",
        "status",
    ],
)

blockages_df = load_csv(
    BLOCKAGES_FILE,
    [
        "blockage_id",
        "created_at",
        "location",
        "road_name",
        "description",
        "severity",
        "status",
    ],
)


# -----------------------------
# Header
# -----------------------------
st.title("🏔️ PahadiSathi")
st.caption("AI-assisted landslide-risk and weather dashboard for Uttarakhand")

st.info(
    "PahadiSathi ek prototype decision-support system hai. "
    "Emergency ke liye hamesha local administration aur official alerts follow karein."
)


# -----------------------------
# City selector
# -----------------------------
st.subheader("📍 Select City / Location")

city_options = (
    locations_df["place_name"]
    .dropna()
    .astype(str)
    .str.strip()
    .replace("", pd.NA)
    .dropna()
    .drop_duplicates()
    .tolist()
)

if not city_options:
    st.error("Koi city nahi mili. sample_locations.csv check kijiye.")
    st.stop()

selected_city = st.selectbox(
    "City choose kijiye",
    city_options,
    index=0,
    key="city_selector",
)

selected_row = locations_df[
    locations_df["place_name"] == selected_city
].iloc[0]

selected_lat = float(selected_row["latitude"])
selected_lon = float(selected_row["longitude"])

selected_weather = get_weather(selected_lat, selected_lon)

rainfall_now = selected_weather.get("rain", 0)
humidity_now = selected_weather.get("relative_humidity_2m", 50)

selected_score, selected_level, selected_color = calculate_risk(
    selected_row,
    rainfall=rainfall_now,
    soil_moisture=humidity_now,
)


# -----------------------------
# Selected city information
# -----------------------------
st.subheader(f"📌 {selected_city}")

info_col1, info_col2, info_col3, info_col4 = st.columns(4)

info_col1.metric("District", str(selected_row["district"]))
info_col2.metric("Elevation", f"{selected_row['elevation']} m")
info_col3.metric("Slope", f"{selected_row['slope']}°")
info_col4.metric("Risk", f"{selected_score}/100 ({selected_level})")


# -----------------------------
# Weather
# -----------------------------
st.subheader("🌦️ Live Weather")

weather_col1, weather_col2, weather_col3, weather_col4 = st.columns(4)

if selected_weather:
    weather_col1.metric(
        "Temperature",
        f"{selected_weather.get('temperature_2m', 'N/A')} °C",
    )
    weather_col2.metric(
        "Humidity",
        f"{selected_weather.get('relative_humidity_2m', 'N/A')}%",
    )
    weather_col3.metric(
        "Rain",
        f"{selected_weather.get('rain', 'N/A')} mm",
    )
    weather_col4.metric(
        "Wind",
        f"{selected_weather.get('wind_speed_10m', 'N/A')} km/h",
    )
else:
    st.warning("Weather service temporarily unavailable.")


# -----------------------------
# Map
# -----------------------------
st.subheader("🗺️ Landslide Risk Map")

map_obj = folium.Map(
    location=[selected_lat, selected_lon],
    zoom_start=9,
    control_scale=True,
)

for _, row in locations_df.iterrows():
    row_weather = get_weather(float(row["latitude"]), float(row["longitude"]))
    row_rain = row_weather.get("rain", 0)
    row_humidity = row_weather.get("relative_humidity_2m", 50)

    score, level, color = calculate_risk(
        row,
        rainfall=row_rain,
        soil_moisture=row_humidity,
    )

    popup = risk_popup(
        row["place_name"],
        row["district"],
        score,
        level,
    )

    folium.CircleMarker(
        location=[float(row["latitude"]), float(row["longitude"])],
        radius=9 if row["place_name"] == selected_city else 6,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.8,
        popup=folium.Popup(popup, max_width=280),
        tooltip=f"{row['place_name']} - {level}",
    ).add_to(map_obj)

st_folium(map_obj, width=None, height=560)


# -----------------------------
# Risk calculator
# -----------------------------
st.subheader("🧮 Manual Risk Calculator")

calc_col1, calc_col2 = st.columns(2)

with calc_col1:
    manual_rainfall = st.number_input(
        "Rainfall in last 24 hours (mm)",
        min_value=0.0,
        max_value=1000.0,
        value=float(rainfall_now or 0),
        step=1.0,
    )

with calc_col2:
    manual_moisture = st.slider(
        "Soil moisture (%)",
        min_value=0,
        max_value=100,
        value=int(humidity_now or 50),
    )

manual_score, manual_level, _ = calculate_risk(
    selected_row,
    rainfall=manual_rainfall,
    soil_moisture=manual_moisture,
)

st.metric(
    "Calculated Risk",
    f"{manual_score}/100 - {manual_level}",
)


# -----------------------------
# Incident report
# -----------------------------
st.subheader("🚨 Report an Incident")

with st.form("incident_form", clear_on_submit=True):
    report_name = st.text_input("Your name")
    report_phone = st.text_input("Phone number")
    report_location = st.text_input(
        "Incident location",
        value=selected_city,
    )
    report_description = st.text_area(
        "Describe the incident",
        placeholder="Landslide, road crack, falling rocks, blocked road, etc.",
    )
    report_severity = st.selectbox(
        "Severity",
        ["Low", "Medium", "High", "Critical"],
    )

    report_submit = st.form_submit_button("Submit Incident Report")

    if report_submit:
        if not report_location.strip() or not report_description.strip():
            st.error("Location aur description required hain.")
        else:
            new_report = {
                "report_id": str(uuid.uuid4()),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "name": report_name.strip(),
                "phone": report_phone.strip(),
                "location": report_location.strip(),
                "description": report_description.strip(),
                "severity": report_severity,
                "status": "Pending",
            }

            reports_df = pd.concat(
                [reports_df, pd.DataFrame([new_report])],
                ignore_index=True,
            )

            save_dataframe(reports_df, REPORTS_FILE)
            st.success("Incident report successfully submit ho gayi.")


# -----------------------------
# Road blockage report
# -----------------------------
st.subheader("🚧 Report Road Blockage")

with st.form("blockage_form", clear_on_submit=True):
    blockage_location = st.text_input(
        "Blockage location",
        value=selected_city,
    )
    blockage_road = st.text_input("Road / highway name")
    blockage_description = st.text_area(
        "Blockage details",
        placeholder="Road blocked by debris, water, rocks, landslide, etc.",
    )
    blockage_severity = st.selectbox(
        "Blockage severity",
        ["Low", "Medium", "High", "Critical"],
    )

    blockage_submit = st.form_submit_button("Submit Road Blockage")

    if blockage_submit:
        if (
            not blockage_location.strip()
            or not blockage_road.strip()
            or not blockage_description.strip()
        ):
            st.error("Location, road name aur details required hain.")
        else:
            new_blockage = {
                "blockage_id": str(uuid.uuid4()),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "location": blockage_location.strip(),
                "road_name": blockage_road.strip(),
                "description": blockage_description.strip(),
                "severity": blockage_severity,
                "status": "Open",
            }

            blockages_df = pd.concat(
                [blockages_df, pd.DataFrame([new_blockage])],
                ignore_index=True,
            )

            save_dataframe(blockages_df, BLOCKAGES_FILE)
            st.success("Road blockage report successfully submit ho gayi.")


# -----------------------------
# Dashboard tables
# -----------------------------
st.subheader("📊 Reports Dashboard")

tab1, tab2, tab3 = st.tabs(
    ["All Cities", "Incident Reports", "Road Blockages"]
)

with tab1:
    display_df = locations_df.copy()
    display_df["risk_score"] = display_df.apply(
        lambda row: calculate_risk(row)[0],
        axis=1,
    )
    display_df["risk_level"] = display_df.apply(
        lambda row: calculate_risk(row)[1],
        axis=1,
    )

    st.dataframe(
        display_df[
            [
                "place_name",
                "district",
                "elevation",
                "slope",
                "risk_score",
                "risk_level",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

with tab2:
    if reports_df.empty:
        st.info("Abhi koi incident report nahi hai.")
    else:
        st.dataframe(
            reports_df.sort_values("created_at", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

with tab3:
    if blockages_df.empty:
        st.info("Abhi koi road blockage report nahi hai.")
    else:
        st.dataframe(
            blockages_df.sort_values("created_at", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


# -----------------------------
# Debug information
# -----------------------------
with st.expander("🔧 Data and Debug Information"):
    st.write("Locations file:", str(LOCATIONS_FILE))
    st.write("Total cities loaded:", len(locations_df))
    st.write("City column: place_name")
    st.write("Loaded cities:", city_options)
    st.write("CSV columns:", locations_df.columns.tolist())


st.caption(
    "PahadiSathi prototype — risk values are indicative and not an official warning."
)
