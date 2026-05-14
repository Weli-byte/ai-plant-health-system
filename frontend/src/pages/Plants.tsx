import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus, Sprout, Loader2, X, ArrowLeft, ArrowRight, Check,
  Droplets, MapPin, Calendar, Ruler, Camera,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { plantsApi, type Plant } from "@/services/api";
import { getUser } from "@/lib/auth";

// ---------------------------------------------------------------------------
// Sabitler
// ---------------------------------------------------------------------------

const PLANT_OPTIONS = [
  { type: "Domates", emoji: "🍅" },
  { type: "Elma", emoji: "🍎" },
  { type: "Buğday", emoji: "🌾" },
  { type: "Mısır", emoji: "🌽" },
  { type: "Kayısı", emoji: "🍑" },
  { type: "Üzüm", emoji: "🍇" },
  { type: "Zeytin", emoji: "🫒" },
  { type: "Biber", emoji: "🫑" },
  { type: "Çilek", emoji: "🍓" },
  { type: "Patates", emoji: "🥔" },
  { type: "Salatalık", emoji: "🥒" },
  { type: "Portakal", emoji: "🍊" },
];

const GROWTH_STAGES = [
  { id: "seedling", label: "Fide", emoji: "🌱" },
  { id: "vegetative", label: "Vejetatif", emoji: "🌿" },
  { id: "flowering", label: "Çiçeklenme", emoji: "🌸" },
  { id: "fruiting", label: "Meyve", emoji: "🍅" },
  { id: "harvest", label: "Hasat", emoji: "✂️" },
];

const IRRIGATION_METHODS = [
  { id: "drip", label: "Damla" },
  { id: "sprinkler", label: "Yağmurlama" },
  { id: "furrow", label: "Karık" },
  { id: "manual", label: "Elle" },
];

const IRRIGATION_FREQS = [
  { id: "daily", label: "Günlük" },
  { id: "every2days", label: "2 Günde Bir" },
  { id: "weekly", label: "Haftalık" },
];

const STAGE_ORDER = ["seedling", "vegetative", "flowering", "fruiting", "harvest"];

const IRRIGATION_FREQ_TR: Record<string, string> = {
  daily: "Günlük", every2days: "2 günde bir", weekly: "Haftalık",
};
const IRRIGATION_METHOD_TR: Record<string, string> = {
  drip: "Damla sulama", sprinkler: "Yağmurlama", furrow: "Karık", manual: "Elle sulama",
};

// ---------------------------------------------------------------------------
// Tip yardımcısı
// ---------------------------------------------------------------------------

function getUserId(): number {
  const user = getUser();
  return user?.backendUserId ?? 1;
}

// ---------------------------------------------------------------------------
// Bileşen
// ---------------------------------------------------------------------------

