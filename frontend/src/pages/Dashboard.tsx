import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Eye, Plus } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface Plant {
  id: number;
  plant_name: string;
  created_at: string;
}

export default function Dashboard() {
  const { user } = useAuth();
  const [plants, setPlants] = useState<Plant[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPlants = async () => {
      if (!user) return;
      try {
        const res = await fetch(`http://localhost:8000/plants/user/${user.id}`);
        if (res.ok) {
          const data = await res.json();
          setPlants(data);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchPlants();
  }, [user]);

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Karşılama Alanı */}
      <div className="bg-white rounded-3xl p-8 shadow-sm border border-earth-200 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-earth-800 mb-2">
            Merhaba, {user?.username}! 👋
          </h2>
          <p className="text-earth-500 text-lg">
            Seralarındaki bitkilerini takip etmeye devam et.
          </p>
        </div>
        <div className="flex gap-3 w-full md:w-auto">
           <Link to="/analyze" className="flex-1 md:flex-none text-center bg-green-600 text-white px-6 py-3 rounded-xl font-bold shadow hover:bg-green-700 transition">
             AI Tahlil
           </Link>
           <Link to="/plants/add" className="flex-1 md:flex-none text-center bg-earth-800 text-white px-6 py-3 rounded-xl font-bold shadow hover:bg-earth-900 transition flex items-center justify-center gap-2">
             <Plus size={20} /> Bitki
           </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* İstatistik Kartları */}
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-earth-200">
           <h3 className="text-earth-500 font-semibold mb-1">Toplam Bitki</h3>
           <p className="text-4xl font-bold text-green-700">{plants.length}</p>
        </div>
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-earth-200 bg-green-50">
           <h3 className="text-green-800 font-semibold mb-1">Sağlık Skoru (Ort.)</h3>
           <p className="text-4xl font-bold text-green-600">%85</p>
        </div>
      </div>

      {/* Bitki Listesi */}
      <h3 className="text-2xl font-bold text-earth-800 mt-10 mb-4 px-2">Kayıtlı Bitkilerim</h3>
      {loading ? (
        <div className="text-earth-500">Yükleniyor...</div>
      ) : plants.length === 0 ? (
        <div className="bg-white rounded-3xl p-10 text-center border border-earth-200 shadow-sm">
          <p className="text-earth-500 text-lg mb-4">Henüz hiç bitki eklememişsiniz.</p>
          <Link to="/plants/add" className="text-green-600 font-bold hover:underline">İlk Bitkini Ekle</Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plants.map(plant => (
            <div key={plant.id} className="bg-white rounded-3xl p-6 shadow-sm border border-earth-200 hover:shadow-md transition">
               <h4 className="font-bold text-xl text-earth-800 mb-4">{plant.plant_name}</h4>
               <div className="flex items-center justify-between mt-auto pt-4 border-t border-earth-100">
                  <span className="text-sm text-earth-400">{new Date(plant.created_at).toLocaleDateString("tr-TR")}</span>
                  <Link to={`/plants/${plant.id}`} className="text-green-600 font-semibold flex items-center gap-1 hover:text-green-800">
                    <Eye size={18} /> Gözat
                  </Link>
               </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
