import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Leaf, Loader2, Microscope, RefreshCw } from "lucide-react";
import { analysisRecordsApi, type AnalysisRecord } from "@/services/api";
import { getUser } from "@/lib/auth";

const RISK_BADGE: Record<number, { label: string; color: string; icon: string }> = {
  1: { label: "Sağlıklı", color: "bg-green-100 text-green-700", icon: "bg-green-200/70" },
  2: { label: "Takip Et", color: "bg-blue-100 text-blue-700", icon: "bg-blue-200/70" },
  3: { label: "Dikkat", color: "bg-amber-100 text-amber-800", icon: "bg-amber-200/70" },
  4: { label: "Yüksek Risk", color: "bg-orange-100 text-orange-800", icon: "bg-orange-200/70" },
  5: { label: "Acil Müdahale", color: "bg-red-100 text-red-700", icon: "bg-red-200/70" },
};

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" })
    + ", " + d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
}

export default function AnalysisHistory() {
  const navigate = useNavigate();
  const [analyses, setAnalyses] = useState<AnalysisRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const user = getUser();

  const load = useCallback(async () => {
    if (!user?.email) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      const data = await analysisRecordsApi.getByEmail(user.email);
      setAnalyses(data);
    } catch (err) {
      console.error("Analiz geçmişi yükleme hatası:", err);
      setError("Analizler yüklenemedi. Sunucu bağlantısını kontrol edin.");
    } finally {
      setLoading(false);
    }
  }, [user?.email]);

  useEffect(() => { load(); }, [load]);

  const handleViewDetail = (a: AnalysisRecord) => {
    let enrichment = null;
    if (a.enrichment_json) {
      try { enrichment = JSON.parse(a.enrichment_json); } catch { /* ignore */ }
    }
    const resultData = {
      success: true,
      leaf_detection: {
        success: true, leaf_detected: true, bounding_box: null,
        confidence: a.confidence_score, cropped_leaf_base64: null,
        original_width: 0, original_height: 0, message: "Vision AI",
      },
      disease_classification: {
        success: true,
        predicted_class: a.disease_name_en ?? a.disease_name_tr,
        predicted_class_index: 0,
        confidence: a.confidence_score ?? 0,
        all_scores: {},
        message: "",
      },
      gradcam: null,
      disease_enrichment: enrichment,
      message: "Kayıtlı analiz",
    };
    navigate("/results", { state: { resultData } });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <span className="ml-2 text-sm text-muted-foreground">Analizler yükleniyor...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-3 animate-fade-in">
        <div className="rounded-2xl bg-red-50 border border-red-200 p-4 text-sm text-red-800">{error}</div>
        <button
          onClick={load}
          className="w-full rounded-2xl border border-border/60 py-3 text-sm font-semibold hover:bg-muted/40 transition"
        >
          Tekrar Dene
        </button>
      </div>
    );
  }

  if (analyses.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 space-y-5 animate-fade-in">
        <div className="flex h-24 w-24 items-center justify-center rounded-full bg-muted/50">
          <Leaf className="h-12 w-12 text-muted-foreground/40" />
        </div>
        <div className="text-center space-y-1.5">
          <p className="text-lg font-bold text-foreground">Henüz analiz yapmadınız</p>
          <p className="text-sm text-muted-foreground">İlk tarla analizinizi yapın ve buraya kaydedin</p>
        </div>
        <button
          onClick={() => navigate("/analyze")}
          className="rounded-2xl bg-leaf-gradient px-8 py-3.5 text-sm font-bold text-primary-foreground shadow-soft active:scale-[0.98] transition"
        >
          İlk Analizi Başlat
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3 animate-fade-in">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">{analyses.length} analiz kaydı</p>
        <button
          onClick={load}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Yenile
        </button>
      </div>

      {analyses.map((a) => {
        const badge = RISK_BADGE[a.risk_level ?? 3] ?? RISK_BADGE[3];
        const confidencePct = a.confidence_score ? Math.round(a.confidence_score * 100) : 0;

        return (
          <div
            key={a.id}
            className="rounded-3xl bg-card border border-border/60 shadow-card p-4 space-y-3"
          >
            {/* Başlık satırı */}
            <div className="flex items-start gap-3">
              <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${badge.icon}`}>
                <Microscope className="h-5 w-5" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-foreground leading-tight truncate">
                  {a.disease_name_tr}
                </p>
                {a.disease_name_en && a.disease_name_en !== a.disease_name_tr && (
                  <p className="text-xs text-muted-foreground italic truncate">{a.disease_name_en}</p>
                )}
              </div>
              <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-bold ${badge.color}`}>
                {badge.label}
              </span>
            </div>

            {/* Meta bilgiler */}
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{formatDate(a.created_at)}</span>
              {confidencePct > 0 && (
                <span className="font-bold text-foreground">%{confidencePct} güven</span>
              )}
            </div>

            {/* Detay butonu */}
            <button
              onClick={() => handleViewDetail(a)}
              className="w-full rounded-2xl bg-primary/8 border border-primary/20 py-2.5 text-sm font-semibold text-primary transition hover:bg-primary/15 active:scale-[0.98]"
            >
              Detayı Gör
            </button>
          </div>
        );
      })}
    </div>
  );
}
