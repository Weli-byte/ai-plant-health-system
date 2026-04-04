import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

// Pages
import Landing from './pages/Landing';
import Signup from './pages/Signup';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import AddPlant from './pages/AddPlant';
import PlantDetail from './pages/PlantDetail';
import DiseaseHistory from './pages/DiseaseHistory';
import Analyze from './pages/Analyze';
import Results from './pages/Results';
import Layout from './components/Layout';

// Korumalı rota (Giriş yapmayanları login sayfasına atar)
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return children;
};

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/plants/add" element={<AddPlant />} />
        <Route path="/plants/:id" element={<PlantDetail />} />
        <Route path="/history" element={<DiseaseHistory />} />
        <Route path="/analyze" element={<Analyze />} />
        <Route path="/results" element={<Results />} />
      </Route>
    </Routes>
  );
}

export default App;
