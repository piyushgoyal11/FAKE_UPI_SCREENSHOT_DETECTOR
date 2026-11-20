import cv2
import numpy as np
from pathlib import Path


APP_REFERENCE_FOLDERS = {
    "googlepay": "gpay",
    "phonepe": "phonepe",
    "paytm": "paytm",
    "bhim": "bhim",
    "navi": "navi",
    "supermoney": "supermoney",
}

REFERENCE_FOLDER_APPS = {
    "gpay": "Google Pay",
    "phonepe": "PhonePe",
    "paytm": "Paytm",
    "bhim": "BHIM",
    "navi": "Navi",
    "supermoney": "super.money",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def find_app_reference(app_name, references_root):
    if not app_name:
        return None

    normalized_app = "".join(
        character
        for character in app_name.lower()
        if character.isalnum()
    )
    folder_name = APP_REFERENCE_FOLDERS.get(normalized_app)
    if folder_name is None:
        return None

    app_folder = Path(references_root) / folder_name
    if not app_folder.is_dir():
        return None

    references = sorted(
        path
        for path in app_folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )

    if len(references) == 1:
        return references[0]

    named_references = [
        path for path in references
        if "reference" in path.stem.lower()
    ]
    if len(named_references) == 1:
        return named_references[0]

    return None


def compare_all_references(image_path, references_root):
    image = cv2.imread(str(image_path))
    if image is None:
        return {
            "status": "ERROR",
            "message": "Screenshot could not be read",
            "best_reference": None,
            "comparisons": []
        }

    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image_gray = cv2.resize(image_gray, (360, 720))
    image_blur = cv2.GaussianBlur(image_gray, (9, 9), 0)
    image_edges = cv2.Canny(image_blur, 80, 160)

    comparisons = []
    root = Path(references_root)

    for folder_name, app_name in REFERENCE_FOLDER_APPS.items():
        app_folder = root / folder_name
        if not app_folder.is_dir():
            continue

        reference_paths = sorted(
            path
            for path in app_folder.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )

        for reference_path in reference_paths:
            reference = cv2.imread(str(reference_path))
            if reference is None:
                comparisons.append({
                    "app": app_name,
                    "reference": reference_path.name,
                    "status": "ERROR",
                    "message": "Reference image could not be read"
                })
                continue

            reference_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
            reference_gray = cv2.resize(reference_gray, (360, 720))
            reference_blur = cv2.GaussianBlur(
                reference_gray,
                (9, 9),
                0
            )
            difference = cv2.absdiff(image_blur, reference_blur)

            reference_edges = cv2.Canny(reference_blur, 80, 160)
            edge_difference = cv2.absdiff(image_edges, reference_edges)

            comparisons.append({
                "app": app_name,
                "reference": reference_path.name,
                "status": "ANALYZED",
                "difference_score": round(float(np.mean(difference)), 2),
                "edge_difference_percent": round(
                    float(np.mean(edge_difference) / 255 * 100),
                    2
                )
            })

    successful_comparisons = [
        result
        for result in comparisons
        if result["status"] == "ANALYZED"
    ]
    successful_comparisons.sort(
        key=lambda result: (
            result["edge_difference_percent"],
            result["difference_score"]
        )
    )

    return {
        "status": "ANALYZED" if successful_comparisons else "UNAVAILABLE",
        "message": (
            "Compared with all available app reference screenshots"
            if successful_comparisons
            else "No readable app reference screenshots were found"
        ),
        "best_reference": (
            successful_comparisons[0]
            if successful_comparisons
            else None
        ),
        "comparisons": successful_comparisons + [
            result
            for result in comparisons
            if result["status"] != "ANALYZED"
        ]
    }


def check_layout(image_path, reference_path):
    image_path = Path(image_path)
    reference_path = Path(reference_path)
    image = cv2.imread(str(image_path))
    reference = cv2.imread(str(reference_path))

    if image is None or reference is None:
        return {
            "status": "ERROR",
            "message": "Screenshot or selected app reference could not be read",
            "reference": str(reference_path)
        }

    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    reference_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)

    image_gray = cv2.resize(image_gray, (360, 720))
    reference_gray = cv2.resize(reference_gray, (360, 720))

    image_blur = cv2.GaussianBlur(image_gray, (9, 9), 0)
    reference_blur = cv2.GaussianBlur(reference_gray, (9, 9), 0)

    difference = cv2.absdiff(image_blur, reference_blur)

    difference_score = float(np.mean(difference))

    image_edges = cv2.Canny(image_blur, 80, 160)
    reference_edges = cv2.Canny(reference_blur, 80, 160)

    edge_difference = cv2.absdiff(image_edges, reference_edges)

    edge_score = float(np.mean(edge_difference) / 255 * 100)

    output_folder = image_path.resolve().parent / "processed"
    output_folder.mkdir(parents=True, exist_ok=True)

    cv2.imwrite(
        str(output_folder / "layout_difference.png"),
        difference
    )

    cv2.imwrite(
        str(output_folder / "edge_difference.png"),
        edge_difference
    )

    return {
        "status": "ANALYZED",
        "reference": reference_path.name,
        "difference_score": round(difference_score, 2),
        "edge_difference_percent": round(edge_score, 2),
        "message": "Layout comparison completed"
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    result = check_layout(
        root / "uploads" / "test_payment.png",
        root / "dataset" / "references" / "phonepe" / "reference.png"
    )

    for key, value in result.items():
        print(key, ":", value)