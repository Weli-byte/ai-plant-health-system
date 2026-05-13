import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Save, Loader2, CheckCircle2, MessageCircle,
  RefreshCw, Leaf, Bug, Microscope, BarChart2, Pill,
  Sprout, TrendingUp, Zap,
} from 'lucide-react';
import { diseaseRecordsApi, type DiseaseEnrichment, type FullAnalysisResult } from '@/services/api';

// ---------------------------------------------------------------------------
// Yardımcılar
// ---------------------------------------------------------------------------

const RISK_BADGE: Record<number, { label: string; color: string }> = {
  1: { label: 'Sağlıklı', color: 'bg-green-100 text-green-700' },
  2: { label: 'Takip Et', color: 'bg-blue-100 text-blue-700' },
  3: { label: 'Dikkat', color: 'bg-amber-100 text-amber-800' },
  4: { label: 'Yüksek Risk', color: 'bg-orange-100 text-orange-800' },
  5: { label: 'Acil Müdahale', color: 'bg-red-100 text-red-700' },
};

const SPREAD_SPEED_LABELS: Record<string, string> = {
  slow: 'Yavaş Yayılım',
  medium: 'Orta Yayılım',
  fast: 'Hızlı Yayılım',
  none: '—',
};

const PATHOGEN_LABELS: Record<string, string> = {
  fungal: 'Fungal',
  bacterial: 'Bakteriyel',
  viral: 'Viral',
  pest: 'Zararlı Böcek',
  none: 'Sağlıklı',
};

const SPREAD_RISK_LABELS: Record<string, string> = {
  low: 'Düşük',
  medium: 'Orta',
  high: 'Yüksek',
};

function RiskBar({ level }: { level: number }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((i) => (
        <div
          key={i}
          className={`h-3 flex-1 rounded-full transition-colors ${
            i <= level
              ? level <= 1 ? 'bg-green-500'
              : level <= 2 ? 'bg-blue-400'
              : level <= 3 ? 'bg-amber-400'
              : level <= 4 ? 'bg-orange-500'
              : 'bg-red-500'
              : 'bg-muted'
          }`}
        />
      ))}
    </div>
  );
}

