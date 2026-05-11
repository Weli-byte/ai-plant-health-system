import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Filter, Leaf, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { plantsApi, diseaseRecordsApi, type Plant, type DiseaseRecord } from "@/services/api";

interface HistoryItem {
  id: string;
  plant: string;
  disease: string;
  confidence: number;
  when: string;
  tone: "ok" | "warn" | "bad";
}

const toneMap = {
  ok: "bg-success/15 text-success",
  warn: "bg-warning/15 text-warning",
  bad: "bg-destructive/15 text-destructive",
} as const;

export default function AnalysisHistory() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const userPlants = await plantsApi.getByUser(1);
      const allItems: HistoryItem[] = [];

      for (const plant of userPlants) {
        try {
          const records = await diseaseRecordsApi.getByPlant(plant.id);
          records.forEach((r) => {
            allItems.push({
              id: `a-${r.id}`,
              plant: plant.plant_name.split(" - ")[0],
              disease: r.disease_name,
              confidence: r.confidence_score ? Math.round(r.confidence_score * 100) : 0,
              when: formatTimeAgo(r.created_at),
              tone: getTone(r.disease_name, r.confidence_score),
            });
          });
        } catch {
          // Kayıt olmayabilir
        }
      }

      // Tarihe göre sırala (en yeniler önce)
      allItems.sort((a, b) => {
        // id'deki numaraya göre (a-5 > a-1)
        const idA = parseInt(a.id.split("-")[1]);
        const idB = parseInt(b.id.split("-")[1]);
        return idB - idA;
      });

      setItems(allItems);
    } catch (err) {
      console.error("Geçmiş yükleme hatası:", err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = items.filter(
    (i) =>
      i.plant.toLowerCase().includes(q.toLowerCase()) ||
      i.disease.toLowerCase().includes(q.toLowerCase())
  );

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Bitki veya hastalık ara"
            className="h-11 rounded-2xl border-border/60 bg-card pl-9"
          />
        </div>
        <button className="flex h-11 w-11 items-center justify-center rounded-2xl bg-card text-foreground shadow-card">
          <Filter className="h-4 w-4" />
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span className="ml-2 text-sm text-muted-foreground">Geçmiş yükleniyor...</span>
        </div>
      )}

      {!loading && (
        <div className="space-y-2">
          {filtered.map((a) => (
            <Link key={a.id} to={`/analysis/${a.id}`}>
              <Card className="rounded-2xl border-border/60 transition hover:bg-accent/30">
                <CardContent className="flex items-center gap-3 p-3">
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-xl ${
                      toneMap[a.tone]
                    }`}
                  >
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
          {filtered.length === 0 && (
            <p className="py-10 text-center text-sm text-muted-foreground">
              Sonuç bulunamadı.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function getTone(disease: string, score: number | null): "ok" | "warn" | "bad" {
  if (disease === "Sağlıklı" || disease === "Healthy") return "ok";
  if (score && score > 0.85) return "bad";
  return "warn";
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
