import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, Image as ImageIcon, Loader2 } from 'lucide-react';

export default function Analyze() {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const navigate = useNavigate();

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Mock: resmi okuyup URL oluştur
      const imageUrl = URL.createObjectURL(file);
      setSelectedImage(imageUrl);
    }
  };

  const handleAnalyze = () => {
    if (!selectedImage) return;
    setIsAnalyzing(true);

    // Mock API bekleme süresi (3 saniye)
    setTimeout(() => {
      setIsAnalyzing(false);
      // Sonuç sayfasına geçiş, resmi state üzerinden taşıyoruz
      navigate('/results', { state: { image: selectedImage } });
    }, 3000);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex flex-col mb-8">
        <h2 className="text-3xl font-bold text-earth-800 mb-2">Hastalık Tespiti Başlat</h2>
        <p className="text-earth-500">
          Bitkinizin problemli olduğunu düşündüğünüz bölgesinin net bir fotoğrafını yükleyin.
        </p>
      </div>

      <div className="bg-white rounded-3xl p-8 shadow-sm border border-earth-200">
        
        {/* Fotoğraf Yükleme Alanı */}
        {!selectedImage ? (
          <div className="border-2 border-dashed border-green-300 bg-green-50 rounded-2xl p-16 flex flex-col items-center justify-center text-center transition hover:bg-green-100">
            <UploadCloud size={64} className="text-green-500 mb-4" />
            <h3 className="text-xl font-bold text-green-800 mb-2">Fotoğraf Yükle veya Sürükle</h3>
            <p className="text-green-600 mb-6 font-medium">JPEG, PNG, WEBP (Max 10MB)</p>
            
            <label className="cursor-pointer bg-green-600 text-white font-semibold py-3 px-6 rounded-xl hover:bg-green-700 transition">
              Bilgisayardan Seç
              <input type="file" className="hidden" accept="image/*" onChange={handleImageUpload} />
            </label>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <div className="relative w-full max-w-lg mb-6 rounded-2xl overflow-hidden shadow-md">
               <img src={selectedImage} alt="Seçilen Bitki" className="w-full h-auto object-cover" />
               <button 
                 onClick={() => setSelectedImage(null)}
                 className="absolute top-4 right-4 bg-white text-red-500 p-2 rounded-full shadow hover:bg-red-50"
                 disabled={isAnalyzing}
               >
                 Değiştir
               </button>
            </div>

            <button
               onClick={handleAnalyze}
               disabled={isAnalyzing}
               className={`w-full max-w-lg font-bold py-4 rounded-xl flex items-center justify-center gap-3 transition-colors ${
                 isAnalyzing 
                   ? 'bg-earth-200 text-earth-500 cursor-not-allowed'
                   : 'bg-green-600 text-white hover:bg-green-700 shadow-lg'
               }`}
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="animate-spin" size={24} />
                  Yapay Zeka Analiz Ediyor...
                </>
              ) : (
                <>
                  <ImageIcon size={24} />
                  Analizi Başlat
                 </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
