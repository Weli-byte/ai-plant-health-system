"""
app/ml/yolo_detector.py
=======================
YOLOv8 Leaf Detection ML Module.
Singleton pattern to ensure the model is loaded once.
"""

import os
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Union
from PIL import Image
from ultralytics import YOLO
from pathlib import Path

# Loglama yapılandırması
logger = logging.getLogger(__name__)

# Model yolu - backend/models/yolov8_leaf.pt
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
YOLO_MODEL_PATH = _BACKEND_ROOT / "models" / "yolov8_leaf.pt"

class YOLODetector:
    """YOLOv8 Singleton Detector Class."""
    _instance = None
    _model: Optional[YOLO] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(YOLODetector, cls).__new__(cls)
        return cls._instance

    def load_model(self):
        """Modeli diskten yükler. Çökme yapmaz, sadece is_loaded False kalır."""
        if self._model is not None:
            return

        # Path varlığını kontrol et
        if not YOLO_MODEL_PATH.exists():
            logger.warning(f"⚠️ YOLO model file not found at: {YOLO_MODEL_PATH}")
            self._model = None
            return

        try:
            logger.info(f"⏳ Loading YOLOv8 model from {YOLO_MODEL_PATH}...")
            # weights_only=False (ultralytics load safe default)
            self._model = YOLO(str(YOLO_MODEL_PATH))
            logger.info("✅ YOLOv8 model loaded successfully.")
        except Exception as exc:
            logger.error(f"❌ Error loading YOLOv8 model: {exc}")
            self._model = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def detect(self, image: Union[np.ndarray, Image.Image, str]) -> Dict[str, Any]:
        """
        Girdi görüntüsü üzerinde yaprak tespiti yapar.
        
        Returns:
            {
              "boxes": [[x1, y1, x2, y2]],
              "scores": [float],
              "classes": [string]
            }
        """
        if not self.is_loaded:
            raise RuntimeError("YOLO model is not loaded.")

        # Inference
        # conf=0.25 (yaprak tespiti için ideal güven eşiği)
        results = self._model.predict(image, conf=0.25, verbose=False)
        
        output = {
            "boxes": [],
            "scores": [],
            "classes": []
        }

        if len(results) > 0:
            result = results[0]
            for box in result.boxes:
                # Koordinatları al [x1, y1, x2, y2]
                coords = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]

                output["boxes"].append(coords)
                output["scores"].append(conf)
                output["classes"].append(cls_name)

        return output

# Singleton instance
yolo_detector = YOLODetector()
