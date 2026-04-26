# models/ — AI Model Ağırlık Dosyaları

Bu klasör Weli'nin eğittiği PyTorch model ağırlıklarını barındırır.

## Beklenen Dosya İsimleri

| Dosya Adı | Model | Açıklama |
|---|---|---|
| `yolov8_leaf.pt` | YOLOv8 | Yaprak tespiti modeli |
| `efficientnet_disease.pt` | EfficientNet-B3 | Hastalık sınıflandırma modeli |

## Kaydetme Formatı (Weli İçin)

### YOLOv8 (ultralytics)
```python
# Ultralytics YOLO otomatik olarak .pt formatında kaydeder.
# Eğitim sonrası: runs/detect/train/weights/best.pt
# Bu dosyayı alıp models/yolov8_leaf.pt olarak kopyala.
from ultralytics import YOLO
model = YOLO("runs/detect/train/weights/best.pt")
# Zaten hazır — kopyala yeter.
```

### EfficientNet-B3 (PyTorch)
```python
# Seçenek 1: Tam model kaydet (ÖNERİLEN)
torch.save(model, "models/efficientnet_disease.pt")

# Seçenek 2: Sadece ağırlıklar (state_dict)
torch.save(model.state_dict(), "models/efficientnet_disease.pt")
```

## Sınıf Listesini Güncelle

Eğer sınıf isimlerin aşağıdan farklıysa `app/core/model_manager.py` içindeki
`DEFAULT_CLASS_NAMES` listesini Weli'nin eğitim sırasındaki sırayla güncelle:

```python
DEFAULT_CLASS_NAMES: list[str] = [
    "Healthy",
    "Powdery Mildew",
    "Leaf Blight",
    ...
]
```

## Git Ignore

`.pt` dosyaları `.gitignore`'a eklenmiştir (boyutları çok büyük).
Takım üyeleri dosyaları doğrudan paylaşmalıdır (Google Drive, Hugging Face Hub, vb.).
