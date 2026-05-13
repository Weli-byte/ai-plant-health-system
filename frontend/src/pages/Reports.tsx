import { useCallback, useEffect, useRef, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from "recharts";
import { Slider } from "@/components/ui/slider";
import { toast } from "sonner";
import {
  Activity, AlertTriangle, BarChart3, Calendar, CheckCircle2,
  ChevronRight, CloudRain, Download, FileBarChart2, Flame,
  Leaf, Loader2, MapPin, RefreshCw, Thermometer, TrendingDown,
  TrendingUp, Wind, XCircle, Zap,
} from "lucide-react";
import {
  reportsApi, riskPredictionApi, weatherApi,
  type ReportSummary, type RiskPredictionResult, type WeatherDay,
  type DailyDataItem,
} from "@/services/api";
import { getUser } from "@/lib/auth";

// ─── constants ───────────────────────────────────────────────────────────────

const DISEASE_COLORS = ["#22c55e", "#ef4444", "#f59e0b", "#3b82f6", "#8b5cf6", "#f97316", "#06b6d4"];

const CROP_DATA: Record<string, { yield: number; price: number }> = {
  Domates: { yield: 5000, price: 8 }, Elma: { yield: 2000, price: 5 },
  Buğday: { yield: 350, price: 12 }, Mısır: { yield: 800, price: 7 },
  Kayısı: { yield: 1000, price: 15 }, Üzüm: { yield: 1500, price: 10 },
  Zeytin: { yield: 400, price: 20 }, Biber: { yield: 3000, price: 9 },
  Çilek: { yield: 2000, price: 25 }, Patates: { yield: 3000, price: 4 },
  Salatalık: { yield: 6000, price: 6 }, Portakal: { yield: 2500, price: 8 },
  Diğer: { yield: 2000, price: 8 },
};

const GRID_SIZE = 10;
type Cell = "healthy" | "infected" | "at-risk" | "treated";

// ─── helper components ────────────────────────────────────────────────────────

function GaugeChart({ score }: { score: number }) {
  const r = 52, cx = 70, cy = 62;
  const clampedScore = Math.max(0, Math.min(100, score));
  const stdAngle = (1 - clampedScore / 100) * Math.PI;
  const endX = cx + r * Math.cos(stdAngle);
  const endY = cy - r * Math.sin(stdAngle);
  const nX = cx + (r - 13) * Math.cos(stdAngle);
  const nY = cy - (r - 13) * Math.sin(stdAngle);
  const color = score < 30 ? "#22c55e" : score < 55 ? "#f59e0b" : score < 78 ? "#f97316" : "#ef4444";
  const bgPath = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
  const fgPath = clampedScore > 0
    ? `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${endX.toFixed(2)} ${endY.toFixed(2)}`
    : "";

  return (
    <svg viewBox={`0 0 140 78`} className="w-full">
      <path d={bgPath} fill="none" stroke="#e2e8f0" strokeWidth="12" strokeLinecap="round" />
      {fgPath && <path d={fgPath} fill="none" stroke={color} strokeWidth="12" strokeLinecap="round" />}
      <line x1={cx} y1={cy} x2={nX.toFixed(2)} y2={nY.toFixed(2)} stroke="#0f172a" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx={cx} cy={cy} r="4.5" fill="#0f172a" />
      <text x={cx - r + 2} y={cy + 13} fontSize="9" fill="#94a3b8">0</text>
      <text x={cx + r - 10} y={cy + 13} fontSize="9" fill="#94a3b8">100</text>
      <text x={cx} y={cy - r / 2} textAnchor="middle" fontSize="22" fontWeight="bold" fill={color}>{score}</text>
    </svg>
  );
}

function SimGrid({ grid, label }: { grid: Cell[][]; label: string }) {
  const cellColor: Record<Cell, string> = {
    healthy: "bg-green-400",
    infected: "bg-red-500",
    "at-risk": "bg-amber-400",
    treated: "bg-teal-400",
  };
  return (
    <div className="space-y-2">
      <p className="text-center text-xs font-bold text-foreground">{label}</p>
      <div
        className="mx-auto overflow-hidden rounded-xl border border-border/60"
        style={{ display: "grid", gridTemplateColumns: `repeat(${GRID_SIZE}, 1fr)`, width: "fit-content", gap: "1px", background: "#e2e8f0" }}
      >
        {grid.map((row, r) =>
          row.map((cell, c) => (
            <div key={`${r}-${c}`} className={`${cellColor[cell]} transition-colors duration-300`} style={{ width: 22, height: 22 }} />
          ))
        )}
      </div>
    </div>
  );
}

// ─── sim helpers ──────────────────────────────────────────────────────────────

function makeInitialGrid(): Cell[][] {
  const g: Cell[][] = Array.from({ length: GRID_SIZE }, () =>
    Array<Cell>(GRID_SIZE).fill("healthy")
  );
  [[4, 4], [4, 5], [5, 4], [5, 5], [3, 5]].forEach(([r, c]) => { g[r][c] = "infected"; });
  return g;
}

function stepGrid(grid: Cell[][], withIntervention: boolean): Cell[][] {
  const next = grid.map((row) => [...row] as Cell[]);
  for (let r = 0; r < GRID_SIZE; r++) {
    for (let c = 0; c < GRID_SIZE; c++) {
      if (grid[r][c] === "infected") {
        if (withIntervention && Math.random() < 0.18) { next[r][c] = "treated"; continue; }
        for (const [dr, dc] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
          const nr = r + dr, nc = c + dc;
          if (nr >= 0 && nr < GRID_SIZE && nc >= 0 && nc < GRID_SIZE && grid[nr][nc] === "healthy") {
            if (Math.random() < (withIntervention ? 0.07 : 0.27)) next[nr][nc] = "at-risk";
          }
        }
      } else if (grid[r][c] === "at-risk") {
        if (Math.random() < (withIntervention ? 0.08 : 0.52)) next[r][c] = "infected";
      }
    }
  }
  return next;
}

function countCells(grid: Cell[][], type: Cell): number {
  return grid.flat().filter((c) => c === type).length;
}

// ─── count-up hook ────────────────────────────────────────────────────────────

function useCountUp(target: number, trigger: boolean, duration = 900) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!trigger) { setVal(0); return; }
    const start = Date.now();
    const tick = () => {
      const p = Math.min((Date.now() - start) / duration, 1);
      setVal(Math.round(target * p));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [target, trigger, duration]);
  return val;
}

