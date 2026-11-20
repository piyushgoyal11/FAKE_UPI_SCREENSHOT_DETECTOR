from pathlib import Path
import cv2
import pandas as pd

DATASET = Path("dataset")

APPS = [
    "gpay",
    "phonepe",
    "paytm",
    "bhim",
    "navi",
    "supermoney"
]

records = []

for category, label in [("genuine", 0), ("edited", 1)]:
    for app in APPS:
        folder = DATASET / category / app

        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue

            if path.suffix.lower() not in [".png", ".jpg", ".jpeg"]:
                continue

            image = cv2.imread(str(path))

            if image is None:
                print("Cannot read:", path)
                continue

            height, width = image.shape[:2]

            records.append({
                "image_path": str(path),
                "app": app,
                "label": label,
                "category": category,
                "width": width,
                "height": height
            })

columns = [
    "image_path",
    "app",
    "label",
    "category",
    "width",
    "height"
]

df = pd.DataFrame(records, columns=columns)

DATASET.mkdir(exist_ok=True)

df.to_csv(DATASET / "metadata.csv", index=False)

print("\n===== DATASET SUMMARY =====")
print("Total Images:", len(df))
print("Genuine Images:", sum(df["label"] == 0))
print("Edited Images:", sum(df["label"] == 1))

if not df.empty:
    print("\nImages by Application:")
    print(pd.crosstab(df["app"], df["category"]))

print("\nDataset metadata saved successfully!") 