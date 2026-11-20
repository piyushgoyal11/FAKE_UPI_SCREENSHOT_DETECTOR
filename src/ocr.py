import easyocr
from pathlib import Path
import re
import sys

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from payment_validator import validate_payment

reader = easyocr.Reader(["en"], gpu=False)

def extract_payment_details(image_path):
    image_path = Path(image_path)

    if not image_path.exists():
        print("Error: Screenshot not found!")
        return {"error": "Screenshot not found"}

    results = reader.readtext(
        str(image_path),
        detail=1,
        paragraph=False,
        contrast_ths=0.1,
        adjust_contrast=0.7
    )

    print("\n===== UPI PAYMENT OCR =====")

    if not results:
        print("No text detected.")
        return {
            "status": "No text detected",
            "lines": [],
            "ocr_items": []
        }

    positioned = sorted(
        results,
        key=lambda item: (
            min(point[1] for point in item[0]),
            min(point[0] for point in item[0])
        )
    )

    lines = [str(text).strip() for _, text, confidence in positioned if str(text).strip()]

    for text in lines:
        print(text)

    full_text = "\n".join(lines)
    upi_match = re.search(r"\b[A-Za-z0-9._-]+@[A-Za-z][A-Za-z0-9.-]*\b", full_text)
    utr_match = re.search(r"\butr\s*[:\-]?\s*(\d{12})\b", full_text, re.I)
    phonepe_id_match = re.search(r"\bT\d{12,24}\b", full_text, re.I)
    time_match = re.search(r"\b([01]?\d|2[0-3])[:.][0-5]\d\s*(?:am|pm)?\b", full_text, re.I)
    date_match = re.search(r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b", full_text, re.I)

    amount_match = re.search(r"(?:₹|rs\.?|inr)\s*(\d[\d,.]*(?:\.\d{1,2})?)", full_text, re.I)
    amount = amount_match.group(1).replace(",", "") if amount_match else None

    extracted = {
        "status": "OCR extraction completed",
        "lines": lines,
        "ocr_items": [
            {
                "text": str(text),
                "confidence": round(float(confidence), 4),
                "box": [[int(x), int(y)] for x, y in box]
            }
            for box, text, confidence in positioned
        ],
        "amount": amount,
        "upi_id": upi_match.group(0) if upi_match else None,
        "utr": utr_match.group(1) if utr_match else None,
        "transaction_id": phonepe_id_match.group(0) if phonepe_id_match else None,
        "time": time_match.group(0) if time_match else None,
        "date": date_match.group(0) if date_match else None
    }

    try:
        payment = validate_payment(image_path)
        extracted.update({
            "payment_status": payment.get("status"),
            "recipient_name": payment.get("recipient_name"),
            "upi_id": payment.get("upi_id"),
            "transaction_id": payment.get("transaction_id"),
            "utr": payment.get("utr"),
            "debited_account": payment.get("debited_account"),
            "amount": payment.get("amount") or extracted["amount"],
            "date": payment.get("date") or extracted["date"],
            "time": payment.get("time"),
            "warnings": payment.get("warnings", [])
        })
    except Exception as error:
        extracted["payment_parse_error"] = str(error)

    print("\nOCR extraction completed!")
    return extracted


if __name__ == "__main__":
    extract_payment_details("uploads/test_payment.png")