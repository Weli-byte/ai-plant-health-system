// =============================================================================
// services/riskService.ts
//
// Sprint 3 & 4 — Plant Risk Prediction
//
// Bu modül, hem Sprint 3 (legacy) hem de Sprint 4 (V2, Multimodal, Digital Twin)
// risk tahmin endpoint'leri için tip-güvenli API çağrıları sağlar.
// =============================================================================

const API_BASE_URL = "http://localhost:8000";

// --- Sprint 3 Types (Legacy) ---
export type Season = "spring" | "summer" | "autumn" | "winter";
export type RiskLevel = "low" | "medium" | "high";

export interface RiskPredictionInput {
    temperature: number;     // °C
    humidity: number;        // %
    rainfall: number;        // mm
    wind_speed: number;      // km/sa
    soil_moisture: number;   // %
    season: Season;
}

export interface RiskPredictionResponse {
    success: boolean;
    risk_score: number;
    risk_level: RiskLevel;
    model_version: string;
    message: string;
}

// --- Sprint 4 Types (Advanced) ---

export type SoilType = "clay" | "sandy" | "loam" | "silt" | "peat" | "chalky";
export type CropType = "tomato" | "wheat" | "corn" | "rice" | "potato" | "grape";

// 1. Risk V2 (XGBoost)
export interface RiskPredictRequestV2 {
    temperature: number;
    humidity: number;
    rainfall: number;
    soil_type: SoilType;
    crop_type: CropType;
}

export interface RiskPredictResponseV2 {
    success: boolean;
    data: {
        risk_score: number;      // 0-100
        risk_level: RiskLevel;
        model_version: string;
        metrics?: Record<string, number>;
    };
    message: string;
}

// 2. Multimodal (Image + Weather)
export interface WeatherInput {
    temperature: number;
    humidity: number;
    rainfall: number;
    wind_speed: number;
    soil_moisture: number;
}

export interface MultimodalPredictRequest {
    image_base64: string;    // Raw base64 or data:image/jpeg;base64,...
    weather: WeatherInput;
    soil_type: SoilType;
}

export interface MultimodalPredictResponse {
    success: boolean;
    data: any;               // Task-dependent (regression or classification)
    message: string;
}

// 3. Digital Twin (LSTM Forecast)
export interface DigitalTwinRequest {
    // 7 features per day: [risk, temp, humid, rain, wind, soil, health]
    observations: number[][]; 
}

export interface DigitalTwinResponse {
    success: boolean;
    data: {
        horizons_days: number[];
        risk_scores: number[];
        risk_levels: RiskLevel[];
        model_version: string;
    };
    message: string;
}

// --- Error Handling ---

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

async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
            const errBody = await response.json();
            if (typeof errBody?.detail === "string") {
                detail = errBody.detail;
            } else if (Array.isArray(errBody?.detail)) {
                detail = errBody.detail
                    .map((e: any) => `${(e.loc ?? []).join(".")}: ${e.msg ?? "geçersiz"}`)
                    .join(" | ");
            }
        } catch { /* ignore parse error */ }
        throw new RiskApiError(response.status, detail);
    }
    return (await response.json()) as T;
}

// --- API Functions ---

/**
 * [Sprint 3] Baseline Risk Prediction (Legacy)
 */
export async function predictRisk(input: RiskPredictionInput): Promise<RiskPredictionResponse> {
    const response = await fetch(`${API_BASE_URL}/api/predict-risk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
    });
    return handleResponse<RiskPredictionResponse>(response);
}

/**
 * [Sprint 4] Advanced XGBoost Risk V2
 */
export async function predictRiskV2(input: RiskPredictRequestV2): Promise<RiskPredictResponseV2> {
    const response = await fetch(`${API_BASE_URL}/api/v2/predict_risk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
    });
    return handleResponse<RiskPredictResponseV2>(response);
}

/**
 * [Sprint 4] Multimodal Inference (PyTorch)
 */
export async function predictMultimodal(input: MultimodalPredictRequest): Promise<MultimodalPredictResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v2/multimodal_predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
    });
    return handleResponse<MultimodalPredictResponse>(response);
}

/**
 * [Sprint 4] Digital Twin LSTM Forecast
 */
export async function predictFuture(input: DigitalTwinRequest): Promise<DigitalTwinResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v2/predict_future`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
    });
    return handleResponse<DigitalTwinResponse>(response);
}

/**
 * UI için renk/rozet eşleyici — risk seviyesine göre Tailwind sınıfı döner.
 */
export function riskLevelBadgeClass(level: RiskLevel): string {
    switch (level) {
        case "low":
            return "bg-green-100/10 text-green-400 border border-green-500/30";
        case "medium":
            return "bg-amber-100/10 text-amber-400 border border-amber-500/30";
        case "high":
            return "bg-red-100/10 text-red-400 border border-red-500/30";
        default:
            return "bg-slate-100/10 text-slate-400 border border-slate-500/30";
    }
}
