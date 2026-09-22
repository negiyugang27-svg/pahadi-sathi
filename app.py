from pathlib import Path
from datetime import datetime
import uuid
import html

import pandas as pd
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium


# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="PahadiSathi",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# PATHS
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOCATIONS_FILE = DATA_DIR / "sample_locations.csv"
REPORTS_FILE = DATA_DIR / "reports.csv"
BLOCKAGES_FILE = DATA_DIR / "road_blockages.csv"


# =========================================================
# BUILT-IN CITY DATA
# =========================================================
DEFAULT_LOCATIONS = [
    ["Dehradun", "Dehradun", 30.3165, 78.0322, 435, 12, "Moderate", "No"],
    ["Haridwar", "Haridwar", 29.9457, 78.1642, 310, 8, "Moderate", "No"],
    ["Rishikesh", "Dehradun", 30.0869, 78.2676, 370, 10, "Moderate", "No"],
    ["Roorkee", "Haridwar", 29.8543, 77.8880, 260, 6, "Stable", "No"],
    ["Haldwani", "Nainital", 29.2183, 79.5130, 424, 12, "Moderate", "No"],
    ["Nainital", "Nainital", 29.3919, 79.4542, 2084, 28, "Weak", "Yes"],
    ["Almora", "Almora", 29.5971, 79.6591, 1650, 25, "Moderate", "Yes"],
    ["Ranikhet", "Almora", 29.6434, 79.4322, 1869, 24, "Moderate", "No"],
    ["Pithoragarh", "Pithoragarh", 29.5829, 80.2182, 1650, 30, "Weak", "Yes"],
    ["Champawat", "Champawat", 29.3364, 80.0911, 1615, 26, "Moderate", "Yes"],
    ["Bageshwar", "Bageshwar", 29.8376, 79.7724, 1004, 24, "Moderate", "Yes"],
    ["Joshimath", "Chamoli", 30.5560, 79.5640, 1875, 36, "Weak", "Yes"],
    ["Gopeshwar", "Chamoli", 30.4100, 79.3210, 1550, 22, "Moderate", "No"],
    ["Badrinath", "Chamoli", 30.7433, 79.4938, 3133, 38, "Weak", "Yes"],
    ["Karnaprayag", "Chamoli", 30.2597, 79.2530, 1451, 26, "Moderate", "Yes"],
    ["Rudraprayag", "Rudraprayag", 30.2850, 78.9810, 895, 30, "Weak", "Yes"],
    ["Kedarnath", "Rudraprayag", 30.7346, 79.0669, 3583, 40, "Weak", "Yes"],
    ["Uttarkashi", "Uttarkashi", 30.7268, 78.4354, 1150, 29, "Weak", "Yes"],
    ["Gangotri", "Uttarkashi", 30.9947, 78.9398, 3048, 37, "Weak", "Yes"],
    ["Purola", "Uttarkashi", 30.9300, 78.4300, 1500, 21, "Moderate", "No"],
    ["Barkot", "Uttarkashi", 30.9100, 78.2800, 1100, 17, "Moderate", "No"],
    ["Tehri", "Tehri Garhwal", 30.3780, 78.4800, 1550, 28, "Weak", "Yes"],
    ["New Tehri", "Tehri Garhwal", 30.3753, 78.4804, 1950, 25, "Moderate", "Yes"],
    ["Pauri", "Pauri Garhwal", 30.1460, 78.7800, 1814, 27, "Moderate", "Yes"],
    ["Lansdowne", "Pauri Garhwal", 29.8419, 78.6871, 1780, 23, "Moderate", "No"],
    ["Kotdwar", "Pauri Garhwal", 29.7460, 78.5220, 395, 10, "Stable", "No"],
    ["Vikasnagar", "Dehradun", 30.4690, 77.7750, 650, 12, "Moderate", "No"],
]

LOCATION_COLUMNS = [
    "place_name",
    "district",
    "latitude",
    "longitude",
    "elevation",
    "slope",
    "soil_type",
    "landslide_history",
]

DEFAULT_LOCATION_DF = pd.DataFrame(
    DEFAULT_LOCATIONS,
    columns=LOCATION_COLUMNS,
)


# =========================================================
# DATA HELPERS
# =========================================================
def normalize_columns(df):
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )
    return df


