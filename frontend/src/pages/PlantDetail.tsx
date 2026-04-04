import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Activity, Calendar } from 'lucide-react';

interface Disease {
  id: number;
  disease_name: string;
  confidence_score: number | null;
  created_at: string;
}

export default function PlantDetail() {
  const { id } = useParams<{ id: string }>();
  const [plant, setPlant] = useState<{ id: number; plant_name: string } | null>(null);
  const [records, setRecords] = useState<Disease[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Bitki bilgisi
        const pRes = await fetch(`http://localhost:8000/plants/${id}`);
        if(pRes.ok) setPlant(await pRes.json());

        // Hastalık geçmişi
        const rRes = await fetch(`http://localhost:8000/disease-records/plant/${id}`);
        if(rRes.ok) setRecords(await rRes.json());
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    if (id) fetchData();
  }, [id]);

  if (loading) return <div className="text-earth-500 font-semibold p-8 text-center animate-pulse">Yükleniyor...</div>;
  if (!plant) return <div className="text-red-500 font-bold p-8 text-center">Bitki Bulunamadı!</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <Link to="/dashboard" className="flex items-center gap-2 text-earth-500 hover:text-earth-800 font-semibold w-fit">
        <ArrowLeft size={20} /> Geri Dön
      </Link>

      <div className="bg-white rounded-3xl p-8 shadow-sm border border-earth-200">
         <h2 className="text-3xl font-black text-earth-800">{plant.plant_name}</h2>
         <p className="text-earth-500 mt-2">Bu bitkiye ait tüm AI analiz tahlil geçmişi aşağıda listelenmiştir.</p>
      </div>

      <div className="bg-white rounded-3xl p-6 shadow-sm border border-earth-200">
         <h3 className="text-xl font-bold flex items-center gap-2 text-earth-800 border-b border-earth-100 pb-4 mb-4">
           <Activity className="text-green-600" /> Yapılan Hastalık Tespitleri
         </h3>

         {records.length === 0 ? (
           <div className="text-center py-10 text-earth-500 bg-earth-50 rounded-2xl">
             Bu bitki için henüz bir hastalık kaydı bulunamadı.
           </div>
         ) : (
           <div className="space-y-4">
             {records.map(r => (
               <div key={r.id} className="flex flex-col sm:flex-row justify-between sm:items-center bg-earth-50 p-4 rounded-2xl border border-earth-100">
                 <div>
                   <h4 className="font-bold text-lg text-earth-800">{r.disease_name}</h4>
                   <p className="text-sm text-earth-500 flex items-center gap-1 mt-1">
                     <Calendar size={14} /> {new Date(r.created_at).toLocaleString('tr-TR')}
                   </p>
                 </div>
                 <div className="mt-3 sm:mt-0 flex flex-col sm:items-end">
                   <span className="text-xs uppercase tracking-wider text-earth-500 font-extrabold">Güven Skoru</span>
                   <span className="text-xl font-bold text-green-600">
                     {r.confidence_score ? `%${(r.confidence_score * 100).toFixed(1)}` : 'Bilinmiyor'}
                   </span>
                 </div>
               </div>
             ))}
           </div>
         )}
      </div>
    </div>
  );
}