// ─── section header ───────────────────────────────────────────────────────────

function SectionHeader({ title, icon }: { title: string; icon: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-primary/10">
        {icon}
      </div>
      <h2 className="text-sm font-bold text-foreground tracking-tight">{title}</h2>
    </div>
  );
}

// ─── main component ───────────────────────────────────────────────────────────

export default function Reports() {
  const user = getUser();

  // — summary
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState("");

  // — weekly modal
  const [selectedDay, setSelectedDay] = useState<DailyDataItem | null>(null);

  // — risk prediction
  const [riskForm, setRiskForm] = useState({
    temp: 22, humidity: 65, rain: 8, wind: 12,
    soil: "Killi", crop: "Domates", stage: "Vejetatif",
  });
  const [riskResult, setRiskResult] = useState<RiskPredictionResult | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);

  // — spray calendar
  const [forecast, setForecast] = useState<WeatherDay[]>([]);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [locationError, setLocationError] = useState("");

  // — yield calculator
  const [calcForm, setCalcForm] = useState({ fieldSize: 5, crop: "Domates", severity: 30, price: 8 });
  const [calcReady, setCalcReady] = useState(false);
  const lossTarget = calcReady
    ? Math.round(calcForm.fieldSize * CROP_DATA[calcForm.crop].yield * calcForm.price * (calcForm.severity / 100))
    : 0;
  const intTarget = calcReady ? Math.round(calcForm.fieldSize * 700) : 0;
  const lossVal = useCountUp(lossTarget, calcReady);
  const intVal = useCountUp(intTarget, calcReady);
  const netVal = useCountUp(Math.max(0, lossTarget - intTarget), calcReady);

  // — simulation
  const initGrid = useRef<Cell[][]>(makeInitialGrid());
  const [noIntGrid, setNoIntGrid] = useState<Cell[][]>(() => makeInitialGrid());
  const [withIntGrid, setWithIntGrid] = useState<Cell[][]>(() => makeInitialGrid());
  const [simStep, setSimStep] = useState(0);
  const [simRunning, setSimRunning] = useState(false);
  const [interventionDay, setInterventionDay] = useState(5);
  const simTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // — section refs for smooth scroll
  const trendRef = useRef<HTMLDivElement>(null);
  const diseaseRef = useRef<HTMLDivElement>(null);
  const riskRef = useRef<HTMLDivElement>(null);
  const calRef = useRef<HTMLDivElement>(null);

  // ─── data loading ────────────────────────────────────────────────────────────

  const loadSummary = useCallback(async () => {
    if (!user?.email) return;
    setSummaryLoading(true);
    try {
      const data = await reportsApi.getSummary(user.email);
      setSummary(data);
      setLastUpdate(new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }));
    } catch {
      toast.error("Rapor verileri yüklenemedi");
    } finally {
      setSummaryLoading(false);
    }
  }, [user?.email]);

  useEffect(() => { loadSummary(); }, [loadSummary]);

  const loadForecast = useCallback(() => {
    setForecastLoading(true);
    setLocationError("");
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const res = await weatherApi.getForecast(pos.coords.latitude, pos.coords.longitude);
          setForecast(res.days);
        } catch {
          toast.error("Hava tahmini alınamadı");
        } finally {
          setForecastLoading(false);
        }
      },
      () => {
        setLocationError("Konum erişimi reddedildi. Ankara konumu kullanılıyor.");
        weatherApi.getForecast(39.9208, 32.8541)
          .then((r) => setForecast(r.days))
          .catch(() => { /* ignore */ })
          .finally(() => setForecastLoading(false));
      }
    );
  }, []);

  useEffect(() => { loadForecast(); }, [loadForecast]);

  // ─── simulation ───────────────────────────────────────────────────────────────

  const startSim = useCallback(() => {
    const fresh = makeInitialGrid();
    initGrid.current = fresh;
    setNoIntGrid(fresh.map((r) => [...r] as Cell[]));
    setWithIntGrid(fresh.map((r) => [...r] as Cell[]));
    setSimStep(0);
    setSimRunning(true);
  }, []);

  const resetSim = useCallback(() => {
    if (simTimer.current) clearInterval(simTimer.current);
    setSimRunning(false);
    setSimStep(0);
    const fresh = makeInitialGrid();
    setNoIntGrid(fresh.map((r) => [...r] as Cell[]));
    setWithIntGrid(fresh.map((r) => [...r] as Cell[]));
  }, []);

  useEffect(() => {
    if (!simRunning) return;
    simTimer.current = setInterval(() => {
      setSimStep((s) => {
        if (s >= 20) { clearInterval(simTimer.current!); setSimRunning(false); return s; }
        setNoIntGrid((g) => stepGrid(g, false));
        setWithIntGrid((g) => stepGrid(g, s >= interventionDay));
        return s + 1;
      });
    }, 600);
    return () => { if (simTimer.current) clearInterval(simTimer.current); };
  }, [simRunning, interventionDay]);

  // ─── risk prediction ──────────────────────────────────────────────────────────

  const runRiskPrediction = async () => {
    setRiskLoading(true);
    setRiskResult(null);
    try {
      const res = await riskPredictionApi.predict(riskForm);
      setRiskResult(res);
    } catch {
      toast.error("Risk tahmini yapılamadı");
    } finally {
      setRiskLoading(false);
    }
  };

  // ─── derived state ────────────────────────────────────────────────────────────

  const riskColor = (level: string) => ({
    "Düşük": "text-green-600 bg-green-100",
    "Orta": "text-amber-700 bg-amber-100",
    "Yüksek": "text-orange-700 bg-orange-100",
    "Kritik": "text-red-600 bg-red-100",
  }[level] ?? "text-gray-600 bg-gray-100");

  const bestSprayDays = forecast
    .map((d, i) => ({ ...d, i }))
    .filter((d) => d.suitability === "ideal")
    .slice(0, 3)
    .map((d) => d.i);

  const noIntInfected = countCells(noIntGrid, "infected") + countCells(noIntGrid, "at-risk");
  const withIntInfected = countCells(withIntGrid, "infected") + countCells(withIntGrid, "at-risk");

  // ─── render ───────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-5 animate-fade-in pb-8">
      {/* ── HEADER ─────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-base font-extrabold text-foreground tracking-tight">Tarım Analitik Dashboard</h1>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            {new Date().toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" })}
            {lastUpdate && ` · Son güncelleme: ${lastUpdate}`}
          </p>
        </div>
        <button
          onClick={loadSummary}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Yenile
        </button>
      </div>

      {/* ── BÖLÜM 1: METRİK KARTLAR ────────────────────────────────────────── */}
      <div className="flex gap-3 overflow-x-auto pb-1 -mx-1 px-1">
        {summaryLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="shrink-0 w-36 h-24 rounded-2xl bg-muted/60 animate-pulse" />
          ))
        ) : summary ? (
          <>
            <MetricCard
              title="Toplam Analiz"
              value={summary.total.toString()}
              sub={`Bu hafta +${summary.this_week}`}
              icon={<BarChart3 className="h-4 w-4 text-primary" />}
              isDemo={summary.is_demo}
              onClick={() => trendRef.current?.scrollIntoView({ behavior: "smooth" })}
            />
            <MetricCard
              title="Sağlık Skoru"
              value={`%${summary.health_score}`}
              sub={summary.health_score >= 70 ? "İyi durumda" : summary.health_score >= 40 ? "Takip gerekli" : "Acil müdahale"}
              icon={<Activity className="h-4 w-4 text-primary" />}
              accent={summary.health_score >= 70 ? "green" : summary.health_score >= 40 ? "amber" : "red"}
              isDemo={summary.is_demo}
              onClick={() => trendRef.current?.scrollIntoView({ behavior: "smooth" })}
              ring={summary.health_score}
            />
            <MetricCard
              title="Aktif Hastalık"
              value={`${summary.active_diseases} türü`}
              sub={summary.diseased > 0 ? `${summary.diseased} analiz` : "Hastalık yok"}
              icon={<AlertTriangle className="h-4 w-4 text-primary" />}
              isDemo={summary.is_demo}
              onClick={() => diseaseRef.current?.scrollIntoView({ behavior: "smooth" })}
            />
            <MetricCard
              title="Risk Seviyesi"
              value={summary.risk_level}
              sub="Son 7 günlük trend"
              icon={<Flame className="h-4 w-4 text-primary" />}
              accent={summary.risk_level === "Düşük" ? "green" : summary.risk_level === "Orta" ? "amber" : "red"}
              isDemo={summary.is_demo}
              onClick={() => riskRef.current?.scrollIntoView({ behavior: "smooth" })}
            />
          </>
        ) : null}
      </div>

      {/* ── BÖLÜM 2: HAFTALIK TREND ────────────────────────────────────────── */}
      <div ref={trendRef} className="rounded-3xl bg-card border border-border/60 shadow-card p-4">
        <SectionHeader title="Haftalık Analiz Trendi" icon={<TrendingUp className="h-3.5 w-3.5 text-primary" />} />
        {summaryLoading ? (
          <div className="h-36 flex items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : summary ? (
          <>
            {summary.is_demo && (
              <p className="text-[10px] text-muted-foreground mb-2 italic">
                Demo mod — gerçek verileriniz analizler yaptıkça görünür
              </p>
            )}
            <ResponsiveContainer width="100%" height={130}>
              <BarChart data={summary.daily_data} barGap={2}
                onClick={(d) => d?.activePayload && setSelectedDay(d.activePayload[0].payload)}
              >
                <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip
                  content={({ active, payload, label }) =>
                    active && payload?.length ? (
                      <div className="rounded-xl bg-card border border-border/60 shadow-sm p-2 text-xs">
                        <p className="font-bold text-foreground">{label}</p>
                        <p className="text-green-600">Sağlıklı: {payload.find((p) => p.dataKey === "healthy")?.value}</p>
                        <p className="text-red-500">Hastalıklı: {payload.find((p) => p.dataKey === "diseased")?.value}</p>
                      </div>
                    ) : null
                  }
                />
                <Bar dataKey="healthy" stackId="a" fill="#4ade80" radius={[0, 0, 0, 0]} />
                <Bar dataKey="diseased" stackId="a" fill="#f87171" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <div className="flex items-center gap-4 mt-2">
              <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                <span className="h-2 w-2 rounded-full bg-green-400 inline-block" /> Sağlıklı
              </span>
              <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                <span className="h-2 w-2 rounded-full bg-red-400 inline-block" /> Hastalıklı
              </span>
              <span className="text-[10px] text-muted-foreground ml-auto">Çubuk = gün detayı</span>
            </div>
          </>
        ) : null}
      </div>

      {/* Day detail modal */}
      {selectedDay && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/40"
          onClick={() => setSelectedDay(null)}
        >
          <div
            className="w-full max-w-sm rounded-t-3xl bg-card p-5 space-y-3 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <p className="text-sm font-bold text-foreground">{selectedDay.date}</p>
              <button onClick={() => setSelectedDay(null)} className="text-muted-foreground">
                <XCircle className="h-5 w-5" />
              </button>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center">
              {[
                { label: "Toplam", val: selectedDay.total, color: "text-foreground" },
                { label: "Sağlıklı", val: selectedDay.healthy, color: "text-green-600" },
                { label: "Hastalıklı", val: selectedDay.diseased, color: "text-red-500" },
              ].map((item) => (
                <div key={item.label} className="rounded-2xl bg-muted/50 p-3">
                  <p className={`text-xl font-bold ${item.color}`}>{item.val}</p>
                  <p className="text-[10px] text-muted-foreground">{item.label}</p>
                </div>
              ))}
            </div>
            {selectedDay.total === 0 && (
              <p className="text-xs text-center text-muted-foreground">Bu gün analiz yapılmadı.</p>
            )}
          </div>
        </div>
      )}

      {/* ── BÖLÜM 3: RİSK TAHMİN MOTORU ───────────────────────────────────── */}
      <div ref={riskRef} className="rounded-3xl bg-card border border-border/60 shadow-card p-4 space-y-4">
        <SectionHeader title="Tarla Risk Tahmini" icon={<Zap className="h-3.5 w-3.5 text-primary" />} />

        {/* Sliders */}
        <div className="space-y-3">
          {[
            { key: "temp", label: "Sıcaklık (°C)", min: -10, max: 50, unit: "°C" },
            { key: "humidity", label: "Nem (%)", min: 0, max: 100, unit: "%" },
            { key: "rain", label: "Yağış (mm)", min: 0, max: 100, unit: "mm" },
            { key: "wind", label: "Rüzgar (km/s)", min: 0, max: 60, unit: "km/s" },
          ].map(({ key, label, min, max, unit }) => (
            <div key={key} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground font-medium">{label}</span>
                <span className="font-bold text-foreground">{riskForm[key as keyof typeof riskForm]}{unit}</span>
              </div>
              <Slider
                min={min} max={max} step={1}
                value={[riskForm[key as keyof typeof riskForm] as number]}
                onValueChange={([v]) => setRiskForm((p) => ({ ...p, [key]: v }))}
              />
            </div>
          ))}
        </div>

        {/* Dropdowns */}
        <div className="grid grid-cols-3 gap-2">
          {[
            { key: "soil", label: "Toprak", options: ["Killi", "Kumlu", "Tınlı", "Kireçli"] },
            { key: "crop", label: "Bitki", options: ["Domates", "Elma", "Buğday", "Mısır", "Kayısı", "Üzüm", "Zeytin", "Diğer"] },
            { key: "stage", label: "Evre", options: ["Fide", "Vejetatif", "Çiçeklenme", "Meyve", "Hasat"] },
          ].map(({ key, label, options }) => (
            <div key={key} className="space-y-1">
              <p className="text-[10px] text-muted-foreground font-medium">{label}</p>
              <select
                value={riskForm[key as keyof typeof riskForm] as string}
                onChange={(e) => setRiskForm((p) => ({ ...p, [key]: e.target.value }))}
                className="w-full rounded-xl border border-border/60 bg-background text-xs p-2 text-foreground"
              >
                {options.map((o) => <option key={o}>{o}</option>)}
              </select>
            </div>
          ))}
        </div>

        <button
          onClick={runRiskPrediction}
          disabled={riskLoading}
          className="w-full rounded-2xl bg-leaf-gradient py-3.5 text-sm font-bold text-primary-foreground shadow-soft disabled:opacity-60 active:scale-[0.98] transition flex items-center justify-center gap-2"
        >
          {riskLoading ? <><Loader2 className="h-4 w-4 animate-spin" /> Hesaplanıyor...</> : "TAHMİN ÇALIŞTIR"}
        </button>

        {/* Results */}
        {riskResult && (
          <div className="space-y-3 border-t border-border/40 pt-4">
            {/* Gauge + overview */}
            <div className="flex items-center gap-4">
              <div className="w-36 shrink-0">
                <GaugeChart score={riskResult.risk_score} />
              </div>
              <div className="flex-1 space-y-1.5">
                <span className={`inline-block rounded-full px-3 py-1 text-xs font-bold ${riskColor(riskResult.overall_risk)}`}>
                  {riskResult.overall_risk} Risk
                </span>
                <p className="text-xs text-muted-foreground">Güven: %{riskResult.confidence}</p>
                <p className="text-[11px] text-foreground leading-snug">{riskResult.week_forecast}</p>
              </div>
            </div>

            {/* Disease risks */}
            <div className="space-y-2">
              <p className="text-xs font-bold text-foreground">Hastalık Riskleri</p>
              {riskResult.disease_risks.map((d) => (
                <div key={d.name} className="rounded-2xl bg-muted/40 p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-foreground">{d.name}</p>
                    <span className={`text-[10px] font-bold rounded-full px-2 py-0.5 ${d.severity === "Yüksek" ? "bg-red-100 text-red-700" : d.severity === "Orta" ? "bg-amber-100 text-amber-700" : "bg-green-100 text-green-700"}`}>
                      {d.severity}
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                    <div className="h-full rounded-full bg-primary/70 transition-all" style={{ width: `${d.probability}%` }} />
                  </div>
                  <p className="text-[10px] text-muted-foreground">%{d.probability} olasılık · {d.reason}</p>
                  <p className="text-[10px] text-primary font-medium">✦ {d.prevention}</p>
                </div>
              ))}
            </div>

            {/* Immediate actions */}
            <div className="space-y-1">
              <p className="text-xs font-bold text-foreground">Acil Aksiyonlar</p>
              {riskResult.immediate_actions.map((a, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-foreground">
                  <CheckCircle2 className="h-3.5 w-3.5 text-primary mt-0.5 shrink-0" />
                  <span>{a}</span>
                </div>
              ))}
            </div>

            {/* Spray window */}
            <div className="rounded-2xl border border-primary/20 bg-primary/5 p-3 flex items-center gap-3">
              <Calendar className="h-5 w-5 text-primary shrink-0" />
              <div>
                <p className="text-xs font-bold text-foreground">
                  İdeal İlaçlama: {riskResult.optimal_spray_window.start_day}. — {riskResult.optimal_spray_window.end_day}. gün
                </p>
                <p className="text-[10px] text-muted-foreground">{riskResult.optimal_spray_window.reason}</p>
              </div>
            </div>

            {/* Economic risk */}
            <div className="rounded-2xl border border-red-200 bg-red-50 p-3 space-y-1">
              <p className="text-xs font-bold text-red-700">Ekonomik Risk</p>
              <p className="text-lg font-extrabold text-red-600">
                %{riskResult.economic_risk_percent} hasar olasılığı
              </p>
              <p className="text-xs text-red-600">
                ≈ {riskResult.economic_risk_tl_per_dekar.toLocaleString("tr-TR")} TL/dönüm potansiyel kayıp
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ── BÖLÜM 4: İLAÇLAMA TAKVİMİ ────────────────────────────────────── */}
      <div ref={calRef} className="rounded-3xl bg-card border border-border/60 shadow-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <SectionHeader title="14 Günlük İlaçlama Takvimi" icon={<Calendar className="h-3.5 w-3.5 text-primary" />} />
          <button onClick={loadForecast} className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition">
            <RefreshCw className="h-3 w-3" />
          </button>
        </div>
        {locationError && (
          <p className="text-[10px] text-muted-foreground flex items-center gap-1">
            <MapPin className="h-3 w-3" />{locationError}
          </p>
        )}

        {forecastLoading ? (
          <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
        ) : forecast.length > 0 ? (
          <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1">
            {forecast.map((day, i) => {
              const isBest = bestSprayDays.includes(i);
              return (
                <div
                  key={day.date}
                  className={`shrink-0 w-28 rounded-2xl p-3 space-y-1.5 border transition ${
                    isBest ? "border-green-400 bg-green-50" :
                    day.suitability === "caution" ? "border-amber-200 bg-amber-50/40" :
                    day.suitability === "unsuitable" ? "border-red-200 bg-red-50/30" :
                    "border-border/60 bg-card"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-bold text-muted-foreground">{day.weekday}</p>
                    {isBest && <span className="text-[9px] text-green-700 font-bold">İDEAL</span>}
                  </div>
                  <p className="text-xs font-semibold text-foreground">{day.day_label}</p>
                  <div className="space-y-0.5 text-[10px] text-muted-foreground">
                    <div className="flex items-center gap-1"><Thermometer className="h-2.5 w-2.5" />{day.temp_max}°C</div>
                    <div className="flex items-center gap-1"><CloudRain className="h-2.5 w-2.5" />{day.rain}mm</div>
                    <div className="flex items-center gap-1"><Wind className="h-2.5 w-2.5" />{day.wind} km/s</div>
                  </div>
                  <div className={`flex items-center gap-1 text-[9px] font-bold rounded-full px-1.5 py-0.5 w-fit ${
                    day.suitability === "ideal" ? "bg-green-100 text-green-700" :
                    day.suitability === "caution" ? "bg-amber-100 text-amber-700" :
                    "bg-red-100 text-red-700"
                  }`}>
                    {day.suitability === "ideal" ? "✅" : day.suitability === "caution" ? "⚠️" : "❌"}
                    {day.suggestion}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-6 text-sm text-muted-foreground">Hava tahmini alınamadı.</div>
        )}
      </div>

      {/* ── BÖLÜM 5: VERİM KAYIP HESAPLAYICI ─────────────────────────────── */}
      <div className="rounded-3xl bg-card border border-border/60 shadow-card p-4 space-y-4">
        <SectionHeader title="Ekonomik Etki Hesaplayıcı" icon={<TrendingDown className="h-3.5 w-3.5 text-primary" />} />

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <p className="text-[10px] text-muted-foreground font-medium">Tarla (dönüm)</p>
            <input
              type="number" min={0.1} step={0.5}
              value={calcForm.fieldSize}
              onChange={(e) => { setCalcReady(false); setCalcForm((p) => ({ ...p, fieldSize: parseFloat(e.target.value) || 1 })); }}
              className="w-full rounded-xl border border-border/60 bg-background text-sm p-2 text-foreground"
            />
          </div>
          <div className="space-y-1">
            <p className="text-[10px] text-muted-foreground font-medium">Bitki Türü</p>
            <select
              value={calcForm.crop}
              onChange={(e) => {
                const crop = e.target.value;
                setCalcReady(false);
                setCalcForm((p) => ({ ...p, crop, price: CROP_DATA[crop]?.price ?? 8 }));
              }}
              className="w-full rounded-xl border border-border/60 bg-background text-xs p-2 text-foreground"
            >
              {Object.keys(CROP_DATA).map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="space-y-1">
            <p className="text-[10px] text-muted-foreground font-medium">Pazar Fiyatı (TL/kg)</p>
            <input
              type="number" min={0.1} step={0.5}
              value={calcForm.price}
              onChange={(e) => { setCalcReady(false); setCalcForm((p) => ({ ...p, price: parseFloat(e.target.value) || 1 })); }}
              className="w-full rounded-xl border border-border/60 bg-background text-sm p-2 text-foreground"
            />
          </div>
          <div className="space-y-1">
            <div className="flex justify-between text-[10px]">
              <span className="text-muted-foreground font-medium">Hastalık Şiddeti</span>
              <span className="font-bold text-foreground">%{calcForm.severity}</span>
            </div>
            <Slider
              min={0} max={100} step={1}
              value={[calcForm.severity]}
              onValueChange={([v]) => { setCalcReady(false); setCalcForm((p) => ({ ...p, severity: v })); }}
            />
          </div>
        </div>

        <button
          onClick={() => setCalcReady(true)}
          className="w-full rounded-2xl bg-leaf-gradient py-3 text-sm font-bold text-primary-foreground active:scale-[0.98] transition"
        >
          HESAPLA
        </button>

        {calcReady && (
          <div className="space-y-2 border-t border-border/40 pt-3">
            <div className="rounded-2xl bg-red-50 border border-red-200 p-3">
              <p className="text-[10px] text-red-600 font-medium">Tahmini Verim Kaybı</p>
              <p className="text-2xl font-extrabold text-red-600 tabular-nums">
                {lossVal.toLocaleString("tr-TR")} TL
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-2xl bg-amber-50 border border-amber-200 p-3">
                <p className="text-[10px] text-amber-700 font-medium">Müdahale Maliyeti</p>
                <p className="text-base font-bold text-amber-700 tabular-nums">{intVal.toLocaleString("tr-TR")} TL</p>
                <p className="text-[9px] text-muted-foreground">İlaç + işçilik tahmini</p>
              </div>
              <div className="rounded-2xl bg-green-50 border border-green-200 p-3">
                <p className="text-[10px] text-green-700 font-medium">Net Tasarruf</p>
                <p className="text-base font-bold text-green-700 tabular-nums">{netVal.toLocaleString("tr-TR")} TL</p>
                <span className={`text-[9px] font-bold rounded-full px-2 py-0.5 ${lossTarget > intTarget ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                  Müdahale {lossTarget > intTarget ? "karlı ✓" : "karlı değil ✗"}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── BÖLÜM 6: YAYILMA SİMÜLASYONU ─────────────────────────────────── */}
      <div className="rounded-3xl bg-card border border-border/60 shadow-card p-4 space-y-4">
        <SectionHeader title="Yayılma Senaryosu" icon={<Activity className="h-3.5 w-3.5 text-primary" />} />

        <div className="grid grid-cols-2 gap-3">
          <SimGrid grid={noIntGrid} label="Müdahale Yok" />
          <SimGrid grid={withIntGrid} label={`Gün ${interventionDay}'de Müdahale`} />
        </div>

        {/* Progress */}
        <div className="grid grid-cols-2 gap-2 text-center">
          <div className="rounded-xl bg-red-50 p-2">
            <p className="text-xs font-bold text-red-600">{noIntInfected}/{GRID_SIZE * GRID_SIZE}</p>
            <p className="text-[9px] text-muted-foreground">Etkilenen hücre (müdahalesiz)</p>
          </div>
          <div className="rounded-xl bg-teal-50 p-2">
            <p className="text-xs font-bold text-teal-600">{withIntInfected}/{GRID_SIZE * GRID_SIZE}</p>
            <p className="text-[9px] text-muted-foreground">Etkilenen hücre (müdahale ile)</p>
          </div>
        </div>

        {/* Intervention day slider */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Müdahale Günü</span>
            <span className="font-bold text-foreground">{interventionDay}. gün</span>
          </div>
          <Slider
            min={1} max={15} step={1}
            value={[interventionDay]}
            onValueChange={([v]) => { setInterventionDay(v); resetSim(); }}
          />
        </div>

        <p className="text-[10px] text-muted-foreground">Adım: {simStep}/20</p>

        <div className="flex gap-2">
          <button
            onClick={startSim}
            disabled={simRunning}
            className="flex-1 rounded-2xl bg-leaf-gradient py-3 text-sm font-bold text-primary-foreground disabled:opacity-50 active:scale-[0.98] transition"
          >
            {simRunning ? "Çalışıyor..." : "Simülasyonu Başlat"}
          </button>
          <button
            onClick={resetSim}
            className="rounded-2xl border border-border/60 px-4 py-3 text-sm font-semibold hover:bg-muted/40 transition"
          >
            Sıfırla
          </button>
        </div>

        <p className="text-[10px] text-muted-foreground italic">
          Bu simülasyon ortalama külleme yayılma hızına (günde %8–12 alan artışı) göre hesaplanmaktadır.
        </p>

        {/* Legend */}
        <div className="flex flex-wrap gap-3">
          {[
            { color: "bg-green-400", label: "Sağlıklı" },
            { color: "bg-red-500", label: "Hasta" },
            { color: "bg-amber-400", label: "Risk altında" },
            { color: "bg-teal-400", label: "İyileşti" },
          ].map(({ color, label }) => (
            <span key={label} className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <span className={`${color} h-3 w-3 rounded-sm inline-block`} /> {label}
            </span>
          ))}
        </div>
      </div>

      {/* ── BÖLÜM 7: HASTALIK DAĞILIMI ────────────────────────────────────── */}
      <div ref={diseaseRef} className="rounded-3xl bg-card border border-border/60 shadow-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <SectionHeader title="Hastalık Dağılımı" icon={<Leaf className="h-3.5 w-3.5 text-primary" />} />
          {summary?.is_demo && (
            <span className="text-[9px] font-bold text-primary bg-primary/10 rounded-full px-2 py-0.5">Demo</span>
          )}
        </div>

        {summaryLoading ? (
          <div className="h-40 flex items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
        ) : summary?.disease_distribution.length ? (
          <>
            <div className="flex items-center gap-4">
              <PieChart width={140} height={140}>
                <Pie
                  data={summary.disease_distribution}
                  cx={65} cy={65}
                  innerRadius={40} outerRadius={62}
                  dataKey="count"
                  startAngle={90} endAngle={-270}
                >
                  {summary.disease_distribution.map((_, i) => (
                    <Cell key={i} fill={DISEASE_COLORS[i % DISEASE_COLORS.length]} />
                  ))}
                </Pie>
              </PieChart>
              <div className="flex-1 space-y-1.5">
                {summary.disease_distribution.map((d, i) => (
                  <div key={d.name} className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: DISEASE_COLORS[i % DISEASE_COLORS.length] }} />
                    <span className="text-[11px] text-foreground font-medium flex-1 truncate">{d.name}</span>
                    <span className="text-[10px] text-muted-foreground">{d.count}×</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-1.5 border-t border-border/40 pt-3">
              {summary.disease_distribution.map((d, i) => (
                <div key={d.name} className="flex items-center justify-between rounded-xl bg-muted/40 px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: DISEASE_COLORS[i % DISEASE_COLORS.length] }} />
                    <p className="text-xs font-semibold text-foreground">{d.name}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-bold text-foreground">{d.count} analiz</p>
                    <p className="text-[10px] text-muted-foreground">{d.last_date}</p>
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="text-center py-6 text-sm text-muted-foreground">Yeterli veri yok.</div>
        )}
      </div>

      {/* ── BÖLÜM 8: AYLIK RAPOR ──────────────────────────────────────────── */}
      <div className="space-y-3">
        <SectionHeader title="Aylık Raporlar" icon={<FileBarChart2 className="h-3.5 w-3.5 text-primary" />} />

        {summaryLoading ? (
          <div className="h-24 flex items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
        ) : summary?.monthly_data.length ? (
          summary.monthly_data.map((m) => (
            <div key={`${m.year}-${m.month}`} className="rounded-3xl bg-card border border-border/60 shadow-card p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10">
                  <FileBarChart2 className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-bold text-foreground">{m.label} — Sağlık Raporu</p>
                  <p className="text-[11px] text-muted-foreground">
                    {m.total} analiz · %{m.health_pct} sağlıklı · En sık: {m.top_disease}
                  </p>
                </div>
                <span className={`flex items-center gap-1 text-[11px] font-bold rounded-full px-2 py-0.5 ${m.health_pct >= 70 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                  {m.health_pct >= 70 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                  %{m.health_pct}
                </span>
              </div>
              <button
                onClick={() => {
                  console.log("[PDF] Rapor indirme:", m.label);
                  toast.info("PDF indirme özelliği yakında aktif olacak.");
                }}
                className="mt-3 w-full rounded-2xl border border-border/60 py-2.5 text-xs font-semibold text-muted-foreground hover:bg-muted/40 flex items-center justify-center gap-2 transition"
              >
                <Download className="h-3.5 w-3.5" /> PDF İndir
              </button>
            </div>
          ))
        ) : (
          <div className="rounded-3xl bg-card border border-border/60 shadow-card p-5 text-center space-y-2">
            <FileBarChart2 className="mx-auto h-8 w-8 text-muted-foreground/30" />
            <p className="text-sm font-semibold text-muted-foreground">
              {new Date().toLocaleDateString("tr-TR", { month: "long", year: "numeric" })} raporu hazırlanıyor
            </p>
            <p className="text-xs text-muted-foreground">Analizler yaptıkça aylık raporlarınız burada görünür.</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── MetricCard ────────────────────────────────────────────────────────────────

function MetricCard({
  title, value, sub, icon, accent, isDemo, onClick, ring,
}: {
  title: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
  accent?: "green" | "amber" | "red";
  isDemo?: boolean;
  onClick?: () => void;
  ring?: number;
}) {
  const accentBg = accent === "green" ? "bg-green-50 border-green-200" : accent === "amber" ? "bg-amber-50 border-amber-200" : accent === "red" ? "bg-red-50 border-red-200" : "bg-card border-border/60";
  const accentText = accent === "green" ? "text-green-700" : accent === "amber" ? "text-amber-700" : accent === "red" ? "text-red-700" : "text-foreground";

  return (
    <button
      onClick={onClick}
      className={`shrink-0 w-36 rounded-2xl border shadow-card p-3.5 text-left space-y-2 active:scale-[0.97] transition ${accentBg}`}
    >
      <div className="flex items-center justify-between">
        {icon}
        {isDemo && <span className="text-[9px] font-bold text-primary bg-primary/10 rounded-full px-1.5 py-0.5">Demo</span>}
      </div>
      {ring !== undefined ? (
        <div className="relative h-9 w-9">
          <svg viewBox="0 0 36 36" className="w-9 h-9 -rotate-90">
            <circle cx="18" cy="18" r="14" fill="none" stroke="#e2e8f0" strokeWidth="4" />
            <circle
              cx="18" cy="18" r="14" fill="none"
              stroke={accent === "green" ? "#22c55e" : accent === "amber" ? "#f59e0b" : "#ef4444"}
              strokeWidth="4"
              strokeDasharray={`${(ring / 100) * 87.96} 87.96`}
              strokeLinecap="round"
            />
          </svg>
        </div>
      ) : null}
      <div>
        <p className={`text-base font-extrabold leading-tight ${accentText}`}>{value}</p>
        <p className="text-[10px] text-muted-foreground leading-tight">{title}</p>
        <p className="text-[9px] text-muted-foreground mt-0.5">{sub}</p>
      </div>
      <ChevronRight className="h-3 w-3 text-muted-foreground" />
    </button>
  );
}
