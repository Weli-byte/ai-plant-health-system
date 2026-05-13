import { useState, useRef, useCallback, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Save, Loader2, CheckCircle2, MessageCircle,
  RefreshCw, Leaf, Microscope, BarChart2, Pill,
  Sprout, TrendingUp, Zap, FlaskConical,
} from 'lucide-react';
import { diseaseRecordsApi, type DiseaseEnrichment, type FullAnalysisResult, type HotspotRegion } from '@/services/api';

// ---------------------------------------------------------------------------
// Sabitler
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

type TabId = 'overview' | 'diagnosis' | 'treatment' | 'economic';

// ---------------------------------------------------------------------------
// Alt bileşenler
// ---------------------------------------------------------------------------

function RiskBar({ level }: { level: number }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((i) => (
        <div
          key={i}
          className={`h-3 flex-1 rounded-full ${
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
        className="absolute inset-y-0 left-0 rounded-full bg-leaf-gradient"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function Empty({ text = '—' }: { text?: string }) {
  return <span className="text-muted-foreground text-sm">{text}</span>;
}

function InfoBlock({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl bg-muted/50 p-3 text-sm">
      <p className="text-xs font-semibold text-muted-foreground mb-1">{label}</p>
      <div className="text-foreground leading-relaxed">{children}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Canvas hotspot drawing
// ---------------------------------------------------------------------------

function drawHotspotsOnCanvas(
  canvas: HTMLCanvasElement,
  img: HTMLImageElement,
  hotspots: HotspotRegion[],
  healthyPct: number,
) {
  const w = img.clientWidth;
  const h = img.clientHeight;
  if (!w || !h) return;

  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  ctx.clearRect(0, 0, w, h);

  if (hotspots.length === 0) return;

  // Sağlıklı alan için hafif yeşil overlay
  if (healthyPct > 30) {
    ctx.fillStyle = 'rgba(0,200,83,0.10)';
    ctx.fillRect(0, 0, w, h);
  }

  // Enfeksiyon odak noktaları
  for (const region of hotspots) {
    const cx = (region.x_percent / 100) * w;
    const cy = (region.y_percent / 100) * h;
    const r = (region.radius_percent / 100) * Math.min(w, h);

    let rgb: string;
    let alpha: number;
    if (region.intensity >= 0.9) { rgb = '255,45,0'; alpha = 0.55; }
    else if (region.intensity >= 0.6) { rgb = '255,140,0'; alpha = 0.40; }
    else { rgb = '255,215,0'; alpha = 0.30; }

    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    grad.addColorStop(0, `rgba(${rgb},${alpha})`);
    grad.addColorStop(0.55, `rgba(${rgb},${alpha * 0.45})`);
    grad.addColorStop(1, `rgba(${rgb},0)`);

    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.fill();

    // Dış halka
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.62, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(${rgb},0.72)`;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  // Sağ üst köşe legendi
  const legendItems = [
    { rgb: '255,45,0', label: 'Kritik' },
    { rgb: '255,140,0', label: 'Orta' },
    { rgb: '255,215,0', label: 'Hafif' },
    { rgb: '0,200,83', label: 'Sağlıklı' },
  ];
  const bh = 17;
  const pad = 6;
  const lw = 90;
  const lh = legendItems.length * bh + pad * 2;
  const lx = w - 6;
  let ly = 6;

  ctx.fillStyle = 'rgba(0,0,0,0.58)';
  ctx.fillRect(lx - lw, ly - pad, lw, lh);

  ctx.font = '10px system-ui,sans-serif';
  ctx.textBaseline = 'top';
  for (const item of legendItems) {
    ctx.fillStyle = `rgba(${item.rgb},0.85)`;
    ctx.fillRect(lx - lw + pad, ly + 2, 9, 9);
    ctx.fillStyle = 'rgba(255,255,255,0.88)';
    ctx.fillText(item.label, lx - lw + pad + 13, ly);
    ly += bh;
  }
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
  const expert = enrichment?.expert_analysis ?? null;

  const diseaseName = enrichment?.disease_name_tr ?? diseaseInfo?.predicted_class ?? 'Tespit edilemedi';
  const diseaseNameEn = enrichment?.disease_name_en ?? diseaseInfo?.predicted_class ?? '';
  const confidencePct = diseaseInfo?.confidence ? Math.round(diseaseInfo.confidence * 100) : 0;
  const overlayImage = gradcamInfo?.overlay_base64
    ? `data:image/jpeg;base64,${gradcamInfo.overlay_base64}`
    : uploadedImage;
  const riskLevel = enrichment?.risk_level ?? (confidencePct > 70 ? 3 : 2);
  const badge = RISK_BADGE[riskLevel] ?? RISK_BADGE[3];
  const hotspots = enrichment?.hotspot_regions ?? [];
  const healthyPct = enrichment?.healthy_percentage ?? 100;
  const affectedPct = enrichment?.affected_percentage ?? 0;

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [tooltip, setTooltip] = useState<{ label: string; intensity: number; x: number; y: number } | null>(null);

  const imgRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const redraw = useCallback(() => {
    if (canvasRef.current && imgRef.current && hotspots.length > 0) {
      drawHotspotsOnCanvas(canvasRef.current, imgRef.current, hotspots, healthyPct);
    }
  }, [hotspots, healthyPct]);

  useEffect(() => { redraw(); }, [redraw]);

  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || hotspots.length === 0) { setTooltip(null); return; }
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    for (const region of hotspots) {
      const cx = (region.x_percent / 100) * canvas.width;
      const cy = (region.y_percent / 100) * canvas.height;
      const r = (region.radius_percent / 100) * Math.min(canvas.width, canvas.height);
      if (Math.hypot(mx - cx, my - cy) <= r) {
        setTooltip({ label: region.label, intensity: region.intensity, x: mx, y: my });
        return;
      }
    }
    setTooltip(null);
  }, [hotspots]);

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

  const tabs: { id: TabId; label: string }[] = [
    { id: 'overview', label: 'Genel Bakış' },
    { id: 'diagnosis', label: 'Teşhis' },
    { id: 'treatment', label: 'Tedavi' },
    { id: 'economic', label: 'Ekonomik' },
  ];

  return (
    <div className="space-y-4 pb-20 animate-fade-in">
      {/* Geri */}
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
            {diseaseNameEn && diseaseNameEn !== diseaseName && (
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
            <span className="font-bold text-foreground">
              {confidencePct > 0 ? `%${confidencePct}` : '—'}
            </span>
          </div>
          <ConfidenceBar pct={confidencePct} />
        </div>
      </div>

      {/* ── Kart 2: Görsel + Hotspot Canvas ── */}
      <div className="rounded-3xl overflow-hidden border border-border/60 shadow-card">
        {(overlayImage || uploadedImage) ? (
          <div
            className="relative bg-black"
            onClick={() => setTooltip(null)}
          >
            <img
              ref={imgRef}
              src={overlayImage || uploadedImage}
              alt="Analiz görseli"
              className="w-full aspect-square object-cover opacity-90"
              onLoad={redraw}
            />
            {hotspots.length > 0 && (
              <canvas
                ref={canvasRef}
                onClick={handleCanvasClick}
                className="absolute inset-0 w-full h-full cursor-crosshair"
              />
            )}
            {tooltip && (
              <div
                className="absolute pointer-events-none z-10 rounded-xl bg-black/75 text-white px-3 py-2 text-xs shadow-lg"
                style={{ left: Math.min(tooltip.x + 8, 200), top: Math.max(tooltip.y - 44, 4) }}
              >
                <p className="font-bold">{tooltip.label}</p>
                <p className="text-white/70">Yoğunluk: %{Math.round(tooltip.intensity * 100)}</p>
              </div>
            )}
            {!gradcamInfo && hotspots.length === 0 && (
              <div className="absolute top-1/3 left-1/3 w-24 h-24 border-4 border-red-500 rounded-full animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.5)]" />
            )}
          </div>
        ) : (
          <div className="aspect-square bg-muted flex items-center justify-center">
            <p className="text-sm text-muted-foreground">Görsel yok</p>
          </div>
        )}
        <div className="bg-card px-4 py-2.5 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            {hotspots.length > 0
              ? `%${affectedPct} etkilenmiş alan · ${hotspots.length} odak noktası`
              : 'Analiz görseli'}
          </p>
          <span className="text-xs font-medium text-muted-foreground">Vision AI</span>
        </div>
      </div>

      {/* ── Kart 3: Uzman Analizi — Sekmeli ── */}
      <div className="rounded-3xl bg-card border border-border/60 shadow-card overflow-hidden">
        {/* Sekme çubuğu */}
        <div className="flex border-b border-border/60">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 py-3 text-xs font-semibold transition border-b-2 ${
                activeTab === tab.id
                  ? 'border-primary text-primary bg-primary/5'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Sekme içeriği */}
        <div className="p-5 space-y-3">

          {/* ── Genel Bakış ── */}
          {activeTab === 'overview' && (
            <>
              <div className="flex items-center gap-2 font-bold text-foreground">
                <Microscope className="h-5 w-5 text-primary" />
                <span>Hastalık Bilgisi</span>
              </div>

              {enrichment?.description && (
                <p className="text-sm text-muted-foreground leading-relaxed">{enrichment.description}</p>
              )}

              <div className="flex flex-wrap gap-2">
                <span className="rounded-full bg-purple-100 text-purple-700 px-3 py-1 text-xs font-semibold">
                  {enrichment?.pathogen_type
                    ? (PATHOGEN_LABELS[enrichment.pathogen_type] ?? enrichment.pathogen_type)
                    : '—'}
                </span>
                {enrichment?.spread_speed && enrichment.spread_speed !== 'none' && (
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    enrichment.spread_speed === 'fast' ? 'bg-red-100 text-red-700'
                    : enrichment.spread_speed === 'medium' ? 'bg-amber-100 text-amber-800'
                    : 'bg-green-100 text-green-700'
                  }`}>
                    {SPREAD_SPEED_LABELS[enrichment.spread_speed] ?? enrichment.spread_speed}
                  </span>
                )}
              </div>

              {enrichment?.severity_distribution && (
                <InfoBlock label="Şiddet Dağılımı">{enrichment.severity_distribution}</InfoBlock>
              )}

              {expert?.biology && (
                <InfoBlock label="Patojen Biyolojisi">{expert.biology}</InfoBlock>
              )}

              {expert?.spread_mechanism && (
                <InfoBlock label="Yayılma Mekanizması">{expert.spread_mechanism}</InfoBlock>
              )}

              {expert?.environmental_conditions && (
                <InfoBlock label="Tetikleyici Çevresel Koşullar">{expert.environmental_conditions}</InfoBlock>
              )}

              {!enrichment?.description && !expert?.biology && (
                <Empty text="Açıklama mevcut değil" />
              )}
            </>
          )}

          {/* ── Teşhis ── */}
          {activeTab === 'diagnosis' && (
            <>
              <div className="flex items-center gap-2 font-bold text-foreground">
                <FlaskConical className="h-5 w-5 text-indigo-500" />
                <span>Teşhis Analizi</span>
              </div>

              {expert?.diagnosis_certainty && (
                <div className="rounded-xl bg-indigo-50 border border-indigo-200 p-3 text-sm">
                  <p className="text-xs font-bold text-indigo-800 mb-1">Teşhis Kesinliği</p>
                  <p className="text-indigo-900 leading-relaxed">{expert.diagnosis_certainty}</p>
                </div>
              )}

              {expert?.similar_diseases && (
                <InfoBlock label="Benzer Hastalıklar / Ayırıcı Tanı">{expert.similar_diseases}</InfoBlock>
              )}

              {enrichment?.affected_parts && enrichment.affected_parts.length > 0 && (
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

              {enrichment?.estimated_timeline && (
                <InfoBlock label="Tahmini Gelişim Süresi">{enrichment.estimated_timeline}</InfoBlock>
              )}

              {!expert?.diagnosis_certainty && !expert?.similar_diseases && (
                <Empty text="Teşhis bilgisi mevcut değil" />
              )}
            </>
          )}

          {/* ── Tedavi ── */}
          {activeTab === 'treatment' && (
            <>
              <div className="flex items-center gap-2 font-bold text-foreground">
                <Pill className="h-5 w-5 text-blue-500" />
                <span>Tedavi Protokolü</span>
              </div>

              {expert?.treatment_protocol && (
                <div className="rounded-xl bg-blue-50 border border-blue-200 p-3 text-sm">
                  <p className="text-xs font-bold text-blue-800 mb-1">Uygulama Protokolü</p>
                  <p className="text-blue-900 leading-relaxed">{expert.treatment_protocol}</p>
                </div>
              )}

              {expert?.organic_alternatives && (
                <div className="rounded-xl bg-green-50 border border-green-200 p-3 text-sm">
                  <p className="text-xs font-bold text-green-800 mb-1">Organik / Biyolojik Alternatifler</p>
                  <p className="text-green-900 leading-relaxed">{expert.organic_alternatives}</p>
                </div>
              )}

              {expert?.resistance_management && (
                <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 text-sm">
                  <p className="text-xs font-bold text-amber-800 mb-1">Direnç Yönetimi</p>
                  <p className="text-amber-900 leading-relaxed">{expert.resistance_management}</p>
                </div>
              )}

              {enrichment?.treatment_products && enrichment.treatment_products.length > 0 && (
                <div className="space-y-3">
                  <p className="text-xs font-semibold text-muted-foreground">Önerilen Ürünler</p>
                  {enrichment.treatment_products.map((product, idx) => (
                    <div key={idx} className="rounded-2xl border border-border/60 p-4 space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <p className="font-bold text-foreground text-sm">{product.name || '—'}</p>
                        {product.price_range_tl && (
                          <span className="shrink-0 rounded-full bg-green-100 text-green-700 px-2.5 py-0.5 text-xs font-semibold">
                            {product.price_range_tl}
                          </span>
                        )}
                      </div>
                      {product.active_ingredient && (
                        <p className="text-xs text-muted-foreground">Etken madde: {product.active_ingredient}</p>
                      )}
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div>
                          <p className="text-muted-foreground">Doz</p>
                          <p className="font-medium text-foreground">{product.dose || '—'}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Zamanlama</p>
                          <p className="font-medium text-foreground">{product.timing || '—'}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Sıklık</p>
                          <p className="font-medium text-foreground">{product.frequency || '—'}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {!expert?.treatment_protocol && (!enrichment?.treatment_products || enrichment.treatment_products.length === 0) && (
                <p className="text-sm text-muted-foreground">
                  {!enrichment
                    ? 'AI analizi tamamlanamadı — internet bağlantısını kontrol edip tekrar deneyin.'
                    : 'Bu hastalık için tedavi bilgisi mevcut değil.'}
                </p>
              )}
            </>
          )}

          {/* ── Ekonomik Etki ── */}
          {activeTab === 'economic' && (
            <>
              <div className="flex items-center gap-2 font-bold text-foreground">
                <TrendingUp className="h-5 w-5 text-indigo-500" />
                <span>Ekonomik Etki Analizi</span>
              </div>

              {expert?.economic_impact && (
                <InfoBlock label="Ekonomik Analiz">{expert.economic_impact}</InfoBlock>
              )}

              <div className="space-y-2.5">
                <div className="rounded-xl bg-green-50 border border-green-200 p-3">
                  <p className="text-xs font-bold text-green-800 mb-1">Tedavi ile Prognoz</p>
                  <p className="text-sm text-green-700">{enrichment?.prognosis_with_treatment || '—'}</p>
                </div>
                <div className="rounded-xl bg-red-50 border border-red-200 p-3">
                  <p className="text-xs font-bold text-red-800 mb-1">Tedavisiz Prognoz</p>
                  <p className="text-sm text-red-700">{enrichment?.prognosis_without_treatment || '—'}</p>
                </div>
                <div className="rounded-xl bg-amber-50 border border-amber-200 p-3">
                  <p className="text-xs font-bold text-amber-800 mb-1">Hasat Etkisi</p>
                  <p className="text-sm text-amber-800">{enrichment?.harvest_impact || '—'}</p>
                </div>
                <div className="rounded-xl bg-muted/50 p-3">
                  <p className="text-xs font-bold text-muted-foreground mb-1">Gelecek Sezon Önleme</p>
                  <p className="text-sm text-foreground">{enrichment?.next_season_prevention || '—'}</p>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Kart 4: Risk Değerlendirmesi ── */}
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
            <p className="font-semibold text-foreground">{enrichment?.current_stage || '—'}</p>
          </div>
          <div className="rounded-xl bg-muted/50 p-3">
            <p className="text-muted-foreground mb-0.5">Yayılma Riski</p>
            <p className="font-semibold text-foreground">
              {enrichment?.spread_risk
                ? (SPREAD_RISK_LABELS[enrichment.spread_risk] ?? enrichment.spread_risk)
                : '—'}
            </p>
          </div>
        </div>
        {affectedPct > 0 && (
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="rounded-xl bg-green-50 border border-green-200 p-3">
              <p className="text-green-700 mb-0.5">Sağlıklı Alan</p>
              <p className="font-bold text-green-800">%{healthyPct}</p>
            </div>
            <div className="rounded-xl bg-red-50 border border-red-200 p-3">
              <p className="text-red-700 mb-0.5">Etkilenen Alan</p>
              <p className="font-bold text-red-800">%{affectedPct}</p>
            </div>
          </div>
        )}
      </div>

      {/* ── Kart 5: Kültürel Önlemler ── */}
      <div className="rounded-3xl bg-card border border-border/60 shadow-card p-5 space-y-3">
        <div className="flex items-center gap-2 font-bold text-foreground">
          <Sprout className="h-5 w-5 text-green-600" />
          <span>Kültürel Önlemler</span>
        </div>
        {enrichment?.cultural_measures && enrichment.cultural_measures.length > 0 ? (
          <ul className="space-y-2">
            {enrichment.cultural_measures.map((measure, idx) => (
              <li key={idx} className="flex items-start gap-2.5 text-sm text-foreground">
                <Leaf className="h-4 w-4 mt-0.5 shrink-0 text-green-500" />
                <span>{measure}</span>
              </li>
            ))}
          </ul>
        ) : (
          <Empty text="Kültürel önlem bilgisi mevcut değil" />
        )}
      </div>

      {/* ── Kart 6: Aksiyonlar ── */}
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
          onClick={() => navigate('/chat', {
            state: { prefill: `${diseaseName} hastalığı hakkında ne yapmalıyım?` },
          })}
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
          Görselde net bir yaprak tespit edilemedi. Daha yakın çekilmiş bir fotoğraf deneyin.
        </div>
      )}
    </div>
  );
}
