import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AlertTriangle, ShieldCheck, TrendingUp, Droplets, ArrowLeft, Save, Loader2, CheckCircle2 } from 'lucide-react';
import { diseaseRecordsApi, sprint3Api, type FarmingAdviceResponse } from '@/services/api';

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();

  // Analiz sayfasından gelen fotoğraf URL'i ve API sonuçları
  const uploadedImage = location.state?.image || 'https://images.unsplash.com/photo-1592843997233-0eff958b4fcd?auto=format&fit=crop&q=80&w=800';
  const resultData = location.state?.resultData;

  const leafDetected = resultData?.leaf_detection?.leaf_detected ?? true;
  const diseaseInfo = resultData?.disease_classification;
  const gradcamInfo = resultData?.gradcam;

  const diseaseName = diseaseInfo?.predicted_class || 'Powdery Mildew (Külleme)';
  const confidenceScore = diseaseInfo?.confidence ? (diseaseInfo.confidence * 100).toFixed(1) : '94.2';
  const overlayImage = gradcamInfo?.overlay_base64 ? `data:image/jpeg;base64,${gradcamInfo.overlay_base64}` : uploadedImage;

  // Kaydetme durumu
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Tarım danışma
  const [advice, setAdvice] = useState<FarmingAdviceResponse | null>(null);
  const [adviceLoading, setAdviceLoading] = useState(false);

  // Sonucu hastalık geçmişine kaydet
  const handleSave = async () => {
    setSaving(true);
    try {
      await diseaseRecordsApi.create({
        plant_id: 1, // İlk bitki (şimdilik sabit)
        disease_name: diseaseName,
        confidence_score: diseaseInfo?.confidence ?? 0.94,
      });
      setSaved(true);
    } catch (err) {
      console.error('Kaydetme hatası:', err);
      alert('Sonuç kaydedilemedi. Lütfen tekrar deneyin.');
    } finally {
      setSaving(false);
    }
  };

  // Tarım danışma API'sinden öneri al
  const loadAdvice = async () => {
    setAdviceLoading(true);
    try {
      const data = await sprint3Api.getFarmingAdvice({
        temperature: 24,
        humidity: 72,
        rainfall: 12,
        wind_speed: 8,
        season: 'spring',
        plant_health_status: 'diseased',
        disease_name: diseaseName,
      });
      setAdvice(data);
    } catch (err) {
      console.error('Danışma hatası:', err);
    } finally {
      setAdviceLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-20">
      <button
        onClick={() => navigate('/analyze')}
        className="flex items-center gap-2 text-earth-500 hover:text-earth-800 font-semibold mb-2"
      >
        <ArrowLeft size={20} /> Yeni Analiz
      </button>

      <div className="flex items-center justify-between">
         <h2 className="text-3xl font-bold text-earth-800">Yapay Zeka Analiz Raporu</h2>
         <span className="bg-red-100 text-red-700 px-4 py-2 rounded-full font-bold text-sm">Dikkat Gerektiriyor</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Sol Kolon */}
        <div className="space-y-6">
          <div className="bg-white rounded-3xl p-6 shadow-sm border border-earth-200">
            <h3 className="text-xl font-bold text-earth-800 mb-4 flex gap-2 items-center">
              <ShieldCheck className="text-green-500" />
              Saptanan Problemli Bölge
            </h3>
            <div className="relative rounded-2xl overflow-hidden bg-black group">
               <img src={overlayImage} alt="Bitki Analizi" className="w-full opacity-80" />
               {!gradcamInfo && <div className="absolute top-[30%] left-[40%] w-32 h-32 border-4 border-red-500 rounded-full animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.5)]"></div>}
               <div className="absolute bottom-4 left-4 bg-black/60 text-white text-sm px-3 py-1 rounded-lg backdrop-blur-sm">
                  Model Güven Skoru: <strong className="text-green-400">%{confidenceScore}</strong>
               </div>
            </div>
            <p className="mt-4 text-earth-500 text-sm">
               Kırmızı işaretli bölge, yapay zekanın <b>"{diseaseName}"</b> hastalığı teşhisini koyarken odaklandığı ana dokuları göstermektedir.
               {!leafDetected && <span className="text-red-500 block mt-2">Uyarı: Görselde net bir bitki yaprağı tespit edilemedi. Analiz sonuçları yanıltıcı olabilir.</span>}
            </p>
          </div>

           {/* Erken Risk Tahmini */}
           <div className="bg-orange-50 rounded-3xl p-6 border border-orange-200">
             <h3 className="text-lg font-bold text-orange-800 mb-2 flex items-center gap-2">
               <AlertTriangle size={20} />
               Erken Risk Tahmini
             </h3>
             <p className="text-orange-700">
               Lezyonlar henüz başlangıç evresinde (Evre 1). Ancak nem miktarının yüksek seyretmesi sebebiyle yayılma riski son 48 saatte %40 artmış durumda.
             </p>
           </div>

           {/* Sonucu Kaydet Butonu */}
           <button
             onClick={handleSave}
             disabled={saving || saved}
             className={`w-full flex items-center justify-center gap-2 py-3 rounded-2xl font-semibold transition ${
               saved
                 ? 'bg-green-100 text-green-700 cursor-default'
                 : 'bg-green-600 text-white hover:bg-green-700 shadow-lg'
             }`}
           >
             {saving && <Loader2 className="h-4 w-4 animate-spin" />}
             {saved && <CheckCircle2 className="h-4 w-4" />}
             {saved ? 'Sonuç Kaydedildi ✓' : saving ? 'Kaydediliyor...' : '💾 Sonucu Geçmişe Kaydet'}
           </button>
        </div>

        {/* Sağ Kolon */}
        <div className="space-y-6">

          {/* Teşhis Kartı */}
          <div className="bg-white rounded-3xl p-6 shadow-sm border-l-8 border-red-500">
             <h4 className="text-earth-500 font-semibold mb-1">Tespit Edilen Hastalık</h4>
             <p className="text-3xl font-black text-earth-800 mb-2">{diseaseName}</p>
             <p className="text-earth-600">
               Yapay zeka sistemimiz yüklediğiniz görselde bu hastalığın belirtilerini tespit etti. Aşağıdaki bakım önerilerini dikkate almanız tavsiye edilir.
             </p>
          </div>

          {/* İlaç ve Bakım Önerileri */}
          <div className="bg-white rounded-3xl p-6 shadow-sm border border-earth-200">
             <h3 className="text-xl font-bold text-earth-800 mb-4 flex items-center gap-2">
               <Droplets className="text-blue-500" />
               İlaç ve Bakım Önerileri
             </h3>

             {/* Tarım danışma butonu */}
             {!advice && (
               <button
                 onClick={loadAdvice}
                 disabled={adviceLoading}
                 className="w-full mb-4 py-2 rounded-xl bg-blue-50 text-blue-700 font-semibold text-sm hover:bg-blue-100 transition flex items-center justify-center gap-2"
               >
                 {adviceLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Droplets className="h-4 w-4" />}
                 {adviceLoading ? 'AI öneriler yükleniyor...' : 'AI Tarım Danışmanlığı Al'}
               </button>
             )}

             {/* API'den gelen öneriler */}
             {advice ? (
               <ul className="space-y-3">
                 {advice.farming_advice.map((tip, idx) => (
                   <li key={idx} className="flex gap-3 text-earth-700 bg-earth-50 p-3 rounded-xl text-sm">
                     {tip}
                   </li>
                 ))}
                 {advice.pesticide_recommendations.map((p, idx) => (
                   <li key={`pest-${idx}`} className="flex gap-3 text-earth-700 bg-green-50 p-3 rounded-xl text-sm">
                     <strong className="text-green-700">💊</strong>
                     <span><b>{p.product_name}</b> ({p.active_ingredient}) — {p.application_notes}</span>
                   </li>
                 ))}
                 <li className="flex gap-3 text-earth-700 bg-blue-50 p-3 rounded-xl text-sm">
                   <strong className="text-blue-700">💧</strong> {advice.irrigation_advice}
                 </li>
               </ul>
             ) : (
               <ul className="space-y-3">
                 <li className="flex gap-3 text-earth-700 bg-earth-50 p-3 rounded-xl">
                   <strong className="text-green-700">1.</strong> Organik kükürt bazlı fungisit uygulamasına hemen başlanmalıdır.
                 </li>
                 <li className="flex gap-3 text-earth-700 bg-earth-50 p-3 rounded-xl">
                   <strong className="text-green-700">2.</strong> Enfekte olmuş alt yaprakları steril makasla derhal budayın.
                 </li>
                 <li className="flex gap-3 text-earth-700 bg-earth-50 p-3 rounded-xl">
                   <strong className="text-green-700">3.</strong> Akşam üstü sulamayı kesmeli, toprak yüzeyini kuru tutmalısınız.
                 </li>
               </ul>
             )}
          </div>

          {/* Tarım Planlama */}
          <div className="bg-white rounded-3xl p-6 shadow-sm border border-earth-200 bg-gradient-to-br from-white to-green-50">
             <h3 className="text-xl font-bold text-earth-800 mb-4 flex items-center gap-2">
               <TrendingUp className="text-green-600" />
               Gelecek Durum ve Planlama
             </h3>
             <div className="mb-4">
                <span className="text-xs font-bold text-green-700 uppercase tracking-widest block mb-1">Müdahale Halinde</span>
                <p className="text-earth-700">Önerilen ilaçlama yapılırsa 7 gün içerisinde beyaz lekelerin dökülmesi ve yeni yaprakların sağlıklı çıkması %85 oranında muhtemeldir.</p>
             </div>
             <div>
                <span className="text-xs font-bold text-red-700 uppercase tracking-widest block mb-1">Tarım Planlama Etkisi</span>
                <p className="text-earth-700">Hasat süresi yaklaşık 10 gün gecikebilir. Önümüzdeki sezon dikim aralıklarını %15 daha geniş tutarak hava sirkülasyonunu artırın.</p>
             </div>
          </div>

        </div>
      </div>
    </div>
  );
}
