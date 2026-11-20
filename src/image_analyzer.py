import cv2
from pathlib import Path

def analyze_image(image_path):
    image = cv2.imread(str(image_path))

    if image is None:
        print("Error: Could not read image!")
        return

    height, width = image.shape[:2]

    print("\n===== UPI IMAGE ANALYSIS =====")
    print("Image Width:", width)
    print("Image Height:", height)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    edges = cv2.Canny(gray, 100, 200)

    sharpness = cv2.Laplacian(
        gray, cv2.CV_64F
    ).var()

    print("Image Sharpness:", round(sharpness, 2))

    output_folder = Path("uploads/processed")
    output_folder.mkdir(parents=True, exist_ok=True)

    cv2.imwrite(
        str(output_folder / "grayscale.png"),
        gray
    )

    cv2.imwrite(
        str(output_folder / "edges.png"),
        edges
    )

    print("Image analysis completed!")
    print("Processed images saved successfully!")


if __name__ == "__main__":
    image_path = Path("uploads/test_payment.png")
    analyze_image(image_path)