def normalize_locations(df):
    df = normalize_columns(df)

    # Support old CSV format using "location"
    if "place_name" not in df.columns and "location" in df.columns:
        df["place_name"] = df["location"]

    # Support old CSV names if present
    rename_map = {
        "lat": "latitude",
        "lon": "longitude",
        "lng": "longitude",
        "height": "elevation",
        "gradient": "slope",
        "soil": "soil_type",
        "history": "landslide_history",
    }

    for old_name, new_name in rename_map.items():
        if new_name not in df.columns and old_name in df.columns:
            df[new_name] = df[old_name]

    # Add missing columns safely
    for column in LOCATION_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    for column in ["latitude", "longitude", "elevation", "slope"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["place_name"] = (
        df["place_name"]
        .astype("string")
        .str.strip()
    )

    df["district"] = (
        df["district"]
        .astype("string")
        .str.strip()
    )

    df["soil_type"] = (
        df["soil_type"]
        .astype("string")
        .str.strip()
        .fillna("Moderate")
    )

    df["landslide_history"] = (
        df["landslide_history"]
        .astype("string")
        .str.strip()
        .fillna("No")
    )

    df = df.dropna(subset=["latitude", "longitude"])
    df = df[df["place_name"].notna()]
    df = df[df["place_name"].str.len() > 0]

    return df[LOCATION_COLUMNS].copy()


def merge_locations(csv_df, default_df):
    """
    CSV aur built-in cities ko merge karta hai.
    CSV ki values same city ke liye priority leti hain.
    Built-in cities missing cities ke liye add hoti hain.
    """
    csv_df = normalize_locations(csv_df)
    default_df = normalize_locations(default_df)

    merged = pd.concat(
        [csv_df, default_df],
        ignore_index=True,
    )

    merged["place_name_key"] = (
        merged["place_name"]
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    merged = merged.drop_duplicates(
        subset=["place_name_key"],
        keep="first",
    )

    merged = merged.drop(columns=["place_name_key"])
    merged = merged.reset_index(drop=True)

    return merged


@st.cache_data
def load_locations(file_signature):
    """
    file_signature badalne par cached old CSV use nahi hoti.
    """
    csv_df = pd.DataFrame(columns=LOCATION_COLUMNS)

    if LOCATIONS_FILE.exists():
        try:
            csv_df = pd.read_csv(LOCATIONS_FILE)
        except Exception:
            csv_df = pd.DataFrame(columns=LOCATION_COLUMNS)

    final_df = merge_locations(
        csv_df,
        DEFAULT_LOCATION_DF,
    )

    # Complete merged list file mein save
    try:
        final_df.to_csv(
            LOCATIONS_FILE,
            index=False,
        )
    except Exception:
        pass

    return final_df


def ensure_csv(file_path, columns):
    if not file_path.exists():
        pd.DataFrame(columns=columns).to_csv(
            file_path,
            index=False,
        )


def load_csv(file_path, columns):
    ensure_csv(file_path, columns)

    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return pd.DataFrame(columns=columns)
        return df
    except Exception:
        return pd.DataFrame(columns=columns)


def save_csv(df, file_path):
    df.to_csv(file_path, index=False)


# =========================================================
# RISK AND WEATHER
# =========================================================
def safe_number(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_risk(row, rainfall=0, soil_moisture=50):
    slope = safe_number(row.get("slope", 0))
    elevation = safe_number(row.get("elevation", 0))
    rainfall = safe_number(rainfall)
    soil_moisture = safe_number(soil_moisture)

    soil = str(row.get("soil_type", "")).lower()
    history = str(row.get("landslide_history", "")).lower()

    score = 0

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

    if history in {"yes", "true", "1"}:
        score += 15

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
        return score, "High", "red"
    if score >= 40:
        return score, "Medium", "orange"
    return score, "Low", "green"


@st.cache_data(ttl=900)
def get_weather(latitude, longitude):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        "&current=temperature_2m,relative_humidity_2m,"
        "precipitation,rain,wind_speed_10m"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("current", {})
    except Exception:
        return {}


# =========================================================
# LOAD FILES
# =========================================================
if LOCATIONS_FILE.exists():
    location_signature = LOCATIONS_FILE.stat().st_mtime_ns
else:
    location_signature = 0

locations_df = load_locations(location_signature)

reports_columns = [
    "report_id",
    "created_at",
    "name",
    "phone",
    "location",
    "description",
    "severity",
    "status",
]

blockages_columns = [
    "blockage_id",
    "created_at",
    "location",
    "road_name",
    "description",
    "severity",
    "status",
]

reports_df = load_csv(REPORTS_FILE, reports_columns)
blockages_df = load_csv(BLOCKAGES_FILE, blockages_columns)


# =========================================================
# HEADER
# =========================================================
st.title("🏔️ PahadiSathi")
st.caption(
    "AI-assisted landslide-risk and live-weather dashboard "
    "for Uttarakhand"
)

st.info(
    "PahadiSathi ek prototype decision-support system hai. "
    "Emergency ke liye official authorities ke instructions follow karein."
)


# =========================================================
# CITY SELECTOR
# =========================================================
st.subheader("📍 Select City / Location")

city_options = (
    locations_df["place_name"]
    .dropna()
    .astype(str)
    .str.strip()
)

city_options = [
    city for city in dict.fromkeys(city_options.tolist())
    if city
]

if not city_options:
    st.error("City list empty hai.")
    st.stop()

selected_city = st.selectbox(
    "City choose kijiye",
    options=city_options,
    index=0,
    key="city_selector",
)

selected_rows = locations_df[
    locations_df["place_name"].astype(str).str.strip()
    == selected_city
]

if selected_rows.empty:
    st.error("Selected city ka data nahi mila.")
    st.stop()

selected_row = selected_rows.iloc[0]

selected_lat = safe_number(selected_row["latitude"])
selected_lon = safe_number(selected_row["longitude"])

selected_weather = get_weather(
    selected_lat,
    selected_lon,
)

rainfall_now = safe_number(
    selected_weather.get("rain", 0)
)

humidity_now = safe_number(
    selected_weather.get("relative_humidity_2m", 50),
)

selected_score, selected_level, selected_color = calculate_risk(
    selected_row,
    rainfall=rainfall_now,
    soil_moisture=humidity_now,
)


# =========================================================
# CITY DETAILS
# =========================================================
st.subheader(f"📌 {selected_city}")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "District",
    str(selected_row["district"]),
)

col2.metric(
    "Elevation",
    f"{safe_number(selected_row['elevation']):.0f} m",
)

col3.metric(
    "Slope",
    f"{safe_number(selected_row['slope']):.0f}°",
)

col4.metric(
    "Risk",
    f"{selected_score}/100 ({selected_level})",
)


# =========================================================
# WEATHER
# =========================================================
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
    st.warning(
        "Weather service temporarily unavailable. "
        "Risk calculation sample values par continue ho rahi hai."
    )


# =========================================================
# MAP
# =========================================================
st.subheader("🗺️ Landslide Risk Map")

risk_map = folium.Map(
    location=[selected_lat, selected_lon],
    zoom_start=8,
    control_scale=True,
)

for _, row in locations_df.iterrows():
    lat = safe_number(row["latitude"])
    lon = safe_number(row["longitude"])

    # Map ke liye base risk; selected city par live weather use hota hai
    row_score, row_level, row_color = calculate_risk(row)

    popup_html = f"""
    <b>{html.escape(str(row['place_name']))}</b><br>
    District: {html.escape(str(row['district']))}<br>
    Elevation: {safe_number(row['elevation']):.0f} m<br>
    Slope: {safe_number(row['slope']):.0f}°<br>
    Risk: {row_score}/100<br>
    Level: {row_level}
    """

    folium.CircleMarker(
        location=[lat, lon],
        radius=10 if str(row["place_name"]) == selected_city else 6,
        color=row_color,
        fill=True,
        fill_color=row_color,
        fill_opacity=0.85,
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=f"{row['place_name']} - {row_level}",
    ).add_to(risk_map)

st_folium(
    risk_map,
    width=None,
    height=560,
)


# =========================================================
# MANUAL RISK CALCULATOR
# =========================================================
st.subheader("🧮 Manual Risk Calculator")

calc_col1, calc_col2 = st.columns(2)

with calc_col1:
    manual_rainfall = st.number_input(
        "Rainfall in last 24 hours (mm)",
        min_value=0.0,
        max_value=1000.0,
        value=float(rainfall_now),
        step=1.0,
    )

with calc_col2:
    manual_moisture = st.slider(
        "Soil moisture (%)",
        min_value=0,
        max_value=100,
        value=max(0, min(100, int(humidity_now))),
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


# =========================================================
# INCIDENT REPORT
# =========================================================
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
        placeholder=(
            "Landslide, road crack, falling rocks, "
            "blocked road, etc."
        ),
    )
    report_severity = st.selectbox(
        "Severity",
        ["Low", "Medium", "High", "Critical"],
        key="incident_severity",
    )

    report_submit = st.form_submit_button(
        "Submit Incident Report"
    )

    if report_submit:
        if (
            not report_location.strip()
            or not report_description.strip()
        ):
            st.error(
                "Location aur description required hain."
            )
        else:
            new_report = {
                "report_id": str(uuid.uuid4()),
                "created_at": datetime.now().isoformat(
                    timespec="seconds"
                ),
                "name": report_name.strip(),
                "phone": report_phone.strip(),
                "location": report_location.strip(),
                "description": report_description.strip(),
                "severity": report_severity,
                "status": "Pending",
            }

            reports_df = pd.concat(
                [
                    reports_df,
                    pd.DataFrame([new_report]),
                ],
                ignore_index=True,
            )

            save_csv(reports_df, REPORTS_FILE)

            st.success(
                "Incident report successfully submit ho gayi."
            )


# =========================================================
# ROAD BLOCKAGE REPORT
# =========================================================
st.subheader("🚧 Report Road Blockage")

with st.form("blockage_form", clear_on_submit=True):
    blockage_location = st.text_input(
        "Blockage location",
        value=selected_city,
    )
    blockage_road = st.text_input(
        "Road / highway name"
    )
    blockage_description = st.text_area(
        "Blockage details",
        placeholder=(
            "Road blocked by debris, water, rocks, "
            "landslide, etc."
        ),
    )
    blockage_severity = st.selectbox(
        "Blockage severity",
        ["Low", "Medium", "High", "Critical"],
        key="blockage_severity",
    )

    blockage_submit = st.form_submit_button(
        "Submit Road Blockage"
    )

    if blockage_submit:
        if (
            not blockage_location.strip()
            or not blockage_road.strip()
            or not blockage_description.strip()
        ):
            st.error(
                "Location, road name aur details required hain."
            )
        else:
            new_blockage = {
                "blockage_id": str(uuid.uuid4()),
                "created_at": datetime.now().isoformat(
                    timespec="seconds"
                ),
                "location": blockage_location.strip(),
                "road_name": blockage_road.strip(),
                "description": blockage_description.strip(),
                "severity": blockage_severity,
                "status": "Open",
            }

            blockages_df = pd.concat(
                [
                    blockages_df,
                    pd.DataFrame([new_blockage]),
                ],
                ignore_index=True,
            )

            save_csv(blockages_df, BLOCKAGES_FILE)

            st.success(
                "Road blockage report successfully submit ho gayi."
            )


# =========================================================
# DASHBOARD
# =========================================================
st.subheader("📊 Dashboard")

tab1, tab2, tab3 = st.tabs(
    [
        "All Cities",
        "Incident Reports",
        "Road Blockages",
    ]
)

with tab1:
    dashboard_df = locations_df.copy()

    dashboard_df["risk_score"] = dashboard_df.apply(
        lambda row: calculate_risk(row)[0],
        axis=1,
    )

    dashboard_df["risk_level"] = dashboard_df.apply(
        lambda row: calculate_risk(row)[1],
        axis=1,
    )

    st.dataframe(
        dashboard_df[
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
            reports_df.sort_values(
                "created_at",
                ascending=False,
            ),
            use_container_width=True,
            hide_index=True,
        )

with tab3:
    if blockages_df.empty:
        st.info("Abhi koi road blockage report nahi hai.")
    else:
        st.dataframe(
            blockages_df.sort_values(
                "created_at",
                ascending=False,
            ),
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# DEBUG AND CACHE CONTROLS
# =========================================================
with st.expander("🔧 Data and Debug Information"):
    st.write(
        "Locations file:",
        str(LOCATIONS_FILE),
    )
    st.write(
        "Total cities loaded:",
        len(locations_df),
    )
    st.write(
        "Cities in dropdown:",
        city_options,
    )
    st.write(
        "CSV columns:",
        locations_df.columns.tolist(),
    )

    if st.button("Clear cache and reload"):
        st.cache_data.clear()
        st.rerun()


st.caption(
    "PahadiSathi prototype — risk values are indicative "
    "and not an official warning system."
)
