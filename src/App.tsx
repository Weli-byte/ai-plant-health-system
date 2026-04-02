import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Navbar } from "@/components/Navbar";
import { Chatbot } from "@/components/Chatbot";
import Index from "./pages/Index";
import AnalysisResult from "./pages/AnalysisResult";
import AnalysisHistory from "./pages/AnalysisHistory";
import Planning from "./pages/Planning";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <div className="min-h-screen bg-background">
          <Navbar />
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/analysis/:id" element={<AnalysisResult />} />
            <Route path="/history" element={<AnalysisHistory />} />
            <Route path="/planning" element={<Planning />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
          <Chatbot />
        </div>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
