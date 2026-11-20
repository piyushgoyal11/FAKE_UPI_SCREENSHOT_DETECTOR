import io
import sys
import uuid
import asyncio
import contextlib
import threading
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from detector import analyze_upi_screenshot

app = FastAPI(title="Pay Authentic AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

UPLOADS = ROOT / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000
DETECTOR_LOCK = threading.Lock()


@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Pay Authentic AI Backend Running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "Pay Authentic AI"
    }


def run_detector(image_path):
    output = io.StringIO()

    with DETECTOR_LOCK:
        with contextlib.redirect_stdout(output):
            detector_result = analyze_upi_screenshot(image_path)

    analysis = output.getvalue()

    if isinstance(detector_result, dict):
        return detector_result, analysis

    return None, analysis


def extract_verdict(detector_data, analysis):
    if detector_data is not None:
        value = str(
            detector_data.get("verdict", "UNVERIFIED")
        ).strip().upper()

        if value in {"SUSPICIOUS", "FAKE", "EDITED_LIKE"}:
            return "SUSPICIOUS"

        return "UNVERIFIED"

    for line in analysis.splitlines():
        clean_line = line.strip()

        if clean_line.lower().startswith("verdict:"):
            value = clean_line.split(":", 1)[1].strip().upper()

            if value in {"SUSPICIOUS", "FAKE", "EDITED_LIKE"}:
                return "SUSPICIOUS"

            return "UNVERIFIED"

    return "UNVERIFIED"


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    allowed_types = {
        "image/png": ".png",
        "image/jpeg": ".jpg"
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only PNG and JPEG images are supported"
        )

    image_path = None

    try:
        data = await file.read(MAX_FILE_SIZE + 1)

        if not data:
            raise HTTPException(
                status_code=400,
                detail="The uploaded image is empty"
            )

        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Maximum image size is 5 MB"
            )

        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {"PNG", "JPEG"}:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid image format"
                    )

                if image.width * image.height > MAX_PIXELS:
                    raise HTTPException(
                        status_code=413,
                        detail="Image dimensions are too large"
                    )

                image.verify()

        except (UnidentifiedImageError, OSError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is not a valid image"
            )

        image_path = UPLOADS / (
            uuid.uuid4().hex + allowed_types[file.content_type]
        )

        await asyncio.to_thread(image_path.write_bytes, data)

        detector_data, analysis = await asyncio.to_thread(
            run_detector,
            image_path
        )

        if "Payment analysis failed:" in analysis:
            raise RuntimeError("Detector reported an analysis failure")

        if "Image not found:" in analysis:
            raise RuntimeError("Detector could not read the screenshot")

        if detector_data is None:
            valid_headings = (
                "===== FINAL ANALYSIS RESULT =====",
                "===== ANALYSIS RESULT ====="
            )

            if not any(
                heading in analysis for heading in valid_headings
            ):
                raise RuntimeError("Incomplete detector output")

        verdict = extract_verdict(detector_data, analysis)

        return {
            "status": "success",
            "verdict": verdict,
            "payment": (
                detector_data.get("payment")
                if isinstance(detector_data, dict)
                else None
            ),
            "reference_comparison": (
                detector_data.get("reference_comparison")
                if isinstance(detector_data, dict)
                else None
            ),
            "reasons": (
                detector_data.get("reasons", [])
                if isinstance(detector_data, dict)
                else []
            ),
            "warnings": (
                detector_data.get("warnings", [])
                if isinstance(detector_data, dict)
                else []
            ),
            "analysis": analysis,
            "message": (
                "Screenshot analysis completed. "
                "A screenshot cannot verify payment receipt."
            )
        }

    except HTTPException:
        raise

    except Exception as error:
        print("Backend error:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Screenshot analysis failed. Check backend terminal."
        )

    finally:
        if image_path is not None:
            image_path.unlink(missing_ok=True)

        await file.close()