from pathlib import Path

from payment_validator import validate_payment
from transaction_database import check_transaction
from layout_check import compare_all_references
from pixel_check import check_pixels
from ai_predictor import predict_screenshot

ROOT = Path(__file__).resolve().parent.parent
IMAGE_PATH = ROOT / "uploads" / "test_payment.png"


def analyze_upi_screenshot(image_path):
    image_path = Path(image_path)

    print("\n======================================")
    print("UPI SHIELD AI SCREENSHOT ANALYSIS")
    print("======================================")

    if not image_path.is_file():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    payment = validate_payment(image_path)

    if not isinstance(payment, dict):
        raise ValueError("Invalid payment validation result")

    print("\n===== OCR DEBUG =====")

    for line in payment.get("ocr_text", []):
        print(repr(line))

    print("\n===== EXTRACTED VALUES =====")
    print("Amount:", payment.get("amount"))
    print("Status:", payment.get("status"))

    print("\n===== PAYMENT DETAILS =====")
    print("Application:", payment.get("app") or "Not detected")
    print("Amount:", payment.get("amount") or "Not detected")
    print(
        "Transaction ID:",
        payment.get("transaction_id") or "Not detected"
    )
    print("Status:", payment.get("status") or "Not detected")
    print("Date:", payment.get("date") or "Not detected")
    print("Time:", payment.get("time") or "Not detected")
    print("Recipient:", payment.get("recipient_name") or "Not detected")
    print("UPI ID:", payment.get("upi_id") or "Not detected")
    print("UTR:", payment.get("utr") or "Not detected")
    print("Debited Account:", payment.get("debited_account") or "Not detected")

    reasons = list(payment.get("reasons") or [])
    warnings = list(payment.get("warnings") or [])

    transaction_id = payment.get("transaction_id")
    amount = payment.get("amount")
    app = payment.get("app")

    print("\n===== DATABASE ANALYSIS =====")

    if transaction_id:
        try:
            database_result = check_transaction(
                transaction_id,
                app,
                amount
            )

            print(database_result)

            if isinstance(database_result, dict):
                if database_result.get("reused"):
                    warnings.append(
                        "Transaction ID was previously scanned"
                    )

                if database_result.get("amount_changed"):
                    warnings.append(
                        "Local scan history contains a different amount"
                    )

        except Exception as error:
            print("Database analysis failed:", error)
            warnings.append("Database analysis unavailable")
    else:
        print("Skipped: Transaction ID unavailable")

    print("\n===== VISUAL FORENSIC ANALYSIS =====")

    try:
        pixel_result = check_pixels(image_path)
        print("\nPixel Analysis:")
        print(pixel_result)
    except Exception as error:
        print("Pixel analysis failed:", error)
        warnings.append("Pixel analysis unavailable")

    reference_root = ROOT / "dataset" / "references"
    try:
        layout_result = compare_all_references(
            image_path,
            reference_root
        )
        print("\nAll Reference Comparisons:")
        print(layout_result)

        if layout_result.get("status") != "ANALYZED":
            warnings.append(layout_result["message"])
        elif (
            app != "Unknown"
            and layout_result["best_reference"]["app"] != app
        ):
            warnings.append(
                "The closest visual reference differs from the app "
                "identified in the screenshot text"
            )
    except Exception as error:
        print("Reference comparison failed:", error)
        layout_result = {
            "status": "ERROR",
            "message": "Reference comparison unavailable",
            "best_reference": None,
            "comparisons": []
        }
        warnings.append("Reference comparison unavailable")

    print("\n===== AI MODEL ANALYSIS =====")

    try:
        ai_result = predict_screenshot(image_path)

        print("Status:", ai_result.get("status"))
        print("Prediction:", ai_result.get("prediction"))
        print("Model Score:", ai_result.get("confidence"))

        if ai_result.get("prediction") == "EDITED":
            warnings.append(
                "Experimental AI model flagged possible editing"
            )

    except Exception as error:
        print("AI analysis failed:", error)
        warnings.append("AI analysis unavailable")

    reasons = list(dict.fromkeys(str(x) for x in reasons))
    warnings = list(dict.fromkeys(str(x) for x in warnings))

    verdict = "SUSPICIOUS" if reasons else "UNVERIFIED"

    print("\n===== FINAL ANALYSIS RESULT =====")
    print("Verdict:", verdict)

    if reasons:
        print("\nReasons:")
        for reason in reasons:
            print("-", reason)

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print("-", warning)

    if not reasons and not warnings:
        print("No explicit inconsistencies detected")

    print("\nPayment authenticity is not verified.")
    print("Confirm receipt in the bank or UPI account.")
    print("AI model is experimental.")
    print("\nAnalysis completed!")

    return {
        "status": "ANALYZED",
        "verdict": verdict,
        "payment": {
            "app": app,
            "amount": amount,
            "transaction_id": transaction_id,
            "status": payment.get("status"),
            "date": payment.get("date"),
            "time": payment.get("time"),
            "recipient_name": payment.get("recipient_name"),
            "upi_id": payment.get("upi_id"),
            "utr": payment.get("utr"),
            "debited_account": payment.get("debited_account"),
            "ocr_text": payment.get("ocr_text", [])
        },
        "reference_comparison": layout_result,
        "reasons": reasons,
        "warnings": warnings
    }


if __name__ == "__main__":
    analyze_upi_screenshot(IMAGE_PATH)