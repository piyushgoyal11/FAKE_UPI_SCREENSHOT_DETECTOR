from pathlib import Path
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parent.parent

data = pd.read_csv(ROOT / "dataset" / "features.csv")

features = [
    "sharpness",
    "noise_mean",
    "noise_std",
    "edge_density",
    "brightness",
    "contrast",
    "saturation",
    "color_variation"
]

X = data[features]
y = data["label"]

if len(data) < 2 or y.nunique() < 2:
    raise ValueError("Both genuine and edited images are required")

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
    class_weight="balanced"
)

model.fit(X, y)

model_path = ROOT / "models" / "upi_detector.pkl"
model_path.parent.mkdir(exist_ok=True)

joblib.dump({
    "model": model,
    "features": features
}, model_path)

print("\n===== MODEL TRAINING =====")
print("Training Images:", len(data))
print("Features:", len(features))
print("Model:", "Random Forest")
print("Saved:", model_path)
print("Training completed!")