export default function Plants() {
  const navigate = useNavigate();
  const [plants, setPlants] = useState<Plant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Wizard state
  const [showWizard, setShowWizard] = useState(false);
  const [wizardStep, setWizardStep] = useState<1 | 2 | 3>(1);
  const [adding, setAdding] = useState(false);

  // Step 1
  const [selectedType, setSelectedType] = useState("");
  const [selectedEmoji, setSelectedEmoji] = useState("");
  const [isOther, setIsOther] = useState(false);
  const [customName, setCustomName] = useState("");

  // Step 2
  const [plantingDate, setPlantingDate] = useState("");
  const [locationStr, setLocationStr] = useState("");
  const [growthStage, setGrowthStage] = useState("");
  const [irrigationMethod, setIrrigationMethod] = useState("");
  const [irrigationFreq, setIrrigationFreq] = useState("");
  const [areaSize, setAreaSize] = useState("");
  const [notes, setNotes] = useState("");

  const fetchPlants = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await plantsApi.getByUser(getUserId());
      setPlants(data);
    } catch (err) {
      console.error("Bitki yükleme hatası:", err);
      setError("Bitkiler yüklenemedi. Sunucu bağlantısını kontrol edin.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPlants(); }, [fetchPlants]);

  const resetWizard = () => {
    setWizardStep(1);
    setSelectedType(""); setSelectedEmoji(""); setIsOther(false); setCustomName("");
    setPlantingDate(""); setLocationStr(""); setGrowthStage("");
    setIrrigationMethod(""); setIrrigationFreq(""); setAreaSize(""); setNotes("");
  };

  const openWizard = () => { resetWizard(); setShowWizard(true); };
  const closeWizard = () => { setShowWizard(false); resetWizard(); };

  const canGoNext1 = isOther ? customName.trim().length > 0 : selectedType.length > 0;
  const canGoNext2 = true; // tüm step-2 alanları opsiyonel

  const handleSave = async () => {
    setAdding(true);
    const finalType = isOther ? customName.trim() : selectedType;
    const finalEmoji = isOther ? "🌱" : selectedEmoji;
    const plantName = `${finalEmoji} ${finalType}`;

    try {
      await plantsApi.create({
        plant_name: plantName,
        user_id: getUserId(),
        plant_type: finalType,
        plant_emoji: finalEmoji,
        planting_date: plantingDate || undefined,
        location: locationStr.trim() || undefined,
        growth_stage: growthStage || undefined,
        irrigation_method: irrigationMethod || undefined,
        irrigation_frequency: irrigationFreq || undefined,
        area_size: areaSize ? parseFloat(areaSize) : undefined,
        notes: notes.trim() || undefined,
      });
      await fetchPlants();
      closeWizard();
    } catch (err) {
      console.error("Bitki ekleme hatası:", err);
      alert(`Bitki eklenemedi: ${err instanceof Error ? err.message : "Bilinmeyen hata"}`);
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Wizard */}
      {showWizard && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 backdrop-blur-sm sm:items-center"
          onClick={(e) => e.target === e.currentTarget && closeWizard()}>
          <div className="w-full max-w-sm rounded-t-3xl sm:rounded-3xl bg-card border border-border/60 shadow-2xl overflow-hidden animate-slide-up">
            {/* Step indicator */}
            <div className="flex items-center justify-between px-5 pt-5 pb-2">
              <button onClick={closeWizard} className="flex h-8 w-8 items-center justify-center rounded-full bg-muted/60 text-muted-foreground hover:text-foreground transition">
                <X className="h-4 w-4" />
              </button>
              <div className="flex items-center gap-2">
                {[1, 2, 3].map((s) => (
                  <div key={s} className={`h-2 rounded-full transition-all ${wizardStep === s ? "w-6 bg-primary" : wizardStep > s ? "w-2 bg-primary/60" : "w-2 bg-muted"}`} />
                ))}
              </div>
              <p className="text-xs font-semibold text-muted-foreground">{wizardStep}/3</p>
            </div>

            <div className="px-5 pb-6 space-y-4 max-h-[75dvh] overflow-y-auto">

              {/* ── Adım 1: Bitki Seç ── */}
              {wizardStep === 1 && (
                <>
                  <div>
                    <h2 className="text-lg font-bold text-foreground">Bitki Türü Seç</h2>
                    <p className="text-xs text-muted-foreground mt-0.5">Hangi bitkiyi takip ediyorsunuz?</p>
                  </div>
                  <div className="grid grid-cols-4 gap-2">
                    {PLANT_OPTIONS.map((p) => (
                      <button
                        key={p.type}
                        onClick={() => { setSelectedType(p.type); setSelectedEmoji(p.emoji); setIsOther(false); }}
                        className={`flex flex-col items-center gap-1 rounded-2xl p-2.5 text-center transition border ${
                          selectedType === p.type && !isOther
                            ? "border-primary bg-primary/10"
                            : "border-border/60 bg-muted/30 hover:bg-muted/60"
                        }`}
                      >
                        <span className="text-2xl">{p.emoji}</span>
                        <span className="text-[10px] font-medium text-foreground leading-tight">{p.type}</span>
                      </button>
                    ))}
                    <button
                      onClick={() => { setIsOther(true); setSelectedType(""); }}
                      className={`flex flex-col items-center gap-1 rounded-2xl p-2.5 text-center transition border ${
                        isOther
                          ? "border-primary bg-primary/10"
                          : "border-border/60 bg-muted/30 hover:bg-muted/60"
                      }`}
                    >
                      <span className="text-2xl">➕</span>
                      <span className="text-[10px] font-medium text-foreground">Diğer</span>
                    </button>
                  </div>

                  {isOther && (
                    <input
                      value={customName}
                      onChange={(e) => setCustomName(e.target.value)}
                      placeholder="Bitki adını girin..."
                      className="w-full rounded-2xl border border-border/60 bg-background px-4 py-3 text-sm outline-none focus:border-primary transition"
                      autoFocus
                    />
                  )}

                  <Button
                    onClick={() => setWizardStep(2)}
                    disabled={!canGoNext1}
                    className="h-12 w-full rounded-2xl bg-leaf-gradient font-semibold shadow-soft"
                  >
                    Devam Et <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </>
              )}

              {/* ── Adım 2: Detaylar ── */}
              {wizardStep === 2 && (
                <>
                  <div className="flex items-center gap-2">
                    <button onClick={() => setWizardStep(1)} className="flex h-8 w-8 items-center justify-center rounded-full bg-muted/60 text-muted-foreground">
                      <ArrowLeft className="h-4 w-4" />
                    </button>
                    <div>
                      <h2 className="text-lg font-bold text-foreground">Detaylar</h2>
                      <p className="text-xs text-muted-foreground">Tüm alanlar opsiyonel</p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {/* Ekim tarihi */}
                    <div>
                      <label className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground mb-1.5">
                        <Calendar className="h-3.5 w-3.5" /> Ekim / Dikim Tarihi
                      </label>
                      <input
                        type="date"
                        value={plantingDate}
                        onChange={(e) => setPlantingDate(e.target.value)}
                        className="w-full rounded-2xl border border-border/60 bg-background px-4 py-2.5 text-sm outline-none focus:border-primary transition"
                      />
                    </div>

                    {/* Konum */}
                    <div>
                      <label className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground mb-1.5">
                        <MapPin className="h-3.5 w-3.5" /> Tarla / Konum
                      </label>
                      <input
                        value={locationStr}
                        onChange={(e) => setLocationStr(e.target.value)}
                        placeholder="örn: 1. Sera, Kuzey Tarla"
                        className="w-full rounded-2xl border border-border/60 bg-background px-4 py-2.5 text-sm outline-none focus:border-primary transition"
                      />
                    </div>

                    {/* Büyüme evresi */}
                    <div>
                      <p className="text-xs font-semibold text-muted-foreground mb-1.5">Büyüme Evresi</p>
                      <div className="flex gap-1.5">
                        {GROWTH_STAGES.map((s) => (
                          <button
                            key={s.id}
                            onClick={() => setGrowthStage(s.id)}
                            className={`flex flex-1 flex-col items-center gap-1 rounded-xl py-2 text-center text-[10px] font-medium transition border ${
                              growthStage === s.id
                                ? "border-primary bg-primary/10 text-primary"
                                : "border-border/50 bg-muted/30 text-muted-foreground hover:bg-muted/60"
                            }`}
                          >
                            <span className="text-base">{s.emoji}</span>
                            <span className="leading-tight">{s.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Sulama yöntemi */}
                    <div>
                      <label className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground mb-1.5">
                        <Droplets className="h-3.5 w-3.5" /> Sulama Yöntemi
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        {IRRIGATION_METHODS.map((m) => (
                          <button
                            key={m.id}
                            onClick={() => setIrrigationMethod(m.id)}
                            className={`rounded-xl py-2 text-sm font-medium transition border ${
                              irrigationMethod === m.id
                                ? "border-primary bg-primary/10 text-primary"
                                : "border-border/60 bg-muted/30 text-muted-foreground hover:bg-muted/60"
                            }`}
                          >
                            {m.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Sulama sıklığı */}
                    <div>
                      <p className="text-xs font-semibold text-muted-foreground mb-1.5">Sulama Sıklığı</p>
                      <div className="flex gap-2">
                        {IRRIGATION_FREQS.map((f) => (
                          <button
                            key={f.id}
                            onClick={() => setIrrigationFreq(f.id)}
                            className={`flex-1 rounded-xl py-2 text-xs font-medium transition border ${
                              irrigationFreq === f.id
                                ? "border-primary bg-primary/10 text-primary"
                                : "border-border/60 bg-muted/30 text-muted-foreground hover:bg-muted/60"
                            }`}
                          >
                            {f.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Alan büyüklüğü */}
                    <div>
                      <label className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground mb-1.5">
                        <Ruler className="h-3.5 w-3.5" /> Alan Büyüklüğü (dönüm)
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="0.5"
                        value={areaSize}
                        onChange={(e) => setAreaSize(e.target.value)}
                        placeholder="örn: 2.5"
                        className="w-full rounded-2xl border border-border/60 bg-background px-4 py-2.5 text-sm outline-none focus:border-primary transition"
                      />
                    </div>

                    {/* Notlar */}
                    <div>
                      <p className="text-xs font-semibold text-muted-foreground mb-1.5">Notlar (opsiyonel)</p>
                      <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Ek bilgi varsa buraya yazın..."
                        rows={2}
                        className="w-full rounded-2xl border border-border/60 bg-background px-4 py-2.5 text-sm outline-none focus:border-primary resize-none transition"
                      />
                    </div>
                  </div>

                  <Button
                    onClick={() => setWizardStep(3)}
                    disabled={!canGoNext2}
                    className="h-12 w-full rounded-2xl bg-leaf-gradient font-semibold shadow-soft"
                  >
                    Özeti Gör <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </>
              )}

              {/* ── Adım 3: Özet ── */}
              {wizardStep === 3 && (
                <>
                  <div className="flex items-center gap-2">
                    <button onClick={() => setWizardStep(2)} className="flex h-8 w-8 items-center justify-center rounded-full bg-muted/60 text-muted-foreground">
                      <ArrowLeft className="h-4 w-4" />
                    </button>
                    <div>
                      <h2 className="text-lg font-bold text-foreground">Özet</h2>
                      <p className="text-xs text-muted-foreground">Bilgileri kontrol edin</p>
                    </div>
                  </div>

                  {/* Bitki başlığı */}
                  <div className="flex items-center gap-3 rounded-2xl bg-muted/40 p-4">
                    <span className="text-4xl">{isOther ? "🌱" : selectedEmoji}</span>
                    <div>
                      <p className="font-bold text-foreground">{isOther ? customName : selectedType}</p>
                      {locationStr && <p className="text-xs text-muted-foreground">{locationStr}</p>}
                    </div>
                  </div>

                  <div className="space-y-2 text-sm">
                    {plantingDate && (
                      <SummaryRow label="Ekim tarihi" value={new Date(plantingDate).toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" })} />
                    )}
                    {growthStage && (
                      <SummaryRow label="Büyüme evresi" value={GROWTH_STAGES.find(s => s.id === growthStage)?.label ?? growthStage} />
                    )}
                    {irrigationMethod && (
                      <SummaryRow label="Sulama yöntemi" value={IRRIGATION_METHOD_TR[irrigationMethod] ?? irrigationMethod} />
                    )}
                    {irrigationFreq && (
                      <SummaryRow label="Sulama sıklığı" value={IRRIGATION_FREQ_TR[irrigationFreq] ?? irrigationFreq} />
                    )}
                    {areaSize && (
                      <SummaryRow label="Alan büyüklüğü" value={`${areaSize} dönüm`} />
                    )}
                    {notes && (
                      <SummaryRow label="Notlar" value={notes} />
                    )}
                  </div>

                  <Button
                    onClick={handleSave}
                    disabled={adding}
                    className="h-12 w-full rounded-2xl bg-leaf-gradient font-bold shadow-soft"
                  >
                    {adding ? (
                      <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Kaydediliyor...</>
                    ) : (
                      <><Check className="mr-2 h-4 w-4" /> Bitkiyi Kaydet</>
                    )}
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Yeni bitki butonu */}
      <Button
        onClick={openWizard}
        className="h-12 w-full rounded-2xl bg-leaf-gradient text-base font-semibold shadow-soft"
      >
        <Plus className="mr-2 h-4 w-4" /> Yeni Bitki Ekle
      </Button>

      {/* Yükleniyor */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="ml-2 text-sm text-muted-foreground">Bitkiler yükleniyor...</span>
        </div>
      )}

      {/* Hata */}
      {error && (
        <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-4 text-center">
          <p className="text-sm text-destructive">{error}</p>
          <Button onClick={fetchPlants} variant="outline" size="sm" className="mt-2 rounded-xl">
            Tekrar Dene
          </Button>
        </div>
      )}

      {/* Boş durum */}
      {!loading && !error && plants.length === 0 && (
        <div className="py-12 text-center">
          <Sprout className="mx-auto h-10 w-10 text-muted-foreground/40" />
          <p className="mt-3 text-sm font-semibold text-muted-foreground">Henüz bitki eklenmemiş</p>
          <p className="text-xs text-muted-foreground">Yukarıdaki butona tıklayarak ilk bitkinizi ekleyin</p>
        </div>
      )}

      {/* Bitki kartları */}
      {!loading && !error && plants.map((p) => (
        <PlantCard key={p.id} plant={p} onAnalyze={() => navigate("/analyze")} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bitki Kartı
// ---------------------------------------------------------------------------

function PlantCard({ plant, onAnalyze }: { plant: Plant; onAnalyze: () => void }) {
  const stageIndex = STAGE_ORDER.indexOf(plant.growth_stage ?? "");
  const stagePct = stageIndex >= 0 ? ((stageIndex + 1) / STAGE_ORDER.length) * 100 : 0;
  const stageName = GROWTH_STAGES.find(s => s.id === plant.growth_stage)?.label;
  const stageEmoji = GROWTH_STAGES.find(s => s.id === plant.growth_stage)?.emoji;

  return (
    <div className="rounded-3xl border border-border/60 bg-card shadow-card p-4 space-y-3">
      {/* Üst satır */}
      <div className="flex items-start gap-3">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-2xl" style={{ background: "var(--renk-bej-koyu)" }}>
          {plant.plant_emoji ?? "🌱"}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold text-foreground truncate">
            {plant.plant_type ?? plant.plant_name}
          </p>
          {plant.location && (
            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
              <MapPin className="h-3 w-3" /> {plant.location}
            </p>
          )}
        </div>
        <span className="shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-bold" style={{ background: "#E8F5E0", color: "#2D4A2D" }}>
          Aktif
        </span>
      </div>

      {/* Büyüme evresi çubuğu */}
      {plant.growth_stage && (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Büyüme Evresi</span>
            <span className="font-medium text-foreground">{stageEmoji} {stageName}</span>
          </div>
          <div className="h-2 w-full rounded-full overflow-hidden" style={{ background: "var(--renk-bej-koyu)" }}>
            <div className="h-full rounded-full" style={{ width: `${stagePct}%`, background: "var(--renk-acik-yesil)" }} />
          </div>
        </div>
      )}

      {/* Meta bilgiler */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {plant.planting_date && (
          <span className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            Ekim: {new Date(plant.planting_date).toLocaleDateString("tr-TR", { day: "numeric", month: "short" })}
          </span>
        )}
        {plant.irrigation_method && (
          <span className="flex items-center gap-1">
            <Droplets className="h-3 w-3" />
            {IRRIGATION_METHOD_TR[plant.irrigation_method] ?? plant.irrigation_method}
          </span>
        )}
        {plant.area_size && (
          <span className="flex items-center gap-1">
            <Ruler className="h-3 w-3" />
            {plant.area_size} dönüm
          </span>
        )}
      </div>

      {/* Analiz başlat butonu */}
      <button
        onClick={onAnalyze}
        className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold transition hover:opacity-90 active:scale-[0.98]"
        style={{ background: "white", border: "1.5px solid var(--renk-acik-yesil)", color: "var(--renk-acik-yesil)" }}
      >
        <Camera className="h-4 w-4" />
        Analiz Başlat
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Özet satırı
// ---------------------------------------------------------------------------

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl bg-muted/40 px-3 py-2">
      <span className="text-xs text-muted-foreground shrink-0">{label}</span>
      <span className="text-xs font-semibold text-foreground text-right">{value}</span>
    </div>
  );
}
