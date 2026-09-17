from pathlib import Path
import joblib

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "risk_model.pkl"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

bundle = {
    "model_type": "rule_based_prototype",
    "version": "1.0",
    "features": [
        "rainfall_24h",
        "rainfall_7d",
        "slope",
        "elevation",
        "soil_moisture",
        "road_distance",
        "previous_landslide",
    ],
}

joblib.dump(bundle, MODEL_PATH)

print(f"Model saved successfully to: {MODEL_PATH}")