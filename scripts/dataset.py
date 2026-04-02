"""
dataset.py — Production-Level PyTorch Dataset & DataLoader Pipeline
====================================================================
Sprint 1 - Step 4

Bu modül, processed veriyi PyTorch modeline besleyecek tüm bileşenleri içerir:
    - PlantDiseaseDataset  : Custom PyTorch Dataset class
    - get_transforms()     : Albumentations tabanlı augmentation pipeline
    - get_dataloaders()    : Train / Val / Test DataLoader factory
    - LabelEncoder         : Sınıf isimleri ↔ integer mapping

Mimari Kararlar:
    - Lazy Loading: Görüntüler RAM'e toplu yüklenmez, __getitem__ anında diskten okunur.
    - Train vs Val/Test Transform Ayrımı: Augmentation SADECE train setine uygulanır.
    - Albumentations: torchvision.transforms yerine kullanılır çünkü ~2x daha hızlıdır
      ve OpenCV tabanlıdır (NumPy native).

Kullanım:
    python scripts/dataset.py
"""

import os
import sys
import cv2
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import albumentations as A
from albumentations.pytorch import ToTensorV2


# ══════════════════════════════════════════════════════════
# Step 4.2: Label Encoder
# ══════════════════════════════════════════════════════════
class LabelEncoder:
    """
    Sınıf isimlerini tutarlı integer label'lara çevirir.

    Neden ayrı bir class?
        - Train, val ve test setlerinin AYNI encoding'i kullanması ZORUNLU.
        - Eğer her set kendi sırasıyla label atarsa, "Tomato = 3" train'de
          "Tomato = 7" test'te olabilir → model çöp sonuç verir.
        - Bu class tek bir kaynak (single source of truth) sağlar.
    """

    def __init__(self, class_names: list):
        """
        Args:
            class_names: Sıralı sınıf isimleri listesi
        """
        self.class_names = sorted(class_names)
        self.class_to_idx = {name: idx for idx, name in enumerate(self.class_names)}
        self.idx_to_class = {idx: name for name, idx in self.class_to_idx.items()}

    def encode(self, class_name: str) -> int:
        return self.class_to_idx[class_name]

    def decode(self, idx: int) -> str:
        return self.idx_to_class[idx]

    def __len__(self):
        return len(self.class_names)


# ══════════════════════════════════════════════════════════
# Step 4.3: Albumentations Transform Pipeline
# ══════════════════════════════════════════════════════════
def get_transforms(mode: str = "train"):
    """
    Modüler Albumentations transform pipeline döndürür.

    Args:
        mode: "train" veya "val" / "test"

    TRAIN pipeline'ında augmentation var çünkü:
        - Model aynı görüntüyü her epoch'ta farklı görsün → overfitting azalır
        - Gerçek dünyada fotoğraflar farklı açılardan, farklı ışıkta çekilir
        - Augmentation bu varyasyonları simüle eder

    VAL/TEST pipeline'ında augmentation YOK çünkü:
        - Değerlendirme sırasında modelin gerçek performansını ölçmek istiyoruz
        - Augmentation sonucu değiştirirse, metrikler güvenilmez olur

    Normalize değerleri:
        ImageNet ortalaması ve standart sapması kullanılıyor (0.485, 0.456, 0.406 / 0.229, 0.224, 0.225).
        Neden? Çünkü Sprint 2'de transfer learning ile ImageNet üzerinde pretrained
        bir model (ResNet, EfficientNet vb.) kullanacağız. Modelin beklediği dağılıma
        uygun normalize etmeliyiz.
    """
    # ImageNet istatistikleri (transfer learning standardı)
    IMAGENET_MEAN = [0.485, 0.456, 0.406]
    IMAGENET_STD = [0.229, 0.224, 0.225]

    if mode == "train":
        return A.Compose([
            A.Resize(224, 224),                          # Sabit boyut (model giriş boyutu)
            A.HorizontalFlip(p=0.5),                     # Yatay çevirme (%50 olasılık)
            A.RandomBrightnessContrast(                   # Parlaklık & kontrast değişimi
                brightness_limit=0.2,
                contrast_limit=0.2,
                p=0.3
            ),
            A.Rotate(limit=15, p=0.3),                   # ±15° döndürme
            A.GaussianBlur(blur_limit=(3, 5), p=0.1),    # Hafif bulanıklaştırma
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),                                 # HWC NumPy → CHW Tensor
        ])
    else:
        return A.Compose([
            A.Resize(224, 224),
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),
        ])


