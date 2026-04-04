import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { ShieldAlert, Sprout } from 'lucide-react';

interface Disease {
  id: number;
  plant_id: number;
  disease_name: string;
  confidence_score: number | null;
  created_at: string;
}

export default function DiseaseHistory() {
  const { user } = useAuth();
  const [history, setHistory] = useState<(Disease & { plantName: string })[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      if (!user) return;
      try {
        // Önce tüm bitkileri çek
        const pRes = await fetch(`http://localhost:8000/plants/user/${user.id}`);
        if (!pRes.ok) throw new Error('Bitkiler alınamadı');
        const plants = await pRes.json();

        // Her bitki için hastalıkları çek
        const allRecords: (Disease & { plantName: string })[] = [];
        for (const p of plants) {
           const dRes = await fetch(`http://localhost:8000/disease-records/plant/${p.id}`);
           if (dRes.ok) {
             const diseases = await dRes.json();
             diseases.forEach((d: Disease) => {
               allRecords.push({ ...d, plantName: p.plant_name });
             });
           }
        }
        
        // Yeniden eskiye sırala
        allRecords.sort((a,b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        setHistory(allRecords);

      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [user]);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
       <h2 className="text-3xl font-bold text-earth-800">Tüm Hastalık Geçmişi</h2>
       <p className="text-earth-500">Sahip olduğunuz tüm bitkilerde bugüne kadar yapılmış olan yapay zeka tahlillerinin sonuçları.</p>

       <div className="bg-white p-6 rounded-3xl border border-earth-200 shadow-sm mt-6">
         {loading ? (
             <p className="text-earth-500 animate-pulse text-center p-6">Sistem taranıyor...</p>
         ) : history.length === 0 ? (
            <div className="text-center py-10 bg-earth-50 rounded-2xl">
               <ShieldAlert className="mx-auto text-green-300 mb-4" size={48} />
               <p className="text-earth-600 font-semibold text-lg">Hiçbir hastalık kaydı bulunamadı!</p>
               <p className="text-earth-500 text-sm">Bitkileriniz gayet sağlıklı görünüyor.</p>
            </div>
         ) : (
           <div className="overflow-x-auto">
             <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-earth-200 text-earth-500 text-sm">
                    <th className="pb-3 pl-4 font-semibold">Tarih</th>
                    <th className="pb-3 font-semibold">Bitki</th>
                    <th className="pb-3 font-semibold">Hastalık / Teşhis</th>
                    <th className="pb-3 font-semibold">Güven Skoru</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-earth-100">
                  {history.map((h) => (
                    <tr key={h.id} className="hover:bg-earth-50 transition">
                      <td className="py-4 pl-4 text-earth-600 text-sm">
                         {new Date(h.created_at).toLocaleDateString("tr-TR")}
                      </td>
                      <td className="py-4 font-semibold text-earth-800 flex items-center gap-2">
                         <span className="bg-green-100 text-green-700 p-1.5 rounded-lg"><Sprout size={16}/></span>
                         {h.plantName}
                      </td>
                      <td className="py-4 text-earth-800 font-medium">
                         {h.disease_name}
                      </td>
                      <td className="py-4 font-bold text-earth-800">
                         {h.confidence_score ? (
                            <span className="px-3 py-1 bg-green-50 text-green-600 rounded-full text-xs border border-green-200">
                              %{(h.confidence_score * 100).toFixed(1)}
                            </span>
                         ) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
             </table>
           </div>
         )}
       </div>
    </div>
  );
}
