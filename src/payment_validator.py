import re
from datetime import datetime
from pathlib import Path

import easyocr

reader = None

APPS = {
    "Google Pay": ["google pay", "gpay"],
    "PhonePe": ["phonepe"],
    "Paytm": ["paytm"],
    "BHIM": ["bhim"],
    "Navi": ["navi"],
    "super.money": ["super.money", "super money"]
}

SUCCESS_PATTERNS = [
    r"\bpayment\s+successful\b",
    r"\bpaid\s+successfully\b",
    r"\btransaction\s+successful\b",
    r"\bpayment\s+complete(?:d)?\b",
    r"\bmoney\s+sent\b",
    r"\bpayment\s+sent\b",
    r"\bpayment\s+done\b",
    r"\bsuccessfully\s+paid\b",
    r"\btransaction\s+completed\b",
    r"\bpayment\s+success\b",
    r"\bsent\s+successfully\b"
]

FAILURE_PATTERNS = [
    r"\bpayment\s+failed\b",
    r"\btransaction\s+failed\b",
    r"\bpayment\s+declined\b",
    r"\btransaction\s+declined\b",
    r"\bpayment\s+unsuccessful\b"
]

def get_reader():
    global reader

    if reader is None:
        reader = easyocr.Reader(["en"], gpu=False)

    return reader


def normalize_amount(value):
    try:
        amount = float(value.replace(",", ""))

        if 0 < amount <= 10000000:
            return f"{amount:.2f}"

    except (ValueError, TypeError):
        pass

    return None


def extract_amount(lines):
    currency = r"(?:₹|rs\.?|inr)"
    number = r"(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d{1,7}(?:\.\d{1,2})?)"

    patterns = [
        rf"{currency}\s*{number}",
        rf"[?]\s*{number}",
        rf"\b(?:amount|total|paid|sent|payment)\s*(?:of|:|-)?\s*(?:{currency}\s*)?{number}"
    ]

    explicit_amounts = []
    for index, line in enumerate(lines):
        nearby = " ".join(lines[index:index + 2])

        for text in (line, nearby):
            for pattern in patterns:
                match = re.search(
                    pattern,
                    text,
                    re.IGNORECASE
                )

                if match:
                    amount = normalize_amount(match.group(1))

                    if amount is not None:
                        explicit_amounts.append(amount)

    if explicit_amounts:
        return explicit_amounts[0]

    # Avoid treating unrelated dates, IDs, or account numbers as amounts.
    # A bare number is only considered in the "paid to" amount block.
    paid_to_index = next(
        (i for i, line in enumerate(lines)
         if re.search(r"\bpaid\s+to\b", line, re.IGNORECASE)),
        None
    )
    if paid_to_index is None:
        return None

    amount_candidates = []
    stop_labels = re.compile(
        r"\b(?:payment details|debited from|utr|transaction\s*(?:id|no|number))\b",
        re.IGNORECASE
    )
    for index, line in enumerate(lines):
        if index < paid_to_index or index > paid_to_index + 5:
            continue
        if stop_labels.search(line):
            break

        candidate_text = line
        if index == paid_to_index:
            paid_to_match = re.search(r"\bpaid\s+to\b", line, re.IGNORECASE)
            candidate_text = line[paid_to_match.end():] if paid_to_match else ""

        candidates = (
            re.findall(r"(?<!\w)\d{1,7}(?:\.\d{1,2})?(?!\w)", candidate_text)
            if index == paid_to_index
            else [line.strip().replace(",", "")]
        )
        for normalized in candidates:
            if not re.fullmatch(r"\d{1,7}(?:\.\d{1,2})?", normalized):
                continue
            if len(normalized.split(".", 1)[0]) >= 3 and normalized[0] in "78":
                normalized = normalized[1:]
            amount = normalize_amount(normalized)
            if amount is not None:
                amount_candidates.append(amount)

    if amount_candidates:
        return amount_candidates[0]

    return None


def extract_transaction_id(lines):
    text = re.sub(r"\s+", " ", " ".join(lines))
    identifier = r"(?<![A-Z0-9])[A-Z0-9][A-Z0-9-]{5,31}(?![A-Z0-9])"
    transaction_labels = (
        r"\b(?:transaction|txn)\s*(?:id|number|no\.?)\b|"
        r"\b(?:reference|ref)\s*(?:number|no\.?|id)\b|"
        r"\bupi\s*(?:ref|reference|transaction\s*(?:id|number|no\.?))\b"
    )

    for label in re.finditer(transaction_labels, text, re.IGNORECASE):
        nearby = text[label.end():label.end() + 100]
        for match in re.finditer(identifier, nearby, re.IGNORECASE):
            if re.search(r"\d", match.group()):
                return match.group()

    for index, line in enumerate(lines):
        if not re.search(r"\b(?:transaction|txn|reference|ref)\b", line, re.I):
            continue
        if re.search(r"\b(?:successful|completed|failed|declined)\b", line, re.I):
            continue

        nearby = " ".join(lines[index:index + 4])
        for match in re.finditer(identifier, nearby, re.IGNORECASE):
            if re.search(r"\d", match.group()):
                return match.group()

    # Keep the UTR fallback for receipts that only show a UTR.
    utr_match = re.search(r"\butr\s*[:\-]?\s*(\d{12})\b", text, re.IGNORECASE)
    if utr_match:
        return utr_match.group(1)

    return None