# ══════════════════════════════════════════════════════════
# Step 4.1 & 4.4: Custom PyTorch Dataset Class
# ══════════════════════════════════════════════════════════
class PlantDiseaseDataset(Dataset):
    """
    PyTorch Dataset subclass — Bitki hastalığı görüntülerini lazy-load eder.

    Lazy Loading Neden Önemli?
        40.000 görüntüyü 224x224x3 olarak RAM'e yüklesek:
        40000 * 224 * 224 * 3 bytes ≈ 17.9 GB RAM → Sistem çöker.
        Lazy loading ile sadece o anki batch'teki görüntüler okunur.

    Yapı:
        __init__  → Dosya yollarını ve label'ları TARAR (hafif operasyon)
        __len__   → Toplam örnek sayısını döndürür
        __getitem__ → İstenilen index'teki görüntüyü diskten okur ve transform uygular
    """

    def __init__(self, data_dir: str, label_encoder: LabelEncoder, transform=None):
        """
        Args:
            data_dir      : processed/train veya processed/val veya processed/test yolu
            label_encoder : Tüm setlerde AYNI encoder kullanılmalı
            transform     : Albumentations Compose nesnesi
        """
        self.data_dir = data_dir
        self.label_encoder = label_encoder
        self.transform = transform

        # Dosya yollarını ve label'ları tara (sadece path string'leri — RAM dostu)
        self.image_paths = []
        self.labels = []
        self._scan_directory()

    def _scan_directory(self):
        """
        Klasör yapısını tarar ve her görüntünün yolunu + label'ını kaydeder.
        Geçersiz dosyaları atlar.
        """
        valid_ext = ('.png', '.jpg', '.jpeg')

        for class_name in sorted(os.listdir(self.data_dir)):
            class_path = os.path.join(self.data_dir, class_name)
            if not os.path.isdir(class_path):
                continue

            label = self.label_encoder.encode(class_name)

            for img_name in os.listdir(class_path):
                if img_name.lower().endswith(valid_ext):
                    full_path = os.path.join(class_path, img_name)
                    self.image_paths.append(full_path)
                    self.labels.append(label)

    def __len__(self) -> int:
        """DataLoader'ın kaç iterasyon yapacağını bilmesi için zorunlu."""
        return len(self.image_paths)

    def __getitem__(self, idx: int):
        """
        Tek bir örneği diskten yükler, transform uygular ve döndürür.

        OpenCV neden kullanılıyor?
            - Albumentations, OpenCV (NumPy array) formatında çalışır.
            - PIL'e göre büyük dosyalarda ~1.5x daha hızlıdır.

        BGR → RGB dönüşümü neden yapılıyor?
            - OpenCV varsayılan olarak BGR formatında okur.
            - PyTorch modelleri ve ImageNet normalizasyonu RGB bekler.
        """
        img_path = self.image_paths[idx]
        label = self.labels[idx]

        # Görüntüyü diskten oku (BGR)
        image = cv2.imread(img_path)

        if image is None:
            raise ValueError(f"Görüntü okunamadı: {img_path}")

        # BGR → RGB dönüşümü
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Albumentations transform uygula
        if self.transform:
            augmented = self.transform(image=image)
            image = augmented["image"]  # Artık torch.Tensor (CHW formatında)

        return image, label


