import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Sprout, Droplets, Sun, Loader2, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { plantsApi, type Plant } from "@/services/api";

const toneMap = {
  ok: "bg-success/15 text-success",
  warn: "bg-warning/15 text-warning",
  bad: "bg-destructive/15 text-destructive",
} as const;

export default function Plants() {
  const [plants, setPlants] = useState<Plant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Yeni bitki ekleme formu
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [adding, setAdding] = useState(false);

  // Bitkileri API'den çek
  const fetchPlants = async () => {
    setLoading(true);
    setError(null);
    try {
      // user_id=1 (mock auth — login olmadığı için sabit)
      const data = await plantsApi.getByUser(1);
      setPlants(data);
    } catch (err) {
      console.error("Bitki yükleme hatası:", err);
      setError("Bitkiler yüklenemedi. Sunucu bağlantısını kontrol edin.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlants();
  }, []);

  // Yeni bitki ekle
  const handleAdd = async () => {
    if (!newName.trim()) return;
    setAdding(true);
    try {
      await plantsApi.create({ plant_name: newName.trim(), user_id: 1 });
      setNewName("");
      setShowForm(false);
      await fetchPlants(); // Listeyi yenile
    } catch (err) {
      console.error("Bitki ekleme hatası:", err);
      alert("Bitki eklenemedi. Lütfen tekrar deneyin.");
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Yeni bitki ekle butonu / formu */}
      {!showForm ? (
        <Button
          onClick={() => setShowForm(true)}
          className="h-12 w-full rounded-2xl bg-leaf-gradient text-base font-semibold shadow-soft"
        >
          <Plus className="mr-2 h-4 w-4" /> Yeni bitki ekle
        </Button>
      ) : (
        <Card className="rounded-3xl border-primary/40 border-dashed shadow-card">
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-foreground">Yeni Bitki Ekle</p>
              <button onClick={() => setShowForm(false)} className="text-muted-foreground hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Bitki adı (örn: Domates - 3. Sera)"
              className="h-11 rounded-2xl border-border/60 bg-background"
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            />
            <Button
              onClick={handleAdd}
              disabled={adding || !newName.trim()}
              className="h-10 w-full rounded-2xl bg-leaf-gradient font-semibold shadow-soft"
            >
              {adding ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}
              {adding ? "Ekleniyor..." : "Ekle"}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Yükleniyor */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="ml-2 text-sm text-muted-foreground">Bitkiler yükleniyor...</span>
        </div>
      )}

      {/* Hata */}
      {error && (
        <Card className="rounded-2xl border-destructive/30 bg-destructive/5">
          <CardContent className="p-4 text-center">
            <p className="text-sm text-destructive">{error}</p>
            <Button onClick={fetchPlants} variant="outline" size="sm" className="mt-2 rounded-xl">
              Tekrar dene
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Bitki listesi */}
      {!loading && !error && plants.length === 0 && (
        <div className="py-12 text-center">
          <Sprout className="mx-auto h-10 w-10 text-muted-foreground/40" />
          <p className="mt-3 text-sm text-muted-foreground">Henüz bitki eklenmemiş.</p>
          <p className="text-xs text-muted-foreground">Yukarıdaki butona tıklayarak ilk bitkinizi ekleyin.</p>
        </div>
      )}

      {!loading &&
        plants.map((p) => (
          <Link key={p.id} to={`/analysis/p-${p.id}`}>
            <Card className="rounded-3xl border-border/60 shadow-card transition hover:bg-accent/30">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-leaf-gradient text-primary-foreground">
                    <Sprout className="h-5 w-5" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-foreground">{p.plant_name}</p>
                      <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${toneMap.ok}`}>
                        Aktif
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      Eklenme: {new Date(p.created_at).toLocaleDateString("tr-TR")}
                    </p>
                    <div className="mt-3 flex gap-2">
                      <Pill icon={Droplets} text="Sulama: Belirsiz" />
                      <Pill icon={Sun} text="Tam güneş" />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
    </div>
  );
}

function Pill({
  icon: Icon,
  text,
}: {
  icon: React.ComponentType<{ className?: string }>;
  text: string;
}) {
  return (
    <span className="flex items-center gap-1.5 rounded-full bg-accent/60 px-2.5 py-1 text-[11px] font-medium text-accent-foreground">
      <Icon className="h-3 w-3" />
      {text}
    </span>
  );
}
