import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Leaf } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (!username || !email) {
      setError('Lütfen tüm alanları doldurun.');
      return;
    }

    setIsLoading(true);

    try {
      // Mock Login işlemi (Şimdilik direkt giriş yapıyor)
      // Normalde burada API isteği atılır (Sprint 3) veya Signup için POST /users/
      const mockUser = {
        id: Math.floor(Math.random() * 1000),
        username,
        email,
      };

      // AuthContext'e kaydedip Dashboard'a yönlendiriyoruz
      login(mockUser);
      navigate('/dashboard');
    } catch (err) {
      setError('Giriş başarısız oldu.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-earth-100 flex items-center justify-center p-4">
      <div className="bg-white max-w-md w-full rounded-3xl p-8 shadow-xl border border-earth-200">
        
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <div className="bg-green-100 p-4 rounded-full text-green-600">
            <Leaf size={48} strokeWidth={2} />
          </div>
        </div>

        <h2 className="text-3xl font-bold text-center text-earth-800 mb-2 font-sans">
          AgroAI'a Hoş Geldiniz
        </h2>
        <p className="text-center text-earth-500 mb-8">
          Bitkilerinizin sağlığı yapay zeka güvencesinde.
        </p>

        {error && (
           <div className="bg-red-50 text-red-600 p-3 rounded-xl mb-4 text-sm text-center">
             {error}
           </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-semibold text-earth-800 mb-1">
              Kullanıcı Adı
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-earth-200 focus:outline-none focus:ring-2 focus:ring-green-500 bg-earth-50 text-earth-800 transition-shadow"
              placeholder="tarim_uzmani"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-earth-800 mb-1">
              E-Posta Adresi
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-earth-200 focus:outline-none focus:ring-2 focus:ring-green-500 bg-earth-50 text-earth-800 transition-shadow"
              placeholder="ornek@mail.com"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3.5 px-4 rounded-xl transition-colors disabled:opacity-50"
          >
            {isLoading ? 'Giriş Yapılıyor...' : 'Sisteme Gir'}
          </button>
        </form>
      </div>
    </div>
  );
}