# ══════════════════════════════════════════════════════════
# Step 4.5 & 4.6: DataLoader Factory
# ══════════════════════════════════════════════════════════
def get_dataloaders(processed_dir: str, batch_size: int = 32, num_workers: int = 0):
    """
    Train, validation ve test DataLoader'larını tek çağrıyla oluşturur.

    Args:
        processed_dir : data/processed dizini
        batch_size    : Her iterasyonda modele verilen örnek sayısı.
                        32 iyi bir başlangıç değeri (GPU belleğine göre ayarlanır).
        num_workers   : Veri yükleme için paralel process sayısı.
                        Windows'ta 0 kullan (multiprocessing sorunu yaşanabilir).
                        Linux/Mac'te CPU çekirdek sayısının yarısı iyi bir değer.

    Shuffle Mantığı:
        - Train: shuffle=True  → Her epoch'ta farklı sıra → model ezberlemesin
        - Val:   shuffle=False → Değerlendirme tutarlı olsun
        - Test:  shuffle=False → Nihai rapor tekrarlanabilir olsun

    Returns:
        (train_loader, val_loader, test_loader, label_encoder)
    """
    train_dir = os.path.join(processed_dir, "train")
    val_dir = os.path.join(processed_dir, "val")
    test_dir = os.path.join(processed_dir, "test")

    # Label Encoder: TÜM setler için TEK encoder (train klasöründen oluşturuluyor)
    class_names = sorted([
        d for d in os.listdir(train_dir)
        if os.path.isdir(os.path.join(train_dir, d))
    ])
    label_encoder = LabelEncoder(class_names)

    # Dataset'leri oluştur (her birine uygun transform veriliyor)
    train_dataset = PlantDiseaseDataset(train_dir, label_encoder, transform=get_transforms("train"))
    val_dataset = PlantDiseaseDataset(val_dir, label_encoder, transform=get_transforms("val"))
    test_dataset = PlantDiseaseDataset(test_dir, label_encoder, transform=get_transforms("test"))

    # DataLoader'ları oluştur
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,           # EĞİTİMDE KARISTIR
        num_workers=num_workers,
        pin_memory=True,        # GPU'ya veri transferini hızlandırır
        drop_last=True          # Son eksik batch'i at (BatchNorm kararlılığı için)
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,          # DEĞERLENDİRMEDE KARIŞTIRMA
        num_workers=num_workers,
        pin_memory=True,
        drop_last=False
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,          # TESTTE KARIŞTIRMA
        num_workers=num_workers,
        pin_memory=True,
        drop_last=False
    )

    return train_loader, val_loader, test_loader, label_encoder


# ══════════════════════════════════════════════════════════
# Step 4.7: Doğrulama Testi (Verification)
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

    if not os.path.exists(PROCESSED_DIR):
        print(f"[Hata] Processed dizini bulunamadı: {PROCESSED_DIR}")
        sys.exit(1)

    print("=" * 60)
    print("  PIPELINE DOĞRULAMA TESTİ")
    print("=" * 60)

    # DataLoader'ları oluştur
    train_loader, val_loader, test_loader, label_encoder = get_dataloaders(
        PROCESSED_DIR, batch_size=32, num_workers=0
    )

    # ─── Dataset Boyutları ───
    print(f"\n[Dataset Boyutları]")
    print(f"  Train      : {len(train_loader.dataset):>6} görüntü")
    print(f"  Validation : {len(val_loader.dataset):>6} görüntü")
    print(f"  Test       : {len(test_loader.dataset):>6} görüntü")

    # ─── Label Encoding Tablosu ───
    print(f"\n[Label Encoding] ({len(label_encoder)} sınıf)")
    for idx in range(len(label_encoder)):
        print(f"  {idx:>2} → {label_encoder.decode(idx)}")

    # ─── Bir Batch Çek ve Kontrol Et ───
    print(f"\n[Batch Testi]")
    images, labels = next(iter(train_loader))

    print(f"  images.shape  : {images.shape}")    # Beklenen: [32, 3, 224, 224]
    print(f"  images.dtype  : {images.dtype}")     # Beklenen: torch.float32
    print(f"  labels.shape  : {labels.shape}")     # Beklenen: [32]
    print(f"  labels.dtype  : {labels.dtype}")     # Beklenen: torch.int64
    print(f"  pixel min     : {images.min().item():.4f}")
    print(f"  pixel max     : {images.max().item():.4f}")
    print(f"  İlk 8 label   : {labels[:8].tolist()}")
    print(f"  İlk 8 sınıf   : {[label_encoder.decode(l.item()) for l in labels[:8]]}")

    # ─── Batch Sayıları ───
    print(f"\n[DataLoader Batch Sayıları]")
    print(f"  Train batches : {len(train_loader)}")
    print(f"  Val batches   : {len(val_loader)}")
    print(f"  Test batches  : {len(test_loader)}")

    print(f"\n{'=' * 60}")
    print(f"  ✔ Pipeline doğrulaması BAŞARILI!")
    print(f"  ✔ Sistem model eğitimine HAZIR.")
    print(f"{'=' * 60}")
