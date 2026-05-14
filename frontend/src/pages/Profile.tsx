import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { User, Leaf, LogOut, MapPin, Phone, Settings, Loader2, Wheat } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getUser, logout } from "@/lib/auth";
import { plantsApi, diseaseRecordsApi } from "@/services/api";

export default function Profile() {
  const navigate = useNavigate();
  const user = getUser();

  const [plantCount, setPlantCount] = useState(0);
  const [analysisCount, setAnalysisCount] = useState(0);
  const [healthPct, setHealthPct] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    setLoading(true);
    try {
      const backendUserId = user?.backendUserId;
      if (!backendUserId) {
        setLoading(false);
        return;
      }

      const plants = await plantsApi.getByUser(backendUserId);
      setPlantCount(plants.length);

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
      setHealthPct(totalRecords > 0 ? Math.round((healthyRecords / totalRecords) * 100) : null);
    } catch (err) {
      console.error("Profil istatistik hatası:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Kullanıcı kartı */}
      <div className="rounded-2xl p-5 text-center shadow-card" style={{ background: "var(--renk-bej-koyu)", border: "1px solid var(--renk-bej-border)" }}>
          <div className="mx-auto mb-3 flex h-20 w-20 items-center justify-center rounded-full text-white shadow-soft" style={{ background: "var(--renk-acik-yesil)" }}>
            <User className="h-9 w-9" />
          </div>
          <p className="text-lg font-semibold text-foreground capitalize">
            {user?.name ?? "Çiftçi"}
          </p>
          <p className="text-xs text-muted-foreground">{user?.email ?? "—"}</p>
      </div>

      {/* İstatistikler */}
      <div className="grid grid-cols-3 gap-2">
        {loading ? (
          <div className="rounded-xl col-span-3 p-3 flex items-center justify-center" style={{ background: "var(--renk-bej-koyu)" }}>
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span className="ml-2 text-xs text-muted-foreground">Yükleniyor...</span>
          </div>
        ) : (
          <>
            <StatCard label="Bitki" value={String(plantCount)} />
            <StatCard label="Analiz" value={String(analysisCount)} />
            <StatCard
              label="Sağlık"
              value={healthPct !== null ? `%${healthPct}` : "—"}
            />
          </>
        )}
      </div>

      {/* Profil detayları */}
      <div className="space-y-2">
        {user?.city && (
          <Row
            icon={MapPin}
            title="Konum"
            sub={user.district ? `${user.city}, ${user.district}` : user.city}
          />
        )}
        {user?.phone && (
          <Row icon={Phone} title="Telefon" sub={user.phone} />
        )}
        {user?.fieldSize && (
          <Row icon={Leaf} title="Tarla Büyüklüğü" sub={`${user.fieldSize} dönüm`} />
        )}
        {user?.crops && user.crops.length > 0 && (
          <Row icon={Wheat} title="Ürünler" sub={user.crops.join(", ")} />
        )}
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
    <div className="rounded-xl p-3 text-center" style={{ background: "var(--renk-bej-koyu)", border: "1px solid var(--renk-bej-border)" }}>
      <p className="text-base font-semibold" style={{ color: "var(--renk-koyu-yesil)" }}>{value}</p>
      <p className="text-[10px] uppercase tracking-wider" style={{ color: "var(--renk-metin-soluk)" }}>{label}</p>
    </div>
  );
}

function Row({
  icon: Icon, title, sub,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  sub: string;
}) {
  return (
    <div
      className="flex items-center gap-3 rounded-xl p-3 bg-white"
      style={{ border: "1px solid var(--renk-bej-border)" }}
    >
      <div
        className="flex h-10 w-10 items-center justify-center rounded-xl"
        style={{ background: "var(--renk-bej-koyu)", color: "var(--renk-metin-orta)" }}
      >
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium" style={{ color: "var(--renk-metin-koyu)" }}>{title}</p>
        <p className="text-[11px]" style={{ color: "var(--renk-metin-soluk)" }}>{sub}</p>
      </div>
    </div>
  );
}
