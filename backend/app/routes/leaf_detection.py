"""
app/routes/leaf_detection.py
============================
Leaf detection endpoint using YOLOv8.
"""

import cv2
import numpy as np
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.services.leaf_detection_service import detect_leaf
from app.schemas.leaf_detection_schemas import LeafDetectionResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2",
    tags=["AI Leaf Detection — Extension"],
)

@router.post(
    "/detect_leaf",
    response_model=LeafDetectionResponse,
    summary="Detect leaf regions in an uploaded image",
    responses={
        200: {"description": "Detection successful"},
        400: {"description": "Invalid image format"},
        503: {"description": "YOLO model not loaded"}
    }
)
async def leaf_detection_endpoint(file: UploadFile = File(...)):
    """
    Accepts an image file and returns detected leaf bounding boxes.
    
    Returns 503 if the YOLO model file is missing.
    Returns 400 if the image cannot be processed.
    """
    # 1. MIME tipi kontrolü
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File provided is not an image."
        )

    try:
        # 2. Görüntü verisini oku ve OpenCV formatına dönüştür
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Could not decode image. Please ensure it is a valid JPEG/PNG.")

        # 3. Servis katmanını çağır
        results = detect_leaf(img)

        # 4. Yanıtı döndür
        return LeafDetectionResponse(
            success=True,
            boxes=results["boxes"],
            scores=results["scores"],
            classes=results["classes"],
            count=len(results["boxes"]),
            message="Detection completed successfully."
        )

    except FileNotFoundError as exc:
        # Model dosyası eksik hatası (Service katmanından gelir)
        logger.error(f"503 Service Unavailable: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YOLO model not found. Ensure 'yolov8_leaf.pt' exists in 'backend/models/'"
        )
    except ValueError as exc:
        # Geçersiz görüntü hatası
        logger.error(f"400 Bad Request: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        # Beklenmedik hatalar
        logger.error(f"500 Internal Server Error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(exc)}"
        )
    finally:
        await file.close()
