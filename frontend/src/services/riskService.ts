// =============================================================================
// services/riskService.ts
//
// Sprint 3 — Plant Risk Prediction
//
// Bu modül, backend'in /api/predict-risk endpoint'i için tip-güvenli bir
// API çağrı fonksiyonu sağlar. Projenin mevcut konvansiyonu ile uyumludur:
// native fetch + http://localhost:8000 (bkz. Dashboard.tsx, Analyze.tsx vb.).
// =============================================================================

const API_BASE_URL = "http://localhost:8000";

export type Season = "spring" | "summer" | "autumn" | "winter";
export type RiskLevel = "low" | "medium" | "high";

export interface RiskPredictionInput {
    temperature: number;     // °C, [-20, 60]
    humidity: number;        // %,  [0, 100]
    rainfall: number;        // mm, [0, 500]
    wind_speed: number;      // km/sa, [0, 200]
    soil_moisture: number;   // %, [0, 100]
    season: Season;
}

export interface RiskPredictionResponse {
    success: boolean;
    risk_score: number;      // 0–1
    risk_level: RiskLevel;
    model_version: string;
    message: string;
}

export class RiskApiError extends Error {
    status: number;
    detail: string;

    constructor(status: number, detail: string) {
        super(`[RiskApi ${status}] ${detail}`);
        this.name = "RiskApiError";
        this.status = status;
        this.detail = detail;
    }
}

/**
 * Backend'e çevre verilerini gönderip bitki hastalık risk skoru alır.
 *
 * @throws RiskApiError — backend 4xx/5xx döndürürse.
 * @throws Error        — ağ hatası vb.
 */
export async function predictRisk(
    input: RiskPredictionInput
): Promise<RiskPredictionResponse> {
    const response = await fetch(`${API_BASE_URL}/api/predict-risk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
    });

    if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
            const errBody = await response.json();
            // FastAPI hatası tipik olarak { "detail": "..." } veya
            // şema doğrulama hatası { "detail": [{loc, msg, type}, ...] } şeklindedir.
            if (typeof errBody?.detail === "string") {
                detail = errBody.detail;
            } else if (Array.isArray(errBody?.detail)) {
                detail = errBody.detail
                    .map((e: { loc?: string[]; msg?: string }) =>
                        `${(e.loc ?? []).join(".")}: ${e.msg ?? "geçersiz"}`
                    )
                    .join(" | ");
            }
        } catch {
            /* JSON parse edilemedi → default detail kullanılır */
        }
        throw new RiskApiError(response.status, detail);
    }

    return (await response.json()) as RiskPredictionResponse;
}

/**
 * UI için renk/rozet eşleyici — risk seviyesine göre Tailwind sınıfı döner.
 * (Mevcut tasarım dilini koruyarak earth/green/amber/red paletine yaslanır.)
 */
export function riskLevelBadgeClass(level: RiskLevel): string {
    switch (level) {
        case "low":
            return "bg-green-100 text-green-800 border-green-300";
        case "medium":
            return "bg-amber-100 text-amber-800 border-amber-300";
        case "high":
            return "bg-red-100 text-red-800 border-red-300";
        default:
            return "bg-earth-100 text-earth-800 border-earth-300";
    }
}
