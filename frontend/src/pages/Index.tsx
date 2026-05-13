import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Sun, Droplets, Wind, Camera, Sparkles, ArrowRight,
  Leaf, AlertTriangle, CheckCircle2, TrendingUp, Loader2, MapPin,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { plantsApi, diseaseRecordsApi, type Plant, type DiseaseRecord } from "@/services/api";
import { getUser } from "@/lib/auth";
import { fetchWeather, type WeatherData } from "@/lib/weather";

interface RecentAnalysis {
  id: string;
  plant: string;
  disease: string;
  confidence: number;
  severity: "high" | "med" | "ok";
  when: string;
}

export default function Dashboard() {
  const user = getUser();
  const userName = user?.name ?? "Çiftçi";
  const userCity = user?.city;

  const [plants, setPlants] = useState<Plant[]>([]);
  const [recentAnalyses, setRecentAnalyses] = useState<RecentAnalysis[]>([]);
  const [dataLoading, setDataLoading] = useState(true);

  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [weatherLoading, setWeatherLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
    loadWeather();
  }, []);

  const loadWeather = async () => {
    setWeatherLoading(true);
    if (userCity) {
      const data = await fetchWeather(userCity);
      setWeather(data);
    }
    setWeatherLoading(false);
  };

  const loadDashboardData = async () => {
    setDataLoading(true);
    try {
      const backendUserId = user?.backendUserId;
      if (!backendUserId) {
        // Henüz backend senkronizasyonu yapılmamış — boş göster
        setDataLoading(false);
        return;
      }

      const userPlants = await plantsApi.getByUser(backendUserId);
      setPlants(userPlants);

      const allRecords: (DiseaseRecord & { plant_name: string })[] = [];
      for (const plant of userPlants) {
        try {
          const records = await diseaseRecordsApi.getByPlant(plant.id);
          records.forEach((r) => allRecords.push({ ...r, plant_name: plant.plant_name }));
        } catch {
          // Kayıt olmayabilir
        }
      }

      const sorted = allRecords.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      const recent: RecentAnalysis[] = sorted.slice(0, 5).map((r) => ({
        id: `a-${r.id}`,
        plant: r.plant_name.split(" - ")[0],
        disease: r.disease_name,
        confidence: r.confidence_score ? Math.round(r.confidence_score * 100) : 0,
        severity: getSeverity(r.disease_name, r.confidence_score),
        when: formatTimeAgo(r.created_at),
      }));
      setRecentAnalyses(recent);
    } catch (err) {
      console.error("Dashboard veri yükleme hatası:", err);
    } finally {
      setDataLoading(false);
    }
  };

  const hasAnalyses = recentAnalyses.length > 0;
  const distribution = hasAnalyses ? calculateDistribution(recentAnalyses) : [];
  const total = distribution.reduce((s, d) => s + d.value, 0) || 1;
  const healthyPct = hasAnalyses
    ? Math.round((recentAnalyses.filter((a) => a.severity === "ok").length / recentAnalyses.length) * 100)
    : 0;

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Greeting + Weather */}
      <Card className="overflow-hidden rounded-3xl border-border/60 shadow-card">
        <CardContent className="bg-leaf-gradient p-5 text-primary-foreground">
          <p className="text-xs uppercase tracking-[0.18em] opacity-80">Bugün</p>
          <h2 className="mt-1 text-xl font-semibold">Merhaba, {userName} 👋</h2>
          <p className="mt-1 text-sm opacity-90">
            {userCity ? (
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {userCity}{user?.district ? `, ${user.district}` : ""}
              </span>
            ) : (
              "Tarlanın bugünkü durumunu kontrol et."
            )}
          </p>

          <div className="mt-4 grid grid-cols-3 gap-2">
            {weatherLoading ? (
              <>
                <WeatherSkeleton />
                <WeatherSkeleton />
                <WeatherSkeleton />
              </>
            ) : weather ? (
              <>
                <Stat icon={Sun} label={`${weather.temperature}°C`} sub="Sıcaklık" />
                <Stat icon={Droplets} label={`%${weather.humidity}`} sub="Nem" />
                <Stat icon={Wind} label={`${weather.windSpeed} km/s`} sub="Rüzgâr" />
              </>
            ) : (
              <div className="col-span-3 rounded-2xl bg-primary-foreground/15 px-3 py-2 text-xs opacity-80">
                {userCity
                  ? "Hava durumu alınamadı. İnternet bağlantınızı kontrol edin."
                  : "Profilde il bilgisi girildiğinde hava durumu burada görünür."}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Quick analyze CTA */}
      <Link to="/analysis/new">
        <Card className="rounded-3xl border-dashed border-primary/40 bg-card transition hover:bg-accent/40">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-leaf-gradient text-primary-foreground">
              <Camera className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-foreground">Yeni analiz başlat</p>
              <p className="text-xs text-muted-foreground">
                Bir yaprak fotoğrafı çek, AI saniyeler içinde teşhis koysun.
              </p>
            </div>
            <ArrowRight className="h-5 w-5 text-muted-foreground" />
          </CardContent>
        </Card>
      </Link>

      {/* Loading state */}
      {dataLoading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span className="ml-2 text-xs text-muted-foreground">Veriler yükleniyor...</span>
        </div>
      )}

      {/* Empty state — henüz analiz yok */}
      {!dataLoading && !hasAnalyses && (
        <Card className="rounded-3xl border-border/60 shadow-card">
          <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent text-accent-foreground">
              <Leaf className="h-7 w-7" />
            </div>
            <div>
              <p className="text-base font-semibold text-foreground">
                Henüz analiz yapmadınız
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                İlk tarla analizinizi başlatın ve AI'ın bitkilerinizi incelemesini izleyin.
              </p>
            </div>
            <Link to="/analysis/new" className="w-full">
              <Button className="h-12 w-full rounded-2xl bg-leaf-gradient text-sm font-semibold shadow-soft">
                <Camera className="mr-2 h-4 w-4" />
                Analiz Başlat
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Last AI result — sadece analiz varsa */}
      {!dataLoading && hasAnalyses && (
        <Card className="overflow-hidden rounded-3xl border-border/60 shadow-card">
          <CardContent className="p-0">
            <div className="flex items-center justify-between px-5 pt-5">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Son AI Analizi
                </p>
              </div>
              <Link
                to={`/analysis/${recentAnalyses[0].id}`}
                className="text-xs font-medium text-primary underline-offset-2 hover:underline"
              >
                Detay
              </Link>
            </div>

            <div className="relative mx-5 mt-3 h-44 overflow-hidden rounded-2xl bg-accent">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_40%,hsl(96_45%_55%)_0%,hsl(80_35%_40%)_55%,hsl(80_30%_25%)_100%)]" />
              <div className="absolute left-[18%] top-[28%] h-24 w-24 rounded-full bg-[radial-gradient(circle,hsl(12_85%_60%/0.85)_0%,hsl(35_90%_60%/0.6)_45%,transparent_70%)] blur-[2px]" />
              <div className="absolute right-[15%] bottom-[20%] h-20 w-20 rounded-full bg-[radial-gradient(circle,hsl(12_85%_60%/0.7)_0%,hsl(35_90%_60%/0.5)_50%,transparent_72%)] blur-[2px]" />
              <div className="absolute left-3 top-3 rounded-full bg-background/80 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-foreground backdrop-blur">
                Grad-CAM
              </div>
              <div className="absolute bottom-3 left-3 rounded-full bg-background/85 px-3 py-1 text-xs font-medium text-foreground backdrop-blur">
                AI bu bölgelere baktı
              </div>
            </div>

            <div className="space-y-3 p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-base font-semibold text-foreground">
                    {recentAnalyses[0].plant} · {recentAnalyses[0].disease}
                  </p>
                  <p className="text-xs text-muted-foreground">{recentAnalyses[0].when}</p>
                </div>
                <div className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  recentAnalyses[0].severity === "high"
                    ? "bg-destructive/10 text-destructive"
                    : recentAnalyses[0].severity === "med"
                    ? "bg-warning/15 text-warning"
                    : "bg-success/15 text-success"
                }`}>
                  %{recentAnalyses[0].confidence} Güven
                </div>
              </div>
              {recentAnalyses[0].severity !== "ok" && (
                <div className="flex items-center gap-2 rounded-2xl bg-accent/50 p-3 text-xs text-foreground">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-warning" />
                  Önümüzdeki 3 gün içinde yayılma riski yüksek. Bakır oksiklorür spreyi öneriliyor.
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Distribution + Field summary — sadece veri varsa */}
      {!dataLoading && (
        <div className="grid grid-cols-2 gap-3">
          {/* Hastalık Dağılımı */}
          <Card className="rounded-3xl border-border/60 shadow-card">
            <CardContent className="p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Hastalık Dağılımı
              </p>
              {hasAnalyses ? (
                <>
                  <div className="mt-3 flex h-2 overflow-hidden rounded-full">
                    {distribution.map((d) => (
                      <div
                        key={d.label}
                        style={{ width: `${(d.value / total) * 100}%`, background: d.color }}
                      />
                    ))}
                  </div>
                  <div className="mt-3 space-y-1.5">
                    {distribution.map((d) => (
                      <div key={d.label} className="flex items-center justify-between text-xs">
                        <span className="flex items-center gap-2 text-foreground">
                          <span className="h-2 w-2 rounded-full" style={{ background: d.color }} />
                          {d.label}
                        </span>
                        <span className="font-medium text-muted-foreground">%{d.value}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p className="mt-3 text-[11px] text-muted-foreground leading-relaxed">
                  Henüz analiz yapılmadı. İlk analizden sonra dağılım burada görünür.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Tarla Özeti */}
          <Card className="rounded-3xl border-border/60 shadow-card">
            <CardContent className="p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Tarla Özeti
              </p>
              <div className="mt-3 space-y-3">
                <FieldRow
                  icon={Leaf}
                  label="Aktif bitki"
                  value={String(plants.length)}
                />
                <FieldRow
                  icon={CheckCircle2}
                  label="Sağlıklı"
                  value={hasAnalyses ? `%${healthyPct}` : "—"}
                  tone={hasAnalyses ? "ok" : undefined}
                />
                <FieldRow
                  icon={TrendingUp}
                  label="Bu hafta"
                  value={`${recentAnalyses.length} analiz`}
                />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Son analizler listesi */}
      {!dataLoading && hasAnalyses && (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-semibold text-foreground">Son analizler</p>
            <Link to="/history" className="text-xs font-medium text-primary">
              Tümü
            </Link>
          </div>
          <div className="space-y-2">
            {recentAnalyses.map((a) => (
              <Link key={a.id} to={`/analysis/${a.id}`}>
                <Card className="rounded-2xl border-border/60 transition hover:bg-accent/30">
                  <CardContent className="flex items-center gap-3 p-3">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${
                      a.severity === "high"
                        ? "bg-destructive/10 text-destructive"
                        : a.severity === "med"
                        ? "bg-warning/15 text-warning"
                        : "bg-success/15 text-success"
                    }`}>
                      <Leaf className="h-4 w-4" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-foreground">
                        {a.plant} · {a.disease}
                      </p>
                      <p className="text-[11px] text-muted-foreground">{a.when}</p>
                    </div>
                    <span className="text-xs font-semibold text-muted-foreground">
                      %{a.confidence}
                    </span>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Chat CTA */}
      <Link to="/chat">
        <Card className="rounded-3xl border-primary/30 bg-card shadow-card transition hover:bg-accent/40">
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-leaf-gradient text-primary-foreground">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-foreground">
                AI'a sor: "Bu hastalık neden oldu?"
              </p>
              <p className="text-xs text-muted-foreground">
                Çiftçi diliyle, sade ve hızlı cevaplar.
              </p>
            </div>
            <ArrowRight className="h-5 w-5 text-primary" />
          </CardContent>
        </Card>
      </Link>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Yardımcı bileşenler
