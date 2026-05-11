import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Sprout, Sun, Droplets, Wheat, Loader2, Leaf } from "lucide-react";
import { sprint3Api, type FarmingAdviceResponse } from "@/services/api";

const seasons = [
  { value: "spring", label: "İlkbahar" },
  { value: "summer", label: "Yaz" },
  { value: "autumn", label: "Sonbahar" },
  { value: "winter", label: "Kış" },
];

const defaultMonths = [
  { name: "Mart", crop: "Domates fidesi", icon: Sprout, tone: "leaf" },
  { name: "Nisan", crop: "Biber, patlıcan", icon: Sprout, tone: "leaf" },
  { name: "Mayıs", crop: "Mısır, fasulye", icon: Wheat, tone: "earth" },
  { name: "Haziran", crop: "Salatalık, kabak", icon: Droplets, tone: "leaf" },
  { name: "Temmuz", crop: "Bakım & sulama", icon: Sun, tone: "earth" },
  { name: "Ağustos", crop: "Hasat dönemi", icon: Wheat, tone: "earth" },
];

export default function Planning() {
  const [season, setSeason] = useState("spring");
  const [loading, setLoading] = useState(false);
  const [advice, setAdvice] = useState<FarmingAdviceResponse | null>(null);

  const loadAdvice = async () => {
    setLoading(true);
    try {
      const data = await sprint3Api.getFarmingAdvice({
        temperature: season === "summer" ? 32 : season === "winter" ? 8 : 22,
        humidity: season === "spring" ? 65 : season === "autumn" ? 78 : 55,
        rainfall: season === "spring" ? 15 : season === "winter" ? 25 : 5,
        wind_speed: 10,
        season,
        plant_health_status: "healthy",
        crop_type: "tomato",
      });
      setAdvice(data);
    } catch (err) {
      console.error("Danışma hatası:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Mevsim seçici kart */}
      <Card className="rounded-3xl border-border/60 bg-leaf-gradient text-primary-foreground shadow-card">
        <CardContent className="p-5">
          <p className="text-xs uppercase tracking-[0.18em] opacity-80">Mevsim</p>
          <p className="mt-1 text-xl font-semibold">
            {seasons.find((s) => s.value === season)?.label} 2026
          </p>
          <p className="mt-1 text-sm opacity-90">
            Bölgenize özel ekim takvimi ve bakım önerileri.
          </p>
          <div className="mt-4 grid grid-cols-4 gap-2">
            {seasons.map((s) => (
              <button
                key={s.value}
                onClick={() => { setSeason(s.value); setAdvice(null); }}
                className={`rounded-xl py-2 text-xs font-semibold transition ${
                  season === s.value
                    ? "bg-primary-foreground/25 shadow-sm"
                    : "bg-primary-foreground/10 hover:bg-primary-foreground/15"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* AI Danışma butonu */}
      <Button
        onClick={loadAdvice}
        disabled={loading}
        className="h-12 w-full rounded-2xl bg-primary text-base font-semibold shadow-soft"
      >
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            AI önerileri yükleniyor...
          </>
        ) : (
          <>
            <Leaf className="mr-2 h-4 w-4" />
            AI Tarım Önerileri Al
          </>
        )}
      </Button>

      {/* API'den gelen öneriler */}
      {advice && (
        <Card className="rounded-3xl border-primary/30 shadow-card">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-foreground">AI Tarım Danışma Raporu</p>
              <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase ${
                advice.risk_level === "High"
                  ? "bg-destructive/15 text-destructive"
                  : advice.risk_level === "Medium"
                  ? "bg-warning/15 text-warning"
                  : "bg-success/15 text-success"
              }`}>
                {advice.risk_level} Risk
              </span>
            </div>

            {advice.farming_advice.map((tip, idx) => (
              <div key={idx} className="rounded-2xl bg-accent/50 p-3 text-xs text-foreground">
                {tip}
              </div>
            ))}

            {advice.pesticide_recommendations.length > 0 && (
              <div className="space-y-2 pt-2">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  İlaç Önerileri
                </p>
                {advice.pesticide_recommendations.map((p, idx) => (
                  <div key={idx} className="rounded-2xl bg-green-50 dark:bg-green-950/30 p-3 text-xs">
                    <p className="font-semibold text-foreground">{p.product_name}</p>
                    <p className="text-muted-foreground">{p.active_ingredient} — {p.application_notes}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="rounded-2xl bg-blue-50 dark:bg-blue-950/30 p-3 text-xs text-foreground">
              💧 {advice.irrigation_advice}
            </div>

            <p className="text-[11px] text-muted-foreground italic">{advice.general_notes}</p>
          </CardContent>
        </Card>
      )}

      {/* Aylık takvim */}
      <p className="px-1 text-sm font-semibold text-foreground">Aylık takvim</p>

      {defaultMonths.map((m) => (
        <Card key={m.name} className="rounded-3xl border-border/60 shadow-card">
          <CardContent className="flex items-center gap-3 p-4">
            <div
              className={`flex h-12 w-12 items-center justify-center rounded-2xl ${
                m.tone === "leaf"
                  ? "bg-leaf-gradient text-primary-foreground"
                  : "bg-secondary text-secondary-foreground"
              }`}
            >
              <m.icon className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-foreground">{m.name}</p>
              <p className="text-xs text-muted-foreground">{m.crop}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
