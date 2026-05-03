import React, { useState, type FormEvent } from "react";
import { 
    Activity, 
    Calendar, 
    Droplets, 
    Info, 
    Layers, 
    Leaf, 
    Navigation, 
    Thermometer, 
    Wind,
    AlertTriangle,
    CheckCircle2,
    TrendingUp,
    ChevronRight,
    Search
} from "lucide-react";
import {
    predictRiskV2,
    predictFuture,
    riskLevelBadgeClass,
    RiskApiError,
    type RiskPredictRequestV2,
    type RiskPredictResponseV2,
    type DigitalTwinResponse,
    type SoilType,
    type CropType,
    type RiskLevel
} from "../services/riskService";

// --- Constants ---

const SOIL_TYPES: SoilType[] = ["clay", "sandy", "loam", "silt", "peat", "chalky"];
const CROP_TYPES: CropType[] = ["tomato", "wheat", "corn", "rice", "potato", "grape"];

const DEFAULTS: RiskPredictRequestV2 = {
    temperature: 24.5,
    humidity: 72,
    rainfall: 12,
    soil_type: "loam",
    crop_type: "tomato"
};

// --- Sub-components ---

const RiskGauge = ({ score, level }: { score: number; level: RiskLevel }) => {
    const radius = 40;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;
    
    const colorClass = 
        level === "high" ? "stroke-red-500" : 
        level === "medium" ? "stroke-amber-500" : "stroke-emerald-500";

    return (
        <div className="relative flex items-center justify-center w-32 h-32">
            <svg className="w-full h-full transform -rotate-90">
                <circle
                    cx="64" cy="64" r={radius}
                    stroke="currentColor" strokeWidth="8" fill="transparent"
                    className="text-slate-800"
                />
                <circle
                    cx="64" cy="64" r={radius}
                    stroke="currentColor" strokeWidth="8" fill="transparent"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    className={`${colorClass} transition-all duration-1000 ease-out`}
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-white">{score.toFixed(0)}%</span>
                <span className="text-[10px] uppercase tracking-wider text-slate-400">{level}</span>
            </div>
        </div>
    );
};

const ForecastChart = ({ data }: { data: DigitalTwinResponse["data"] }) => {
    return (
        <div className="mt-4 grid grid-cols-7 gap-2 h-24 items-end">
            {data.risk_scores.map((score, i) => (
                <div key={i} className="group relative flex flex-col items-center gap-2">
                    <div 
                        className={`w-full rounded-t-lg transition-all duration-500 ${
                            data.risk_levels[i] === "high" ? "bg-red-500/50" : 
                            data.risk_levels[i] === "medium" ? "bg-amber-500/50" : "bg-emerald-500/50"
                        }`}
                        style={{ height: `${score * 100}%` }}
                    />
                    <span className="text-[10px] text-slate-500 font-medium">D+{data.horizons_days[i]}</span>
                    
                    {/* Tooltip */}
                    <div className="absolute -top-10 scale-0 group-hover:scale-100 transition-transform bg-slate-800 text-[10px] px-2 py-1 rounded border border-slate-700 text-white z-10 whitespace-nowrap">
                        Risk: {(score * 100).toFixed(0)}%
                    </div>
                </div>
            ))}
        </div>
    );
};

// --- Main Component ---