// ---------------------------------------------------------------------------

function WeatherSkeleton() {
  return (
    <div className="rounded-2xl bg-primary-foreground/15 p-3">
      <Skeleton className="mb-1 h-4 w-4 bg-primary-foreground/20" />
      <Skeleton className="h-4 w-10 bg-primary-foreground/20" />
      <Skeleton className="mt-1 h-2.5 w-8 bg-primary-foreground/20" />
    </div>
  );
}

function Stat({
  icon: Icon, label, sub,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  sub: string;
}) {
  return (
    <div className="rounded-2xl bg-primary-foreground/15 p-3 backdrop-blur">
      <Icon className="mb-1 h-4 w-4 opacity-90" />
      <p className="text-sm font-semibold leading-none">{label}</p>
      <p className="mt-1 text-[10px] opacity-80">{sub}</p>
    </div>
  );
}

function FieldRow({
  icon: Icon, label, value, tone,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  tone?: "ok";
}) {
  return (
    <div className="flex items-center gap-2">
      <span className={`flex h-7 w-7 items-center justify-center rounded-lg ${
        tone === "ok" ? "bg-success/15 text-success" : "bg-accent text-accent-foreground"
      }`}>
        <Icon className="h-3.5 w-3.5" />
      </span>
      <p className="flex-1 text-xs text-muted-foreground">{label}</p>
      <p className="text-xs font-semibold text-foreground">{value}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Yardımcı fonksiyonlar
// ---------------------------------------------------------------------------

function getSeverity(disease: string, score: number | null): "high" | "med" | "ok" {
  if (disease === "Sağlıklı" || disease === "Healthy") return "ok";
  if (score && score > 0.85) return "high";
  return "med";
}

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  if (hours < 1) return "Az önce";
  if (hours < 24) return `${hours} saat önce`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "Dün";
  return `${days} gün önce`;
}

function calculateDistribution(analyses: RecentAnalysis[]) {
  const ok = analyses.filter((a) => a.severity === "ok").length;
  const med = analyses.filter((a) => a.severity === "med").length;
  const high = analyses.filter((a) => a.severity === "high").length;
  const t = analyses.length;
  return [
    { label: "Sağlıklı", value: Math.round((ok / t) * 100), color: "hsl(96 38% 45%)" },
    { label: "Erken Uyarı", value: Math.round((med / t) * 100), color: "hsl(35 85% 55%)" },
    { label: "Hastalıklı", value: Math.round((high / t) * 100), color: "hsl(12 65% 52%)" },
  ].filter((d) => d.value > 0);
}
