"""
split_dataset.py — Production-Level Stratified Dataset Splitter
================================================================
Sprint 1 - Step 3

Bu script, data/interim klasöründeki temizlenmiş veriyi
data/processed altında train / val / test olarak böler.

Mimari Kararlar:
    - Raw ve interim veriye DOKUNULMAZ (read-only). Sadece kopyalama yapılır.
    - Stratified split: Her sınıf AYRI AYRI bölünür, böylece class distribution korunur.
    - Reproducible: random.seed(42) ile her çalıştırmada aynı sonuç garanti edilir.
    - Idempotent: Tekrar çalıştırıldığında zaten kopyalanmış dosyalar atlanır.

Kullanım:
    python scripts/split_dataset.py
"""

import os
import sys
import shutil
import random

# ──────────────────────────────────────────────
# KONFİGÜRASYON
# ──────────────────────────────────────────────
SEED = 42                  # Reproducibility için sabit tohum değeri
TRAIN_RATIO = 0.75         # %75 eğitim
VAL_RATIO = 0.125          # %12.5 doğrulama
TEST_RATIO = 0.125         # %12.5 test
VALID_EXTENSIONS = ('.png', '.jpg', '.jpeg')

# ──────────────────────────────────────────────
# Step 3.1: Klasör Yapısını Oluştur
# ──────────────────────────────────────────────
def create_processed_dirs(processed_dir):
    """
    data/processed altında train, val, test ana klasörlerini oluşturur.
    Zaten varsa hata vermez (idempotent).
    """
    splits = ["train", "val", "test"]
    for split in splits:
        split_path = os.path.join(processed_dir, split)
        os.makedirs(split_path, exist_ok=True)
    print(f"[Step 3.1] Klasör yapısı hazır: {processed_dir}")
    for s in splits:
        print(f"           └── {s}/")

# ──────────────────────────────────────────────
# Step 3.2: Sınıfları Oku
# ──────────────────────────────────────────────
def get_classes(interim_dir):
    """
    interim klasöründeki tüm alt dizinleri (sınıfları) listeler.
    """
    classes = sorted([
        d for d in os.listdir(interim_dir)
        if os.path.isdir(os.path.join(interim_dir, d))
    ])
    print(f"\n[Step 3.2] Toplam {len(classes)} sınıf tespit edildi.")
    return classes

# ──────────────────────────────────────────────
# Step 3.3 & 3.4: Stratified + Reproducible Split
# ──────────────────────────────────────────────
def stratified_split(file_list, seed=SEED):
    """
    Tek bir sınıfa ait dosya listesini train/val/test olarak böler.

    Neden stratified?
        Eğer global (tüm dosyaları tek havuzda) split yapsaydık,
        az örnekli sınıflar test setinde hiç temsil edilmeyebilirdi.
        Stratified split her sınıfın oranını KORUR.

    Neden seed?
        Aynı script'i yarın çalıştırdığında aynı bölünmeyi alırsın.
        Bu, akademik makalelerde "reproducibility" olarak geçer
        ve peer review sürecinde zorunludur.
    """
    random.seed(seed)
    shuffled = file_list.copy()
    random.shuffle(shuffled)

    n = len(shuffled)
    train_end = int(n * TRAIN_RATIO)
    val_end = train_end + int(n * VAL_RATIO)

    train_files = shuffled[:train_end]
    val_files = shuffled[train_end:val_end]
    test_files = shuffled[val_end:]

    return train_files, val_files, test_files

# ──────────────────────────────────────────────
# Step 3.5: Dosyaları Kopyala
# ──────────────────────────────────────────────
def copy_files(file_list, src_dir, dst_dir):
    """
    Kaynak dizinden hedef dizine dosyaları kopyalar.
    Zaten kopyalanmış dosyaları atlar (idempotent).
    """
    os.makedirs(dst_dir, exist_ok=True)
    copied = 0
    skipped = 0

    for filename in file_list:
        src_path = os.path.join(src_dir, filename)
        dst_path = os.path.join(dst_dir, filename)

        if not os.path.exists(dst_path):
            shutil.copy2(src_path, dst_path)
            copied += 1
        else:
            skipped += 1

    return copied, skipped

# ──────────────────────────────────────────────
# ANA İŞ AKIŞI (PIPELINE)
# ──────────────────────────────────────────────
def run_split_pipeline(interim_dir, processed_dir):
    """
    Tüm adımları sırasıyla çalıştırır ve sonucu raporlar.
    """
    # Step 3.1
    create_processed_dirs(processed_dir)

    # Step 3.2
    classes = get_classes(interim_dir)

    # Sayaçlar (Step 3.6 raporu için)
    total_train, total_val, total_test = 0, 0, 0

    print(f"\n[Step 3.3-3.5] Stratified split ve kopyalama başlıyor (seed={SEED})...\n")
    print(f"{'Sınıf':<45} {'Train':>6} {'Val':>6} {'Test':>6} {'Toplam':>7}")
    print("-" * 75)

    for class_name in classes:
        class_src = os.path.join(interim_dir, class_name)

        # Sadece geçerli uzantılı görüntü dosyalarını al
        images = sorted([
            f for f in os.listdir(class_src)
            if f.lower().endswith(VALID_EXTENSIONS)
        ])

        if len(images) == 0:
            print(f"[Uyarı] {class_name} sınıfında görüntü bulunamadı, atlanıyor.")
            continue

        # Step 3.3 & 3.4: Split
        train_files, val_files, test_files = stratified_split(images)

        # Step 3.5: Kopyala
        train_dst = os.path.join(processed_dir, "train", class_name)
        val_dst = os.path.join(processed_dir, "val", class_name)
        test_dst = os.path.join(processed_dir, "test", class_name)

        copy_files(train_files, class_src, train_dst)
        copy_files(val_files, class_src, val_dst)
        copy_files(test_files, class_src, test_dst)

        total_train += len(train_files)
        total_val += len(val_files)
        total_test += len(test_files)

        print(f"{class_name:<45} {len(train_files):>6} {len(val_files):>6} {len(test_files):>6} {len(images):>7}")

    # ──────────────────────────────────────────
    # Step 3.6: Final Rapor
    # ──────────────────────────────────────────
    grand_total = total_train + total_val + total_test
    print("-" * 75)
    print(f"{'TOPLAM':<45} {total_train:>6} {total_val:>6} {total_test:>6} {grand_total:>7}")
    print()
    print("==================== ÖZET RAPOR ====================")
    print(f"  Train seti      : {total_train:>6} görüntü  ({total_train/grand_total*100:.1f}%)")
    print(f"  Validation seti : {total_val:>6} görüntü  ({total_val/grand_total*100:.1f}%)")
    print(f"  Test seti       : {total_test:>6} görüntü  ({total_test/grand_total*100:.1f}%)")
    print(f"  ─────────────────────────────────────")
    print(f"  Genel Toplam    : {grand_total:>6} görüntü")
    print(f"  Sınıf Sayısı    : {len(classes):>6}")
    print(f"  Seed            : {SEED}")
    print("====================================================")


if __name__ == "__main__":
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    INTERIM_DIR = os.path.join(PROJECT_ROOT, "data", "interim")
    PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

    if not os.path.exists(INTERIM_DIR):
        print(f"[Hata] Interim dizini bulunamadı: {INTERIM_DIR}")
        print("       Önce clean_dataset.py scriptini çalıştırın.")
        sys.exit(1)

    run_split_pipeline(INTERIM_DIR, PROCESSED_DIR)
