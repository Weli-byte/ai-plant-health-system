import { createContext, useContext, useState, type ReactNode } from 'react';

// Mock Kullanıcı Verisi Tipi
export interface User {
  id: number;
  username: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  login: (userData: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  // LocalStorage'dan mock user okumaya çalış
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('plant_health_user');
    return saved ? JSON.parse(saved) : null;
  });

  const login = (userData: User) => {
    localStorage.setItem('plant_health_user', JSON.stringify(userData));
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('plant_health_user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
