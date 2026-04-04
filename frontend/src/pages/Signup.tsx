import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Leaf } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Signup() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const API_URL = 'http://localhost:8000';

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (username.length < 3) {
      return setError('Kullanıcı adı en az 3 karakter olmalı.');
    }
    if (password.length < 8) {
      return setError('Şifre en az 8 karakter olmalı.');
    }

    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/users/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Kayıt olurken bir hata oluştu.');
      }

      // Kayıt başarılı, Local AuthContext'e mock session atalım
      login(data);
      navigate('/dashboard');
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-earth-100 flex items-center justify-center p-4">
      <div className="bg-white max-w-md w-full rounded-3xl p-8 shadow-xl border border-earth-200">
        <div className="flex justify-center mb-6">
          <div className="bg-green-100 p-4 rounded-full text-green-600">
            <Leaf size={48} strokeWidth={2} />
          </div>
        </div>
        <h2 className="text-3xl font-bold text-center text-earth-800 mb-8">Kayıt Ol</h2>

        {error && (
           <div className="bg-red-50 text-red-600 p-3 rounded-xl mb-4 text-sm text-center">
             {error}
           </div>
        )}

        <form onSubmit={handleSignup} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-earth-800 mb-1">Kullanıcı Adı</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-earth-200 focus:outline-none focus:ring-2 focus:ring-green-500 bg-earth-50 text-earth-800"
              placeholder="AhmetCiftci"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-earth-800 mb-1">E-Posta Adresi</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-earth-200 focus:outline-none focus:ring-2 focus:ring-green-500 bg-earth-50 text-earth-800"
              placeholder="ahmet@example.com"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-earth-800 mb-1">Şifre</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-earth-200 focus:outline-none focus:ring-2 focus:ring-green-500 bg-earth-50 text-earth-800"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3.5 px-4 rounded-xl mt-6 transition-colors"
          >
            {isLoading ? 'Hesap Oluşturuluyor...' : 'Ücretsiz Kayıt Ol'}
          </button>
        </form>

        <p className="mt-6 text-center text-earth-500 text-sm">
          Zaten hesabınız var mı? <button onClick={() => navigate('/login')} className="text-green-700 font-bold ml-1 hover:underline">Giriş Yap</button>
        </p>
      </div>
    </div>
  );
}
