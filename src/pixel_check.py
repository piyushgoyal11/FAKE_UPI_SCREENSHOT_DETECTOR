import cv2
import numpy as np
from pathlib import Path

def check_pixels(image_path):
    image = cv2.imread(str(image_path))

    if image is None:
        return {
            "status": "ERROR",
            "message": "Image could not be loaded"
        }

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    noise = cv2.absdiff(gray, blurred)

    noise_score = float(np.mean(noise))

    sharpness = float(
        cv2.Laplacian(gray, cv2.CV_64F).var()
    )

    noise_map = cv2.normalize(
        noise,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )

    output_folder = Path("uploads/processed")
    output_folder.mkdir(parents=True, exist_ok=True)

    cv2.imwrite(
        str(output_folder / "noise_map.png"),
        noise_map
    )

    return {
        "status": "ANALYZED",
        "noise_score": round(noise_score, 2),
        "sharpness_score": round(sharpness, 2),
        "message": "Pixel analysis completed"
    }


if __name__ == "__main__":
    result = check_pixels("uploads/test_payment.png")

    for key, value in result.items():
        print(key, ":", value)