import os
import sys
import shutil

# Kullanıcının belirlediği, eğitime dahil edilecek bitki listesi
TARGET_PLANTS = [
    "Apple", "Grape", "Strawberry", "Tomato", "Peach", 
    "Potato", "Pepper_bell", "Corn", "Cherry", "Blueberry"
]

def get_actual_raw_dir(base_raw_dir):
    """
    Step 2.2.1: İç içe 'PlantVillage' klasörü problemini tespit eder ve okuma yapılacak kök dizini döndürür.
    """
    nested_dir = os.path.join(base_raw_dir, 'PlantVillage')
    if os.path.exists(nested_dir) and os.path.isdir(nested_dir):
        return nested_dir
    return base_raw_dir

def filter_and_copy_data(source_dir, interim_dir):
    """
    Step 2.2.2 - 2.2.4: Klasör isimlerini parse eder, hedeflenen bitkileri bulur 
    ve raw veriye dokunmadan yeni interim klasörüne (aynı iç yapı ile) kopyalar.
    """
    if not os.path.exists(interim_dir):
        os.makedirs(interim_dir)
        print(f"[Bilgi] Yeni ana dizin oluşturuldu: {interim_dir}")

    all_classes = [d for d in os.listdir(source_dir) if os.path.isdir(os.path.join(source_dir, d))]
    
    selected_classes = []
    total_images_copied = 0

    print(f"\n--- Filtreleme ve Kopyalama İşlemi Başlatılıyor ---")
    
    for class_name in all_classes:
        # Step 2.2.2: Adı parse et. Örnek: "Tomato___Early_blight" -> "Tomato"
        # Not: PlantVillage isimlendirmesinde "___" üç çizgi ile ayrıldığı varsayılıyor.
        plant_prefix = class_name.split("___")[0]
        
        # "Cherry_(including_sour)" veya "Pepper,_bell" gibi PlantVillage'a özgü variesyonları 
        # güvenli (robust) bir şekilde yakalayabilmek için substring araması yapıyoruz.
        matched_target = None
        for target in TARGET_PLANTS:
            # Virgülleri kaldırıp küçük harfle temiz bir karşılaştırma yapıyoruz.
            cleaned_prefix = plant_prefix.lower().replace(",", "")
            cleaned_target = target.lower().replace(",", "")
            
            if cleaned_target in cleaned_prefix:
                matched_target = target
                break
                
        # Eğer bu sınıf aranan 10 bitkiden biri ise işleme al:
        if matched_target:
            selected_classes.append(class_name)
            
            src_class_path = os.path.join(source_dir, class_name)
            dst_class_path = os.path.join(interim_dir, class_name)
            
            # Alt klasör yapısını aynı tutarak oluştur (Step 2.2.3 / 2.2.4)
            if not os.path.exists(dst_class_path):
                os.makedirs(dst_class_path)
            
            # Görüntüleri listele ve kopyala
            images = [img for img in os.listdir(src_class_path) if img.lower().endswith(('.png', '.jpg', '.jpeg', '.JPG'))]
            
            for img in images:
                src_img_path = os.path.join(src_class_path, img)
                dst_img_path = os.path.join(dst_class_path, img)
                
                # Zaten kopyalanmamışsa kopyala (Tekrar çalıştırıldığında time saver olması için)
                if not os.path.exists(dst_img_path):
                    shutil.copy2(src_img_path, dst_img_path)
                
                total_images_copied += 1
            
            print(f"[+] Kopyalandı: {class_name:40s} -> {len(images)} görüntü")
            
    # Step 2.2.5: Çıktıları Raporla
    print("\n------------------------- ÖZET -------------------------")
    print(f"Toplam hedeflenen bitki sayısı : {len(TARGET_PLANTS)}")
    print(f"Oluşturulan alt sınıf sayısı   : {len(selected_classes)}")
    print(f"Kopyalanan toplam görüntü      : {total_images_copied}")
    print("--------------------------------------------------------\n")

if __name__ == "__main__":
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    BASE_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "PlantVillage")
    
    # Interim klasörü olarak belirlediğimiz hedef:
    INTERIM_DIR = os.path.join(PROJECT_ROOT, "data", "interim")
    
    actual_source_dir = get_actual_raw_dir(BASE_RAW_DIR)
    
    # Kopyalama işlemini başlat
    filter_and_copy_data(actual_source_dir, INTERIM_DIR)
