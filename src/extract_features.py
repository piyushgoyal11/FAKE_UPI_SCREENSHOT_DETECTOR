import cv2
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "dataset"

APPS = [
    "gpay",
    "phonepe",
    "paytm",
    "bhim",
    "navi",
    "supermoney"
]

def extract_features(image_path):
    image = cv2.imread(str(image_path))

    if image is None:
        return None

    image = cv2.resize(image, (360, 720))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    noise = cv2.absdiff(gray, blur)
    edges = cv2.Canny(gray, 100, 200)

    laplacian = cv2.Laplacian(gray, cv2.CV_64F)

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    return {
        "sharpness": float(laplacian.var()),
        "noise_mean": float(np.mean(noise)),
        "noise_std": float(np.std(noise)),
        "edge_density": float(np.mean(edges > 0)),
        "brightness": float(np.mean(gray)),
        "contrast": float(np.std(gray)),
        "saturation": float(np.mean(hsv[:, :, 1])),
        "color_variation": float(np.std(image))
    }

records = []

for category, label in [("genuine", 0), ("edited", 1)]:
    for app in APPS:
        folder = DATASET / category / app

        if not folder.exists():
            continue

        for image_path in sorted(folder.rglob("*")):
            if image_path.suffix.lower() not in [
                ".png", ".jpg", ".jpeg"
            ]:
                continue

            features = extract_features(image_path)

            if features is None:
                print("Skipped:", image_path)
                continue

            record = {
                "image_path": str(image_path.relative_to(ROOT)),
                "app": app,
                "label": label,
                **features
            }

            records.append(record)

df = pd.DataFrame(records)

if df.empty:
    print("No valid images found.")
else:
    output_path = DATASET / "features.csv"
    df.to_csv(output_path, index=False)

    print("\n===== FEATURE EXTRACTION =====")
    print("Total Images:", len(df))
    print("Genuine:", sum(df["label"] == 0))
    print("Edited:", sum(df["label"] == 1))
    print("Features per Image:", 8)
    print("Saved:", output_path)

    print("\nImages by App:")
    print(pd.crosstab(df["app"], df["label"]))