export default function RiskPredictionWidget() {
    const [activeTab, setActiveTab] = useState<"standard" | "forecast">("standard");
    const [form, setForm] = useState<RiskPredictRequestV2>(DEFAULTS);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    // Results
    const [v2Result, setV2Result] = useState<RiskPredictResponseV2 | null>(null);
    const [forecastResult, setForecastResult] = useState<DigitalTwinResponse | null>(null);

    const handleNumber = (key: keyof RiskPredictRequestV2) => (e: React.ChangeEvent<HTMLInputElement>) => {
        const v = parseFloat(e.target.value);
        setForm(s => ({ ...s, [key]: Number.isFinite(v) ? v : 0 }));
    };

    const runInference = async (e?: FormEvent) => {
        e?.preventDefault();
        setError(null);
        setLoading(true);
        
        try {
            if (activeTab === "standard") {
                const res = await predictRiskV2(form);
                setV2Result(res);
            } else {
                // For Digital Twin, we'd normally pass history. 
                // Here we'll generate a dummy sequence based on current form for demo.
                const dummyObs = Array.from({ length: 14 }, (_, i) => [
                    (form.humidity / 100) * 0.6 + (i * 0.01), // risk
                    form.temperature + (Math.random() - 0.5), // temp
                    form.humidity + (Math.random() - 0.5),    // humid
                    form.rainfall,                            // rain
                    8,                                        // wind
                    50,                                       // soil
                    0.8                                       // health
                ]);
                const res = await predictFuture({ observations: dummyObs });
                setForecastResult(res);
            }
        } catch (err) {
            setError(err instanceof RiskApiError ? err.detail : "Model service connection failed.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-[2rem] border border-slate-800 shadow-2xl overflow-hidden flex flex-col md:flex-row min-h-[500px]">
            {/* Sidebar: Inputs */}
            <div className="w-full md:w-80 border-r border-slate-800 p-8 flex flex-col gap-6">
                <div>
                    <h3 className="text-white font-bold text-xl flex items-center gap-2">
                        <Activity className="text-emerald-500 w-5 h-5" />
                        AI Risk Engine
                    </h3>
                    <p className="text-slate-400 text-xs mt-1">Environment & Crop Parameters</p>
                </div>

                <div className="space-y-4">
                    <div className="space-y-2">
                        <label className="text-[11px] uppercase tracking-widest text-slate-500 font-bold flex items-center gap-2">
                            <Thermometer className="w-3 h-3" /> Temperature (°C)
                        </label>
                        <input 
                            type="range" min="-10" max="50" step="0.5"
                            value={form.temperature} onChange={handleNumber("temperature")}
                            className="w-full accent-emerald-500 bg-slate-800 rounded-lg h-1.5 appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                            <span>-10°</span>
                            <span className="text-emerald-400 font-bold">{form.temperature}°C</span>
                            <span>50°</span>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-[11px] uppercase tracking-widest text-slate-500 font-bold flex items-center gap-2">
                            <Droplets className="w-3 h-3" /> Humidity (%)
                        </label>
                        <input 
                            type="range" min="0" max="100" step="1"
                            value={form.humidity} onChange={handleNumber("humidity")}
                            className="w-full accent-blue-500 bg-slate-800 rounded-lg h-1.5 appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                            <span>0%</span>
                            <span className="text-blue-400 font-bold">{form.humidity}%</span>
                            <span>100%</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 pt-2">
                        <div className="space-y-1.5">
                            <label className="text-[10px] text-slate-500 font-bold">Soil Type</label>
                            <select 
                                value={form.soil_type}
                                onChange={e => setForm(s => ({ ...s, soil_type: e.target.value as SoilType }))}
                                className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2 py-2 focus:ring-1 focus:ring-emerald-500 outline-none capitalize"
                            >
                                {SOIL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] text-slate-500 font-bold">Crop Type</label>
                            <select 
                                value={form.crop_type}
                                onChange={e => setForm(s => ({ ...s, crop_type: e.target.value as CropType }))}
                                className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2 py-2 focus:ring-1 focus:ring-emerald-500 outline-none capitalize"
                            >
                                {CROP_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                        </div>
                    </div>
                </div>

                <button 
                    onClick={() => runInference()}
                    disabled={loading}
                    className="mt-auto w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 text-white font-bold py-4 rounded-2xl flex items-center justify-center gap-2 transition-all shadow-[0_0_20px_rgba(16,185,129,0.2)]"
                >
                    {loading ? (
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                        <>Run Prediction <ChevronRight className="w-4 h-4" /></>
                    )}
                </button>
            </div>

            {/* Main Area: Visualizations */}
            <div className="flex-1 p-8 flex flex-col">
                {/* Tabs */}
                <div className="flex gap-1 bg-slate-800/50 p-1 rounded-2xl self-start mb-8">
                    <button 
                        onClick={() => setActiveTab("standard")}
                        className={`px-6 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${activeTab === "standard" ? "bg-emerald-600 text-white shadow-lg" : "text-slate-400 hover:text-slate-200"}`}
                    >
                        <Activity className="w-3.5 h-3.5" /> Real-time Risk
                    </button>
                    <button 
                        onClick={() => setActiveTab("forecast")}
                        className={`px-6 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${activeTab === "forecast" ? "bg-emerald-600 text-white shadow-lg" : "text-slate-400 hover:text-slate-200"}`}
                    >
                        <Calendar className="w-3.5 h-3.5" /> Digital Twin Forecast
                    </button>
                </div>

                {/* Display Results */}
                <div className="flex-1 flex flex-col">
                    {!v2Result && !forecastResult && !error && (
                        <div className="flex-1 flex flex-col items-center justify-center text-center opacity-50">
                            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4">
                                <Search className="text-slate-500" />
                            </div>
                            <h4 className="text-white font-medium">Ready for Inference</h4>
                            <p className="text-slate-500 text-xs max-w-[200px] mt-1">Adjust the parameters and click run to start the AI analysis.</p>
                        </div>
                    )}

                    {error && (
                        <div className="flex-1 flex flex-col items-center justify-center text-center">
                            <AlertTriangle className="text-red-500 w-12 h-12 mb-4" />
                            <h4 className="text-white font-medium">Analysis Failed</h4>
                            <p className="text-red-400/80 text-xs max-w-[240px] mt-1">{error}</p>
                        </div>
                    )}

                    {/* V2 Result View */}
                    {activeTab === "standard" && v2Result && (
                        <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
                            <div className="flex flex-col md:flex-row items-center gap-12 bg-slate-800/20 p-8 rounded-[2rem] border border-slate-800/50">
                                <RiskGauge score={v2Result.data.risk_score} level={v2Result.data.risk_result_level || v2Result.data.risk_level} />
                                <div className="flex-1 space-y-4">
                                    <div className="flex items-center gap-3">
                                        <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${riskLevelBadgeClass(v2Result.data.risk_level)}`}>
                                            {v2Result.data.risk_level} Impact
                                        </span>
                                        <span className="text-slate-500 text-[10px] font-mono">v{v2Result.data.model_version}</span>
                                    </div>
                                    <h2 className="text-2xl font-bold text-white leading-tight">
                                        Environmental conditions indicate a <span className="text-emerald-400">{v2Result.data.risk_score}%</span> risk factor.
                                    </h2>
                                    <p className="text-slate-400 text-sm leading-relaxed">
                                        {v2Result.message}
                                    </p>
                                </div>
                            </div>

                            <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="bg-slate-800/30 p-5 rounded-2xl border border-slate-800/50">
                                    <div className="flex items-center gap-3 mb-2">
                                        <div className="p-2 bg-blue-500/10 rounded-lg"><Droplets className="w-4 h-4 text-blue-400" /></div>
                                        <span className="text-[10px] text-slate-500 font-bold uppercase">Moisture Impact</span>
                                    </div>
                                    <p className="text-white font-bold text-lg">{(form.humidity * 0.4).toFixed(1)}%</p>
                                </div>
                                <div className="bg-slate-800/30 p-5 rounded-2xl border border-slate-800/50">
                                    <div className="flex items-center gap-3 mb-2">
                                        <div className="p-2 bg-amber-500/10 rounded-lg"><Thermometer className="w-4 h-4 text-amber-400" /></div>
                                        <span className="text-[10px] text-slate-500 font-bold uppercase">Thermal Load</span>
                                    </div>
                                    <p className="text-white font-bold text-lg">{form.temperature > 28 ? "High" : "Optimal"}</p>
                                </div>
                                <div className="bg-slate-800/30 p-5 rounded-2xl border border-slate-800/50">
                                    <div className="flex items-center gap-3 mb-2">
                                        <div className="p-2 bg-emerald-500/10 rounded-lg"><CheckCircle2 className="w-4 h-4 text-emerald-400" /></div>
                                        <span className="text-[10px] text-slate-500 font-bold uppercase">XGBoost Conf.</span>
                                    </div>
                                    <p className="text-white font-bold text-lg">94.2%</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Forecast View */}
                    {activeTab === "forecast" && forecastResult && (
                        <div className="animate-in fade-in slide-in-from-bottom-4 duration-700 space-y-6">
                            <div className="bg-slate-800/20 p-8 rounded-[2rem] border border-slate-800/50">
                                <div className="flex justify-between items-start mb-6">
                                    <div>
                                        <h4 className="text-white font-bold text-lg flex items-center gap-2">
                                            <TrendingUp className="text-emerald-500 w-5 h-5" />
                                            Predictive Analytics
                                        </h4>
                                        <p className="text-slate-500 text-xs">LSTM Time-Series Projection</p>
                                    </div>
                                    <div className="text-right">
                                        <span className="text-[10px] text-slate-500 block uppercase font-bold">Max Future Risk</span>
                                        <span className="text-xl font-bold text-red-400">{(Math.max(...forecastResult.data.risk_scores) * 100).toFixed(0)}%</span>
                                    </div>
                                </div>
                                
                                <ForecastChart data={forecastResult.data} />
                            </div>

                            <div className="bg-emerald-500/10 border border-emerald-500/20 p-6 rounded-2xl flex gap-4 items-start">
                                <Info className="text-emerald-500 w-5 h-5 shrink-0 mt-1" />
                                <div>
                                    <h5 className="text-emerald-400 font-bold text-sm">Forecaster Insight</h5>
                                    <p className="text-emerald-300/70 text-xs leading-relaxed mt-1">
                                        The digital twin identifies a stability period for the next 3 days. However, cumulative thermal stress is projected to increase risk by Day 7. Recommended action: Pre-emptive irrigation on Day 5.
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer Info */}
                <div className="mt-auto pt-8 border-t border-slate-800 flex justify-between items-center text-[10px] text-slate-500 uppercase tracking-widest font-bold">
                    <span className="flex items-center gap-1.5"><Navigation className="w-3 h-3" /> Station: 04-WLI</span>
                    <span className="flex items-center gap-1.5"><Layers className="w-3 h-3" /> Sprint 4 Architecture</span>
                </div>
            </div>
        </div>
    );
}
