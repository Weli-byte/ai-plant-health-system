import { StatsCards } from "@/components/dashboard/StatsCards";
import { PhotoUpload } from "@/components/dashboard/PhotoUpload";
import { RecentAnalyses } from "@/components/dashboard/RecentAnalyses";
import { RiskChart } from "@/components/dashboard/RiskChart";
import { CareRecommendations } from "@/components/dashboard/CareRecommendations";

const Index = () => {
  return (
    <div className="container space-y-6 py-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-muted-foreground">Tarım alanlarınızı yapay zeka ile izleyin ve yönetin</p>
      </div>

      <StatsCards />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <PhotoUpload />
        </div>
        <div className="lg:col-span-2">
          <RiskChart />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RecentAnalyses />
        <CareRecommendations />
      </div>
    </div>
  );
};

export default Index;
