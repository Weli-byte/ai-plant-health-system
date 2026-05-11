import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Sparkles, Pill, TrendingUp, AlertTriangle, CheckCircle2, Clock, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { plantsApi, diseaseRecordsApi, sprint3Api, type DiseaseRecord, type FarmingAdviceResponse } from "@/services/api";

const toneIcon = { ok: CheckCircle2, warn: Clock, bad: AlertTriangle };
const toneCls = {
  ok: "bg-success/15 text-success",
  warn: "bg-warning/15 text-warning",
  bad: "bg-destructive/15 text-destructive",
};

const timeline = [
  { day: "Bugün", text: "Erken evre lekeler", tone: "warn" },
  { day: "+3 gün", text: "Yayılma riski yüksek", tone: "bad" },
  { day: "+7 gün", text: "Müdahale yoksa yaprak kaybı", tone: "bad" },
  { day: "+14 gün", text: "Tedaviyle iyileşme", tone: "ok" },
];

export default function AnalysisResult() {
  const { id } = useParams();
  const [record, setRecord] = useState<(DiseaseRecord & { plant_name: string }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [advice, setAdvice] = useState<FarmingAdviceResponse | null>(null);
  const [adviceLoading, setAdviceLoading] = useState(false);

  useEffect(() => {
    loadRecord();
  }, [id]);

  const loadRecord = async () => {
    setLoading(true);
    try {
      // id format: "a-3" → record id = 3
      const recordId = id?.startsWith("a-") ? parseInt(id.split("-")[1]) : parseInt(id || "0");

      // Tüm bitkilerin kayıtlarını tara ve eşleşeni bul
      const plants = await plantsApi.getByUser(1);
      for (const plant of plants) {
        try {
          const records = await diseaseRecordsApi.getByPlant(plant.id);
          const found = records.find((r) => r.id === recordId);
          if (found) {
            setRecord({ ...found, plant_name: plant.plant_name.split(" - ")[0] });
            break;
          }
        } catch {
          // devam
        }
      }
    } catch (err) {
      console.error("Kayıt yükleme hatası:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadAdvice = async () => {
    if (!record) return;
    setAdviceLoading(true);
    try {
      const data = await sprint3Api.getFarmingAdvice({
        temperature: 24,
        humidity: 72,
        rainfall: 12,
        wind_speed: 8,
        season: "spring",
        plant_health_status: record.disease_name === "Sağlıklı" ? "healthy" : "diseased",
        disease_name: record.disease_name,
      });
      setAdvice(data);
    } catch (err) {
      console.error("Danışma hatası:", err);
    } finally {
      setAdviceLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <span className="ml-2 text-sm text-muted-foreground">Yükleniyor...</span>
      </div>
    );
  }

  const diseaseName = record?.disease_name || "Bilinmiyor";
  const confidence = record?.confidence_score ? Math.round(record.confidence_score * 100) : 0;
  const plantName = record?.plant_name || "Bitki";
  const isHealthy = diseaseName === "Sağlıklı" || diseaseName === "Healthy";

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center gap-2">
        <Link to="/history">
          <Button variant="ghost" size="icon" className="rounded-full">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Analiz #{id}</p>
          <p className="text-sm font-semibold text-foreground">
            {plantName} · {diseaseName}
          </p>
        </div>
      </div>

      {/* Grad-CAM image placeholder */}
      <Card className="overflow-hidden rounded-3xl border-border/60 shadow-card">
        <CardContent className="p-0">
          <div className="relative h-56 bg-[radial-gradient(circle_at_30%_40%,hsl(96_45%_55%)_0%,hsl(80_35%_40%)_55%,hsl(80_30%_25%)_100%)]">
            {!isHealthy && (
              <>
                <div className="absolute left-[20%] top-[28%] h-28 w-28 rounded-full bg-[radial-gradient(circle,hsl(12_85%_60%/0.85)_0%,hsl(35_90%_60%/0.6)_45%,transparent_70%)] blur-[2px]" />
                <div className="absolute right-[18%] bottom-[18%] h-20 w-20 rounded-full bg-[radial-gradient(circle,hsl(12_85%_60%/0.7)_0%,hsl(35_90%_60%/0.5)_50%,transparent_72%)] blur-[2px]" />
              </>
            )}
            <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-background/85 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-foreground backdrop-blur">
              <Sparkles className="h-3 w-3 text-primary" /> Grad-CAM
            </div>
            <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between rounded-2xl bg-background/85 px-3 py-2 backdrop-blur">
              <span className="text-xs font-medium text-foreground">
                {isHealthy ? "Sağlıklı bitki" : "AI bu bölgelere odaklandı"}
              </span>
              <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[11px] font-bold text-primary">
                %{confidence}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary */}
      <Card className="rounded-3xl border-border/60 shadow-card">
        <CardContent className="space-y-2 p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Teşhis
          </p>
          <p className="text-sm leading-relaxed text-foreground">
            {isHealthy
              ? `${plantName} bitkisi sağlıklı görünüyor. Herhangi bir hastalık belirtisi tespit edilmedi.`
              : `${diseaseName} tespit edildi. Güven skoru %${confidence}. Aşağıdaki önerileri dikkate alın.`}
          </p>
        </CardContent>
      </Card>

      {/* Timeline — sadece hastalıklıysa göster */}
      {!isHealthy && (
        <div>
          <div className="mb-2 flex items-center gap-2 px-1">
            <TrendingUp className="h-4 w-4 text-primary" />
            <p className="text-sm font-semibold text-foreground">Gelecek tahmini</p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {timeline.map((t, i) => {
              const Icon = toneIcon[t.tone as keyof typeof toneIcon];
              return (
                <Card key={i} className="rounded-2xl border-border/60">
                  <CardContent className="p-3">
                    <div className={`mb-2 inline-flex h-8 w-8 items-center justify-center rounded-lg ${toneCls[t.tone as keyof typeof toneCls]}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <p className="text-xs font-semibold text-foreground">{t.day}</p>
                    <p className="text-[11px] text-muted-foreground">{t.text}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Meds — API'den */}
      {!isHealthy && (
        <div>
          <div className="mb-2 flex items-center gap-2 px-1">
            <Pill className="h-4 w-4 text-primary" />
            <p className="text-sm font-semibold text-foreground">Önerilen müdahaleler</p>
          </div>

          {!advice ? (
            <Button
              onClick={loadAdvice}
              disabled={adviceLoading}
              variant="outline"
              className="h-11 w-full rounded-2xl border-border/60 font-semibold"
            >
              {adviceLoading ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Yükleniyor...</>
              ) : (
                "AI Tarım Önerileri Al"
              )}
            </Button>
          ) : (
            <div className="space-y-2">
              {advice.pesticide_recommendations.map((m) => (
                <Card key={m.product_name} className="rounded-2xl border-border/60">
                  <CardContent className="p-4">
                    <p className="text-sm font-semibold text-foreground">{m.product_name}</p>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Etken Madde</p>
                        <p className="text-xs text-foreground">{m.active_ingredient}</p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Uygulama</p>
                        <p className="text-xs text-foreground">{m.application_notes}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {advice.farming_advice.map((tip, idx) => (
                <div key={idx} className="rounded-2xl bg-accent/50 p-3 text-xs text-foreground">{tip}</div>
              ))}
              <div className="rounded-2xl bg-blue-50 dark:bg-blue-950/30 p-3 text-xs text-foreground">
                💧 {advice.irrigation_advice}
              </div>
            </div>
          )}
        </div>
      )}

      <Link to="/chat">
        <Button className="h-12 w-full rounded-2xl bg-leaf-gradient text-base font-semibold shadow-soft">
          <Sparkles className="mr-2 h-4 w-4" /> AI'a bunu sor
        </Button>
      </Link>
    </div>
  );
}
