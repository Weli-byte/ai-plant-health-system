// =============================================================================
// components/RiskPredictionWidget.tsx
//
// Sprint 3 — Risk Tahmin Bileşeni
//
// Çevre verilerini form ile alıp backend'in /api/predict-risk endpoint'ine
// gönderir, sonucu (risk_score + risk_level + öneri mesajı) gösterir.
// Dashboard'da sergilenmek üzere tasarlanmıştır.
// =============================================================================

import { useState, type FormEvent } from "react";
import {
    predictRisk,
    riskLevelBadgeClass,
    RiskApiError,
    type RiskPredictionInput,
    type RiskPredictionResponse,
    type Season,
} from "../services/riskService";

const DEFAULTS: RiskPredictionInput = {
    temperature: 24.5,
    humidity: 78,
    rainfall: 12,
    wind_speed: 8,
    soil_moisture: 55,
    season: "summer",
};

const SEASONS: Season[] = ["spring", "summer", "autumn", "winter"];

export default function RiskPredictionWidget() {
    const [form, setForm] = useState<RiskPredictionInput>(DEFAULTS);
    const [result, setResult] = useState<RiskPredictionResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleNumber = (key: keyof RiskPredictionInput) =>
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const v = parseFloat(e.target.value);
            setForm((s) => ({ ...s, [key]: Number.isFinite(v) ? v : 0 }));
        };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);
        setResult(null);
        setLoading(true);
        try {
            const res = await predictRisk(form);
            setResult(res);
        } catch (err) {
            if (err instanceof RiskApiError) {
                setError(err.detail);
            } else {
                setError(
                    "Sunucuya ulaşılamadı. Backend'in çalıştığından emin olun."
                );
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-earth-200">
            <div className="mb-4">
                <h3 className="text-xl font-bold text-earth-800">
                    🌦️ Çevresel Risk Tahmini
                </h3>
                <p className="text-sm text-earth-500">
                    Çevre verilerini girin; XGBoost modeli hastalık riskini hesaplasın.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <label className="text-sm">
                    <span className="text-earth-600">Sıcaklık (°C)</span>
                    <input
                        type="number" step="0.1" min={-20} max={60}
                        value={form.temperature}
                        onChange={handleNumber("temperature")}
                        className="mt-1 w-full px-3 py-2 rounded-xl border border-earth-200 focus:outline-none focus:ring-2 focus:ring-green-500"
                    />
                </label>
                <label className="text-sm">
                    <span className="text-earth-600">Nem (%)</span>
                    <input
                        type="number" step="0.1" min={0} max={100}
                        value={form.humidity}
                        onChange={handleNumber("humidity")}
                        className="mt-1 w-full px-3 py-2 rounded-xl border border-earth-200 focus:outline-none focus:ring-2 focus:ring-green-500"
                    />
                </label>
                <label className="text-sm">
                    <span className="text-earth-600">Yağış (mm/gün)</span>
                    <input
                        type="number" step="0.1" min={0} max={500}
                        value={form.rainfall}
                        onChange={handleNumber("rainfall")}
                        className="mt-1 w-full px-3 py-2 rounded-xl border border-earth-200 focus:outline-none focus:ring-2 focus:ring-green-500"
                    />
                </label>
                <label className="text-sm">
                    <span className="text-earth-600">Rüzgar (km/sa)</span>
                    <input
                        type="number" step="0.1" min={0} max={200}
                        value={form.wind_speed}
                        onChange={handleNumber("wind_speed")}
                        className="mt-1 w-full px-3 py-2 rounded-xl border border-earth-200 focus:outline-none focus:ring-2 focus:ring-green-500"
                    />
                </label>
                <label className="text-sm">
                    <span className="text-earth-600">Toprak Nemi (%)</span>
                    <input
                        type="number" step="0.1" min={0} max={100}
                        value={form.soil_moisture}
                        onChange={handleNumber("soil_moisture")}
                        className="mt-1 w-full px-3 py-2 rounded-xl border border-earth-200 focus:outline-none focus:ring-2 focus:ring-green-500"
                    />
                </label>
                <label className="text-sm">
                    <span className="text-earth-600">Mevsim</span>
                    <select
                        value={form.season}
                        onChange={(e) => setForm((s) => ({ ...s, season: e.target.value as Season }))}
                        className="mt-1 w-full px-3 py-2 rounded-xl border border-earth-200 focus:outline-none focus:ring-2 focus:ring-green-500"
                    >
                        {SEASONS.map((s) => (
                            <option key={s} value={s}>{s}</option>
                        ))}
                    </select>
                </label>

                <div className="md:col-span-2 mt-2">
                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-green-600 text-white font-bold py-3 rounded-xl shadow hover:bg-green-700 transition disabled:opacity-60"
                    >
                        {loading ? "Hesaplanıyor..." : "Risk Tahmin Et"}
                    </button>
                </div>
            </form>

            {error && (
                <div className="mt-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
                    {error}
                </div>
            )}

            {result && (
                <div className="mt-4 p-4 rounded-2xl border border-earth-200 bg-earth-50">
                    <div className="flex items-center justify-between">
                        <span className="text-earth-600 text-sm">Risk Skoru</span>
                        <span className="text-2xl font-extrabold text-earth-800">
                            {(result.risk_score * 100).toFixed(1)}%
                        </span>
                    </div>
                    <div className="mt-3 flex items-center justify-between">
                        <span className="text-earth-600 text-sm">Seviye</span>
                        <span
                            className={
                                "px-3 py-1 rounded-full text-xs font-bold border " +
                                riskLevelBadgeClass(result.risk_level)
                            }
                        >
                            {result.risk_level.toUpperCase()}
                        </span>
                    </div>
                    <p className="mt-3 text-sm text-earth-700">{result.message}</p>
                    <p className="mt-1 text-xs text-earth-400">
                        Model: v{result.model_version}
                    </p>
                </div>
            )}
        </div>
    );
}
