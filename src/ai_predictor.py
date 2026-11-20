from pathlib import Path
import sys

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from extract_features import extract_features

MODEL_PATH = ROOT / "models" / "upi_detector.pkl"

_model_bundle = None


def load_model():
    global _model_bundle

    if _model_bundle is None:
        _model_bundle = joblib.load(MODEL_PATH)

    return _model_bundle


def predict_screenshot(image_path):
    if not MODEL_PATH.exists():
        return {
            "status": "MODEL_NOT_FOUND",
            "prediction": None,
            "confidence": None
        }

    features = extract_features(image_path)

    if features is None:
        return {
            "status": "INVALID_IMAGE",
            "prediction": None,
            "confidence": None
        }

    saved = load_model()

    model = saved["model"]
    feature_names = list(saved["features"])

    missing_features = [
        name for name in feature_names
        if name not in features
    ]

    if missing_features:
        raise ValueError(
            f"Missing model features: {missing_features}"
        )

    values = pd.DataFrame(
        [{name: features[name] for name in feature_names}],
        columns=feature_names
    )

    prediction = int(model.predict(values)[0])
    probabilities = model.predict_proba(values)[0]

    predicted_index = list(model.classes_).index(prediction)
    confidence = float(probabilities[predicted_index] * 100)

    return {
        "status": "ANALYZED",
        "prediction": (
            "EDITED"
            if prediction == 1
            else "GENUINE_LIKE"
        ),
        "confidence": round(confidence, 2)
    }


if __name__ == "__main__":
    test_image = ROOT / "uploads" / "test_payment.png"

    result = predict_screenshot(test_image)

    print("\n===== AI ANALYSIS =====")
    print("Status:", result["status"])
    print("Prediction:", result["prediction"])
    print("Model Score:", result["confidence"])
    print("Demonstration model only")