import { useNavigate } from 'react-router-dom';
import { Leaf, ShieldCheck, Activity, Smartphone } from 'lucide-react';

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-earth-100 flex flex-col">
      {/* Navbar */}
      <header className="px-8 py-6 w-full flex items-center justify-between">
        <div className="flex items-center gap-2 text-green-700">
          <Leaf size={32} strokeWidth={2.5} />
          <h1 className="text-2xl font-bold font-sans">AgroAI</h1>
        </div>
        <div className="space-x-4">
          <button 
            onClick={() => navigate('/login')} 
            className="text-earth-600 font-semibold hover:text-earth-800 transition"
          >
            Giriş Yap
          </button>
          <button 
            onClick={() => navigate('/signup')} 
            className="bg-green-600 text-white px-5 py-2.5 rounded-full font-bold shadow hover:bg-green-700 transition"
          >
            Hesap Oluştur
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 max-w-4xl mx-auto mt-10">
        <span className="bg-green-100 text-green-800 px-4 py-1.5 rounded-full text-sm font-bold mb-6 tracking-wide uppercase">
          Yapay Zeka Destekli Tarım
        </span>
        <h2 className="text-5xl md:text-6xl font-black text-earth-800 mb-6 leading-tight">
          Bitkilerinizin Sağlığı <br />
          <span className="text-green-600">Tek Bir Fotoğraf</span> Uzaklığında
        </h2>
        <p className="text-xl text-earth-600 mb-10 max-w-2xl">
          Tarlalardaki ve seralarınızdaki hastalıkları daha gözle görünür hale gelmeden tespit edin, 
          hızlı önlem önerileri ile veriminizi katlayın.
        </p>
        
        <button 
          onClick={() => navigate('/signup')} 
          className="bg-earth-800 text-white text-lg px-8 py-4 rounded-xl font-bold shadow-xl hover:bg-earth-900 transition flex items-center gap-3 transform hover:-translate-y-1"
        >
          Hemen Taramaya Başla <Leaf size={20} />
        </button>

        {/* Özellikler Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-24 mb-16 text-left">
           <div className="bg-white p-6 rounded-3xl shadow-sm border border-earth-200">
             <div className="bg-blue-100 w-12 h-12 rounded-2xl flex items-center justify-center text-blue-600 mb-4"><Smartphone size={24} /></div>
             <h3 className="text-xl font-bold text-earth-800 mb-2">Hızlı Analiz</h3>
             <p className="text-earth-500">Telefonunuzla çektiğiniz bir fotoğrafı sisteme yükleyin ve saniyeler içinde rapor alın.</p>
           </div>
           <div className="bg-white p-6 rounded-3xl shadow-sm border border-earth-200">
             <div className="bg-red-100 w-12 h-12 rounded-2xl flex items-center justify-center text-red-600 mb-4"><Activity size={24} /></div>
             <h3 className="text-xl font-bold text-earth-800 mb-2">Erken Uyarı</h3>
             <p className="text-earth-500">Hastalığın yayılma ihtimallerini, bölgesel risk analizleri ile erkenden öğrenin.</p>
           </div>
           <div className="bg-white p-6 rounded-3xl shadow-sm border border-earth-200">
             <div className="bg-green-100 w-12 h-12 rounded-2xl flex items-center justify-center text-green-600 mb-4"><ShieldCheck size={24} /></div>
             <h3 className="text-xl font-bold text-earth-800 mb-2">Tedavi Önerileri</h3>
             <p className="text-earth-500">Yapay zekanın organik veya inorganik bakım/ilaç tavsiyeleri ile hemen müdahale edin.</p>
           </div>
        </div>
      </main>
    </div>
  );
}