def extract_payment_details(lines):
    text = "\n".join(lines)

    upi_id = None
    for line in lines:
        match = re.search(
            r"\b[A-Za-z0-9._-]+@[A-Za-z][A-Za-z0-9.-]*\b",
            line
        )
        if match:
            upi_id = match.group(0)
            break

    recipient_name = None
    paid_index = next(
        (i for i, line in enumerate(lines)
         if re.search(r"\bpaid\s+to\b", line, re.IGNORECASE)),
        None
    )
    if paid_index is not None:
        for line in lines[paid_index + 1:paid_index + 4]:
            if re.search(r"@[A-Za-z]", line) or re.fullmatch(r"[₹₹?]?\d+(?:\.\d{1,2})?", line):
                continue
            if line and not re.search(r"\b(?:payment details|paid to)\b", line, re.I):
                recipient_name = line
                break

    utr = None
    for line in lines:
        match = re.search(r"\butr\s*[:\-]?\s*(\d{12})\b", line, re.I)
        if match:
            utr = match.group(1)
            break

    account = None
    debited_index = next(
        (i for i, line in enumerate(lines)
         if re.search(r"\bdebited\s+from\b", line, re.IGNORECASE)),
        None
    )
    if debited_index is not None:
        for line in lines[debited_index + 1:debited_index + 4]:
            account_match = re.search(
                r"[X*x0-9]{4,}[*Xx0-9A-Za-z]*(?:\d{4})?",
                line
            )
            if account_match:
                account = account_match.group(0)
                break

    time_match = re.search(
        r"\b([01]?\d|2[0-3])[:.][0-5]\d\s*(?:am|pm)?\b",
        text,
        re.IGNORECASE
    )

    return {
        "recipient_name": recipient_name,
        "upi_id": upi_id,
        "utr": utr,
        "debited_account": account,
        "time": time_match.group(0) if time_match else None,
    }


def extract_date(text):
    patterns = [
        (r"\b\d{1,2}/\d{1,2}/\d{4}\b", "%d/%m/%Y"),
        (r"\b\d{1,2}-\d{1,2}-\d{4}\b", "%d-%m-%Y"),
        (r"\b\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\b", "%d %b %Y"),
        (r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b", "%d %B %Y")
    ]

    for pattern, date_format in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            candidate = match.group()

            try:
                parsed_date = datetime.strptime(
                    candidate,
                    date_format
                )

                return candidate, parsed_date, None

            except ValueError:
                return candidate, None, "Invalid payment date"

    return None, None, "Payment date not detected"


def validate_payment(image_path):
    image_path = Path(image_path)

    if not image_path.is_file():
        raise FileNotFoundError("Screenshot not found")

    ocr_reader = get_reader()

    results = ocr_reader.readtext(
        str(image_path),
        detail=0,
        paragraph=False
    )

    lines = [
        str(line).strip()
        for line in results
        if str(line).strip()
    ]

    text = "\n".join(lines)
    lower_text = text.lower()

    warnings = []
    reasons = []

    app_name = "Unknown"

    for app, keywords in APPS.items():
        if any(keyword in lower_text for keyword in keywords):
            app_name = app
            break

    amount = extract_amount(lines)
    transaction_id = extract_transaction_id(lines)
    payment_details = extract_payment_details(lines)

    success_detected = any(
        re.search(pattern, lower_text)
        for pattern in SUCCESS_PATTERNS
    )

    failure_detected = any(
        re.search(pattern, lower_text)
        for pattern in FAILURE_PATTERNS
    )

    if success_detected and failure_detected:
        status = "Conflicting status text"
        reasons.append(
            "Both successful and failed payment text detected"
        )

    elif failure_detected:
        status = "Failure text detected"
        warnings.append(
            "Screenshot displays a failed payment"
        )

    elif success_detected:
        status = "Success text detected"

    else:
        status = "Unknown"
        warnings.append(
            "Payment status could not be identified"
        )

    timestamp, parsed_date, date_warning = extract_date(text)

    if date_warning:
        warnings.append(date_warning)

    if parsed_date is not None:
        if parsed_date.date() > datetime.now().date():
            warnings.append(
                "Future payment date detected"
            )

    if transaction_id is None:
        warnings.append(
            "Transaction ID not detected"
        )

    if amount is None:
        warnings.append(
            "Payment amount not detected"
        )

    if app_name == "Unknown":
        warnings.append(
            "UPI application not identified"
        )

    if not lines:
        warnings.append(
            "No readable text found in screenshot"
        )

    return {
        "app": app_name,
        "amount": amount,
        "transaction_id": transaction_id,
        "status": status,
        "date": timestamp,
        "timestamp": timestamp,
        "time": payment_details["time"],
        "recipient_name": payment_details["recipient_name"],
        "upi_id": payment_details["upi_id"],
        "utr": payment_details["utr"],
        "debited_account": payment_details["debited_account"],
        "valid": None,
        "reasons": reasons,
        "warnings": warnings,
        "ocr_text": lines
    }