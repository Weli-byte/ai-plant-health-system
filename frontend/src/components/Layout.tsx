import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { Leaf, LogOut, Camera } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import ChatbotWidget from './ChatbotWidget';

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-earth-100">
      {/* Sol Sidebar */}
      <aside className="w-64 bg-white border-r border-earth-200 flex flex-col items-center py-6 shadow-sm">
        <div className="flex items-center gap-2 mb-10 text-green-700">
          <Leaf size={32} strokeWidth={2.5} />
          <h1 className="text-xl font-bold font-sans">AgroAI</h1>
        </div>

        <nav className="flex-1 w-full px-4 flex flex-col gap-2">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `w-full px-4 py-3 rounded-xl flex items-center gap-3 transition-colors ${
                isActive
                  ? 'bg-green-50 text-green-700 font-semibold'
                  : 'text-earth-500 hover:bg-earth-100 hover:text-earth-800'
              }`
            }
          >
            <Leaf size={20} />
            <span>Dashboard</span>
          </NavLink>
          
          <NavLink
            to="/analyze"
            className={({ isActive }) =>
              `w-full px-4 py-3 rounded-xl flex items-center gap-3 transition-colors ${
                isActive
                  ? 'bg-green-50 text-green-700 font-semibold'
                  : 'text-earth-500 hover:bg-earth-100 hover:text-earth-800'
              }`
            }
          >
            <Camera size={20} />
            <span>AI Hastalık Tespiti</span>
          </NavLink>
          <NavLink
            to="/history"
            className={({ isActive }) =>
              `w-full px-4 py-3 rounded-xl flex items-center gap-3 transition-colors ${
                isActive
                  ? 'bg-green-50 text-green-700 font-semibold'
                  : 'text-earth-500 hover:bg-earth-100 hover:text-earth-800'
              }`
            }
          >
            <LogOut size={20} /> {/* Placeholder: lucide History importu olmadan idare için */}
            <span>Hastalık Geçmişi</span>
          </NavLink>
        </nav>

        {/* Kullanıcı Profili ve Çıkış */}
        <div className="w-full px-4 mt-auto border-t border-earth-200 pt-4">
          <div className="px-4 py-3 bg-earth-50 rounded-xl mb-3 flex items-center gap-3">
             <div className="w-8 h-8 rounded-full bg-green-100 text-green-700 flex items-center justify-center font-bold">
               {user?.username.charAt(0).toUpperCase()}
             </div>
             <p className="text-sm font-semibold truncate">{user?.username}</p>
          </div>
          <button
            onClick={handleLogout}
            className="w-full px-4 py-3 rounded-xl flex items-center gap-3 text-red-500 hover:bg-red-50 transition-colors"
          >
            <LogOut size={20} />
            <span>Çıkış Yap</span>
          </button>
        </div>
      </aside>

      {/* Ana İçerik */}
      <main className="flex-1 overflow-y-auto p-8 relative">
        <Outlet />
        
        {/* Chatbot her zaman Layout'un sağ altında olacak */}
        <ChatbotWidget />
      </main>
    </div>
  );
}
