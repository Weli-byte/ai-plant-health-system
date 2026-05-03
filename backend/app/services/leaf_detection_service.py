"""
app/services/leaf_detection_service.py
======================================
Unified Service layer for leaf detection.
Supports both Sprint 2 (Analysis Page) and Sprint 4 (Modular API).
"""

import io
import base64
import logging
import cv2
import numpy as np
from PIL import Image
from typing import Dict, Any, Optional, Union
from app.ml.yolo_detector import yolo_detector

logger = logging.getLogger(__name__)

def _to_pil(image_source: Union[bytes, np.ndarray]) -> Image.Image:
    """Helper to convert various image sources to PIL."""
    if isinstance(image_source, bytes):
        return Image.open(io.BytesIO(image_source)).convert("RGB")
    return Image.fromarray(cv2.cvtColor(image_source, cv2.COLOR_BGR2RGB))

def _to_base64(image: Image.Image) -> str:
    """Helper to convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.read()).decode("utf-8")

def detect_leaf(
    image_data: Optional[np.ndarray] = None,      # For Sprint 4 Route
    image_bytes: Optional[bytes] = None,          # For Sprint 2 Route (Analyze Page)
    yolo_model: Optional[Any] = None,             # Legacy compatibility
    confidence_threshold: float = 0.25            # Legacy compatibility
) -> Dict[str, Any]:
    """
    Unified leaf detection service.
    
    Returns a dictionary compatible with both Sprint 2 and Sprint 4 schemas.
    """
    # 1. Model Check
    if not yolo_detector.is_loaded:
        yolo_detector.load_model()
        if not yolo_detector.is_loaded:
            raise FileNotFoundError("YOLO model not found in models/yolov8_leaf.pt")

    # 2. Source Preparation
    try:
        source = image_data if image_data is not None else image_bytes
        if source is None:
            raise ValueError("No image data provided.")
        
        # We need a numpy array for YOLO and a PIL image for cropping
        if isinstance(source, bytes):
            nparr = np.frombuffer(source, np.uint8)
            cv2_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            pil_img = Image.open(io.BytesIO(source)).convert("RGB")
        else:
            cv2_img = source
            pil_img = Image.fromarray(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
            
        h, w = cv2_img.shape[:2]
    except Exception as exc:
        logger.error(f"Image processing error: {exc}")
        raise ValueError(f"Invalid image format: {exc}")

    # 3. Inference
    try:
        raw_results = yolo_detector.detect(cv2_img)
    except Exception as exc:
        logger.error(f"YOLO detection error: {exc}")
        raise RuntimeError(f"Model inference failed: {exc}")

    # 4. Process Results (Sprint 2 format: Single Best Detection)
    leaf_detected = len(raw_results["boxes"]) > 0
    best_box = None
    best_score = 0.0
    cropped_b64 = None

    if leaf_detected:
        # Find best confidence box
        best_idx = np.argmax(raw_results["scores"])
        best_box = raw_results["boxes"][best_idx] # [x1, y1, x2, y2]
        best_score = raw_results["scores"][best_idx]
        
        # Crop for Sprint 2
        try:
            crop = pil_img.crop((best_box[0], best_box[1], best_box[2], best_box[3]))
            cropped_b64 = _to_base64(crop)
        except Exception as exc:
            logger.warning(f"Cropping failed: {exc}")

    # 5. Combined Response (Compatible with both Sprint 2 and Sprint 4)
    return {
        # Sprint 4 fields
        "boxes": raw_results["boxes"],
        "scores": raw_results["scores"],
        "classes": raw_results["classes"],
        
        # Sprint 2 fields (ai_detection.py)
        "leaf_detected": leaf_detected,
        "bounding_box": best_box,
        "confidence": best_score,
        "cropped_leaf_base64": cropped_b64,
        "original_width": w,
        "original_height": h
    }
