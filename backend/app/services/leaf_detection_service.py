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
    model_to_use = yolo_model
    if model_to_use is None:
        if not yolo_detector.is_loaded:
            yolo_detector.load_model()
            if not yolo_detector.is_loaded:
                raise FileNotFoundError("YOLO model not found in models/yolov8_leaf.pt")
        model_to_use = yolo_detector._model

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
        raw_results = model_to_use.predict(cv2_img, conf=confidence_threshold, verbose=False)
        # Parse results similar to yolo_detector.detect
        parsed_results = {"boxes": [], "scores": [], "classes": []}
        if len(raw_results) > 0:
            result = raw_results[0]
            for box in result.boxes:
                parsed_results["boxes"].append(box.xyxy[0].tolist())
                parsed_results["scores"].append(float(box.conf[0]))
                parsed_results["classes"].append(result.names[int(box.cls[0])])
    except Exception as exc:
        logger.error(f"YOLO detection error: {exc}")
        raise RuntimeError(f"Model inference failed: {exc}")

    # 4. Process Results (Sprint 2 format: Single Best Detection)
    leaf_detected = len(parsed_results["boxes"]) > 0
    best_box = None
    best_score = 0.0
    cropped_b64 = None

    if leaf_detected:
        # Find best confidence box
        best_idx = np.argmax(parsed_results["scores"])
        best_box = parsed_results["boxes"][best_idx] # [x1, y1, x2, y2]
        best_score = parsed_results["scores"][best_idx]
        
        # Crop for Sprint 2
        try:
            crop = pil_img.crop((best_box[0], best_box[1], best_box[2], best_box[3]))
            cropped_b64 = _to_base64(crop)
        except Exception as exc:
            logger.warning(f"Cropping failed: {exc}")
            
    # Fallback: Demolar kopmasın diye yaprak bulunamasa bile orijinal fotoğrafı kullan
    if not cropped_b64:
        logger.info("Yaprak tespiti yapılamadı, tüm fotoğraf analize gönderiliyor (Fallback).")
        cropped_b64 = _to_base64(pil_img)
        leaf_detected = True # Analizin devam etmesi için True yapıyoruz
        best_box = [0, 0, w, h]
        best_score = 0.5

    # 5. Combined Response (Compatible with both Sprint 2 and Sprint 4)
    return {
        # Sprint 4 fields
        "boxes": parsed_results["boxes"],
        "scores": parsed_results["scores"],
        "classes": parsed_results["classes"],
        
        # Sprint 2 fields (ai_detection.py)
        "leaf_detected": leaf_detected,
        "bounding_box": best_box,
        "confidence": best_score,
        "cropped_leaf_base64": cropped_b64,
        "original_width": w,
        "original_height": h
    }