function ConfidenceBar({ pct }: { pct: number }) {
  return (
    <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-muted">
      <div
        className="absolute inset-y-0 left-0 rounded-full bg-leaf-gradient transition-all"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bileşen
// ---------------------------------------------------------------------------

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();

  const uploadedImage: string = location.state?.image || '';
  const resultData: FullAnalysisResult | undefined = location.state?.resultData;

  const diseaseInfo = resultData?.disease_classification;
  const gradcamInfo = resultData?.gradcam;
  const enrichment: DiseaseEnrichment | null = resultData?.disease_enrichment ?? null;

  const diseaseName = enrichment?.disease_name_tr ?? diseaseInfo?.predicted_class ?? 'Bilinmiyor';
  const diseaseNameEn = enrichment?.disease_name_en ?? diseaseInfo?.predicted_class ?? '';
  const confidencePct = diseaseInfo?.confidence ? Math.round(diseaseInfo.confidence * 100) : 0;
  const overlayImage = gradcamInfo?.overlay_base64
    ? `data:image/jpeg;base64,${gradcamInfo.overlay_base64}`
    : uploadedImage;
  const riskLevel = enrichment?.risk_level ?? 1;
  const badge = RISK_BADGE[riskLevel] ?? RISK_BADGE[1];

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await diseaseRecordsApi.create({
        plant_id: 1,
        disease_name: diseaseName,
        confidence_score: diseaseInfo?.confidence ?? 0,
      });
      setSaved(true);
    } catch (err) {
      console.error('Kaydetme hatası:', err);
      alert('Sonuç kaydedilemedi. Lütfen tekrar deneyin.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4 pb-20 animate-fade-in">
      {/* Geri butonu */}
      <button
        onClick={() => navigate('/analyze')}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition"
      >
        <ArrowLeft size={16} /> Yeni Analiz
      </button>

      {/* ── Kart 1: Hero ── */}
      <div className="rounded-3xl bg-card border border-border/60 shadow-card p-5 space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-0.5">
              Tespit Edilen Hastalık
            </p>
            <h2 className="text-2xl font-black text-foreground leading-tight">{diseaseName}</h2>
            {diseaseNameEn && diseaseName !== diseaseNameEn && (
              <p className="text-sm text-muted-foreground mt-0.5 italic">{diseaseNameEn}</p>
            )}
          </div>
          <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-bold ${badge.color}`}>
            {badge.label}
          </span>
        </div>
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Model Güven Skoru</span>
            <span className="font-bold text-foreground">%{confidencePct}</span>
          </div>
          <ConfidenceBar pct={confidencePct} />
        </div>
      </div>

      {/* ── Kart 2: Görsel ── */}
      <div className="rounded-3xl overflow-hidden border border-border/60 shadow-card">
        <div className="relative bg-black">
          <img
            src={overlayImage || uploadedImage}
            alt="Analiz görseli"
            className="w-full aspect-square object-cover opacity-90"
          />
          {!gradcamInfo && (
            <div className="absolute top-1/3 left-1/3 w-24 h-24 border-4 border-red-500 rounded-full animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.5)]" />
          )}
        </div>
        <div className="bg-card px-4 py-2.5 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            {gradcamInfo ? 'Grad-CAM ısı haritası gösteriliyor' : 'Orijinal fotoğraf'}
          </p>
          <span className="text-xs font-medium text-muted-foreground">EfficientNet-B3</span>
        </div>
      </div>

      {/* ── Kart 3: Hastalık Bilgisi ── */}
      {enrichment && (
        <div className="rounded-3xl bg-card border border-border/60 shadow-card p-5 space-y-3">
          <div className="flex items-center gap-2 font-bold text-foreground">
            <Microscope className="h-5 w-5 text-primary" />
            <span>Hastalık Bilgisi</span>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">{enrichment.description}</p>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full bg-purple-100 text-purple-700 px-3 py-1 text-xs font-semibold">
              {PATHOGEN_LABELS[enrichment.pathogen_type] ?? enrichment.pathogen_type}
            </span>
            {enrichment.spread_speed !== 'none' && (
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
                enrichment.spread_speed === 'fast' ? 'bg-red-100 text-red-700'
                : enrichment.spread_speed === 'medium' ? 'bg-amber-100 text-amber-800'
                : 'bg-green-100 text-green-700'
              }`}>
                {SPREAD_SPEED_LABELS[enrichment.spread_speed]}
              </span>
            )}
          </div>
          {enrichment.affected_parts.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground mb-1.5">Etkilenen Bölgeler</p>
              <div className="flex flex-wrap gap-1.5">
                {enrichment.affected_parts.map((part) => (
                  <span key={part} className="rounded-lg bg-muted px-2.5 py-1 text-xs font-medium text-foreground">
                    {part}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Kart 4: Risk Değerlendirmesi ── */}
      {enrichment && (
        <div className="rounded-3xl bg-card border border-border/60 shadow-card p-5 space-y-3">
          <div className="flex items-center gap-2 font-bold text-foreground">
            <BarChart2 className="h-5 w-5 text-amber-500" />
            <span>Risk Değerlendirmesi</span>
          </div>
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Risk Seviyesi</span>
              <span className="font-bold text-foreground">{riskLevel}/5</span>
            </div>
            <RiskBar level={riskLevel} />
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="rounded-xl bg-muted/50 p-3">
              <p className="text-muted-foreground mb-0.5">Mevcut Evre</p>
              <p className="font-semibold text-foreground">{enrichment.current_stage}</p>
            </div>
            <div className="rounded-xl bg-muted/50 p-3">
              <p className="text-muted-foreground mb-0.5">Yayılma Riski</p>
              <p className="font-semibold text-foreground">{SPREAD_RISK_LABELS[enrichment.spread_risk] ?? enrichment.spread_risk}</p>
            </div>
          </div>
          <div className="rounded-xl bg-muted/50 p-3 text-xs">
            <p className="text-muted-foreground mb-0.5">Tahmini Gelişim Süresi</p>
            <p className="font-semibold text-foreground">{enrichment.estimated_timeline}</p>
          </div>
        </div>
      )}

      {/* ── Kart 5: Tedavi Planı ── */}
      {enrichment && enrichment.treatment_products.length > 0 && (
        <div className="rounded-3xl bg-card border border-border/60 shadow-card p-5 space-y-3">
          <div className="flex items-center gap-2 font-bold text-foreground">
            <Pill className="h-5 w-5 text-blue-500" />
            <span>Tedavi Planı</span>
          </div>
          <div className="space-y-3">
            {enrichment.treatment_products.map((product, idx) => (
              <div key={idx} className="rounded-2xl border border-border/60 p-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-bold text-foreground text-sm">{product.name}</p>
                  <span className="shrink-0 rounded-full bg-green-100 text-green-700 px-2.5 py-0.5 text-xs font-semibold">
                    {product.price_range_tl}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">Etken madde: {product.active_ingredient}</p>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <p className="text-muted-foreground">Doz</p>
                    <p className="font-medium text-foreground">{product.dose}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Zamanlama</p>
                    <p className="font-medium text-foreground">{product.timing}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Sıklık</p>
                    <p className="font-medium text-foreground">{product.frequency}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Kart 6: Kültürel Önlemler ── */}
      {enrichment && enrichment.cultural_measures.length > 0 && (
        <div className="rounded-3xl bg-card border border-border/60 shadow-card p-5 space-y-3">
          <div className="flex items-center gap-2 font-bold text-foreground">
            <Sprout className="h-5 w-5 text-green-600" />
            <span>Kültürel Önlemler</span>
          </div>
          <ul className="space-y-2">
            {enrichment.cultural_measures.map((measure, idx) => (
              <li key={idx} className="flex items-start gap-2.5 text-sm text-foreground">
                <Leaf className="h-4 w-4 mt-0.5 shrink-0 text-green-500" />
                <span>{measure}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Kart 7: Prognoz ── */}
      {enrichment && (
        <div className="rounded-3xl bg-card border border-border/60 shadow-card p-5 space-y-3">
          <div className="flex items-center gap-2 font-bold text-foreground">
            <TrendingUp className="h-5 w-5 text-indigo-500" />
            <span>Prognoz ve Etki</span>
          </div>
          <div className="space-y-2.5">
            <div className="rounded-xl bg-green-50 border border-green-200 p-3">
              <p className="text-xs font-bold text-green-800 mb-1">Tedavi ile</p>
              <p className="text-sm text-green-700">{enrichment.prognosis_with_treatment}</p>
            </div>
            <div className="rounded-xl bg-red-50 border border-red-200 p-3">
              <p className="text-xs font-bold text-red-800 mb-1">Tedavi olmadan</p>
              <p className="text-sm text-red-700">{enrichment.prognosis_without_treatment}</p>
            </div>
            <div className="rounded-xl bg-amber-50 border border-amber-200 p-3">
              <p className="text-xs font-bold text-amber-800 mb-1">Hasat Etkisi</p>
              <p className="text-sm text-amber-800">{enrichment.harvest_impact}</p>
            </div>
            <div className="rounded-xl bg-muted/50 p-3">
              <p className="text-xs font-bold text-muted-foreground mb-1">Gelecek Sezon Önleme</p>
              <p className="text-sm text-foreground">{enrichment.next_season_prevention}</p>
            </div>
          </div>
        </div>
      )}

      {/* ── Kart 8: Aksiyonlar ── */}
      <div className="rounded-3xl bg-card border border-border/60 shadow-card p-5 space-y-3">
        <div className="flex items-center gap-2 font-bold text-foreground">
          <Zap className="h-5 w-5 text-primary" />
          <span>Aksiyon Al</span>
        </div>

        <button
          onClick={handleSave}
          disabled={saving || saved}
          className={`w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl font-bold text-sm transition ${
            saved
              ? 'bg-green-100 text-green-700 cursor-default'
              : 'bg-green-600 text-white hover:bg-green-700 shadow-sm active:scale-[0.98]'
          }`}
        >
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {saved && <CheckCircle2 className="h-4 w-4" />}
          {!saving && !saved && <Save className="h-4 w-4" />}
          {saved ? 'Sonuç Kaydedildi' : saving ? 'Kaydediliyor...' : 'Sonucu Kaydet'}
        </button>

        <button
          onClick={() => navigate('/chat', { state: { prefill: `${diseaseName} hastalığı hakkında ne yapmalıyım?` } })}
          className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl border border-primary/50 text-primary font-bold text-sm hover:bg-primary/5 transition active:scale-[0.98]"
        >
          <MessageCircle className="h-4 w-4" />
          AI Danışmanına Sor
        </button>

        <button
          onClick={() => navigate('/analyze')}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-border/60 text-muted-foreground font-semibold text-sm hover:bg-muted/40 transition"
        >
          <RefreshCw className="h-4 w-4" />
          Yeni Analiz
        </button>
      </div>

      {/* Yaprak tespiti uyarısı */}
      {resultData && !resultData.leaf_detection?.leaf_detected && (
        <div className="rounded-2xl bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800">
          Görselde net bir yaprak tespit edilemedi. Sonuçlar yanıltıcı olabilir — daha yakın çekilmiş bir fotoğraf deneyin.
        </div>
      )}
    </div>
  );
}
