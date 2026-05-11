import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { PhoneShell } from "@/components/PhoneShell";
import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import Login from "./pages/Login";
import Index from "./pages/Index";
import AnalysisResult from "./pages/AnalysisResult";
import AnalysisHistory from "./pages/AnalysisHistory";
import CameraAnalysis from "./pages/CameraAnalysis";
import Analyze from "./pages/Analyze";
import Results from "./pages/Results";
import Planning from "./pages/Planning";
import Plants from "./pages/Plants";
import Reports from "./pages/Reports";
import Chat from "./pages/Chat";
import Profile from "./pages/Profile";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const Shell = ({ children }: { children: React.ReactNode }) => (
  <RequireAuth>
    <AppShell>{children}</AppShell>
  </RequireAuth>
);

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <PhoneShell>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Shell><Index /></Shell>} />
            <Route path="/history" element={<Shell><AnalysisHistory /></Shell>} />
            <Route path="/analysis/new" element={<Shell><CameraAnalysis /></Shell>} />
            <Route path="/analysis/:id" element={<Shell><AnalysisResult /></Shell>} />
            <Route path="/analyze" element={<Shell><Analyze /></Shell>} />
            <Route path="/results" element={<Shell><Results /></Shell>} />
            <Route path="/plants" element={<Shell><Plants /></Shell>} />
            <Route path="/reports" element={<Shell><Reports /></Shell>} />
            <Route path="/planning" element={<Shell><Planning /></Shell>} />
            <Route path="/chat" element={<Shell><Chat /></Shell>} />
            <Route path="/profile" element={<Shell><Profile /></Shell>} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </PhoneShell>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
