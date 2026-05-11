import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { User, Leaf, LogOut, Settings, MapPin, Phone, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getUser, logout } from "@/lib/auth";
import { plantsApi, diseaseRecordsApi } from "@/services/api";

export default function Profile() {
  const navigate = useNavigate();
  const user = getUser();

  const [plantCount, setPlantCount] = useState(0);
  const [analysisCount, setAnalysisCount] = useState(0);
  const [healthPct, setHealthPct] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    setLoading(true);
    try {
      const plants = await plantsApi.getByUser(1);
      setPlantCount(plants.length);

      // Tüm hastalık kayıtlarını topla
      let totalRecords = 0;
      let healthyRecords = 0;

      for (const plant of plants) {
        try {
          const records = await diseaseRecordsApi.getByPlant(plant.id);
          totalRecords += records.length;
          healthyRecords += records.filter(
            (r) => r.disease_name === "Sağlıklı" || r.disease_name === "Healthy"
          ).length;
        } catch {
          // Kayıt olmayabilir
        }
      }

      setAnalysisCount(totalRecords);
      setHealthPct(totalRecords > 0 ? Math.round((healthyRecords / totalRecords) * 100) : 0);
    } catch (err) {
      console.error("Profil istatistik hatası:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4 animate-fade-in">
      <Card className="rounded-3xl border-border/60 shadow-card">
        <CardContent className="p-5 text-center">
          <div className="mx-auto mb-3 flex h-20 w-20 items-center justify-center rounded-full bg-leaf-gradient text-primary-foreground shadow-soft">
            <User className="h-9 w-9" />
          </div>
          <p className="text-lg font-semibold text-foreground capitalize">
            {user?.name ?? "Çiftçi"}
          </p>
          <p className="text-xs text-muted-foreground">{user?.email ?? "—"}</p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-3 gap-2">
        {loading ? (
          <Card className="rounded-2xl border-border/60 col-span-3">
            <CardContent className="p-3 flex items-center justify-center">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span className="ml-2 text-xs text-muted-foreground">Yükleniyor...</span>
            </CardContent>
          </Card>
        ) : (
          <>
            <StatCard label="Bitki" value={String(plantCount)} />
            <StatCard label="Analiz" value={String(analysisCount)} />
            <StatCard label="Sağlık" value={`%${healthPct}`} />
          </>
        )}
      </div>

      <div className="space-y-2">
        <Row icon={Leaf} title="Tarlam" sub="Antalya, Serik" />
        <Row icon={MapPin} title="Konum" sub="36.91° K, 31.10° D" />
        <Row icon={Phone} title="İletişim" sub="+90 5•• ••• •• ••" />
        <Row icon={Settings} title="Ayarlar" sub="Bildirim, dil, gizlilik" />
      </div>

      <Button
        onClick={() => {
          logout();
          navigate("/login");
        }}
        variant="outline"
        className="h-12 w-full rounded-2xl border-destructive/30 text-destructive hover:bg-destructive/5"
      >
        <LogOut className="mr-2 h-4 w-4" /> Çıkış yap
      </Button>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="rounded-2xl border-border/60">
      <CardContent className="p-3 text-center">
        <p className="text-base font-semibold text-foreground">{value}</p>
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  );
}

function Row({
  icon: Icon,
  title,
  sub,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  sub: string;
}) {
  return (
    <Card className="rounded-2xl border-border/60">
      <CardContent className="flex items-center gap-3 p-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-accent-foreground">
          <Icon className="h-4 w-4" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-foreground">{title}</p>
          <p className="text-[11px] text-muted-foreground">{sub}</p>
        </div>
      </CardContent>
    </Card>
  );
}
