import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, XCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function AddPlant() {
  const [plantName, setPlantName] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');
  
  const { user } = useAuth();
  const navigate = useNavigate();

  const handleAddPlant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    if (!plantName.trim()) {
      setMessage('Lütfen bitki adını girin.');
      setStatus('error');
      return;
    }

    setStatus('loading');
    try {
      const res = await fetch('http://localhost:8000/plants/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plant_name: plantName, user_id: user.id }),
      });

      if (!res.ok) throw new Error('Bitki eklenemedi.');

      setStatus('success');
      setMessage('Bitkiniz başarıyla kaydedildi!');
      
      setTimeout(() => navigate('/dashboard'), 1500); // 1.5 sn sonra dashboard'a dön
    } catch (error: any) {
      setStatus('error');
      setMessage(error.message);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h2 className="text-3xl font-bold text-earth-800">Yeni Bitki Ekle</h2>
      <p className="text-earth-500">Sisteme takip etmek istediğiniz veya analiz yaptıracağınız yeni bir bitki kaydedin.</p>

      <div className="bg-white rounded-3xl p-8 shadow-sm border border-earth-200">
        {status === 'success' && (
          <div className="bg-green-50 text-green-700 p-4 rounded-xl flex items-center gap-3 mb-6">
            <CheckCircle size={24} /> {message}
          </div>
        )}
        {status === 'error' && (
          <div className="bg-red-50 text-red-700 p-4 rounded-xl flex items-center gap-3 mb-6">
            <XCircle size={24} /> {message}
          </div>
        )}

        <form onSubmit={handleAddPlant} className="space-y-6">
          <div>
            <label className="block text-earth-600 font-semibold mb-2">Bitki Türü / Adı</label>
            <input 
              type="text" 
              value={plantName}
              onChange={(e) => setPlantName(e.target.value)}
              className="w-full bg-earth-50 border border-earth-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder="Örn: Cherry Domates, Sera Salatalık 1"
            />
          </div>
          
          <button 
             type="submit" 
             disabled={status === 'loading' || status === 'success'}
             className="bg-green-600 text-white font-bold py-3 px-8 rounded-xl hover:bg-green-700 transition"
          >
            {status === 'loading' ? 'Ekleniyor...' : 'Bitkiyi Kaydet'}
          </button>
        </form>
      </div>
    </div>
  );
}
