// =============================================================================
// services/api.ts
//
// Merkezi API servis katmanı.
// Tüm backend çağrıları bu dosya üzerinden yapılır.
// Base URL tek bir yerden yönetilir.
// =============================================================================

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Yardımcı: fetch wrapper
// ---------------------------------------------------------------------------

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function requestFormData<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    body: formData,
    // Content-Type otomatik ayarlanır (multipart/form-data)
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Tipler
// ---------------------------------------------------------------------------

export interface User {
  id: number;
  username: string;
  email: string;
}

export interface Plant {
  id: number;
  plant_name: string;
  user_id: number;
  created_at: string;
}

export interface DiseaseRecord {
  id: number;
  plant_id: number;
  disease_name: string;
  confidence_score: number | null;
  created_at: string;
}

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface LeafDetectionResult {
  success: boolean;
  leaf_detected: boolean;
  bounding_box: BoundingBox | null;
  confidence: number | null;
  cropped_leaf_base64: string | null;
  original_width: number;
  original_height: number;
  message: string;
}

export interface DiseaseClassificationResult {
  success: boolean;
  predicted_class: string;
  predicted_class_index: number;
  confidence: number;
  all_scores: Record<string, number>;
  message: string;
}

export interface GradCAMResult {
  success: boolean;
  heatmap_base64: string;
  overlay_base64: string;
  target_class: string;
  target_class_index: number;
  message: string;
}

export interface FullAnalysisResult {
  success: boolean;
  leaf_detection: LeafDetectionResult;
  disease_classification: DiseaseClassificationResult | null;
  gradcam: GradCAMResult | null;
  message: string;
}

export interface ChatResponse {
  success: boolean;
  response: string;
  message: string;
}

export interface PesticideRecommendation {
  disease: string;
  product_type: string;
  active_ingredient: string;
  product_name: string;
  application_notes: string;
}

export interface FarmingAdviceResponse {
  success: boolean;
  risk_level: string;
  farming_advice: string[];
  pesticide_recommendations: PesticideRecommendation[];
  irrigation_advice: string;
  general_notes: string;
  message: string;
}

export interface RiskScoreResponse {
  success: boolean;
  risk_score: number;
  risk_level: string;
  risk_label: string;
  risk_color: string;
  action: string;
  recommendations: string[];
  model_used: string;
  message: string;
}

export interface PlantFutureResponse {
  success: boolean;
  location_label: string | null;
  forecast_3_day: { day: number; risk_score: number; risk_score_pct: number; risk_level: string };
  forecast_7_day: { day: number; risk_score: number; risk_score_pct: number; risk_level: string };
  trend: string;
  model_version: string;
  message: string;
}

// ---------------------------------------------------------------------------
// Users API
// ---------------------------------------------------------------------------

export const usersApi = {
  getAll: () => request<User[]>("/users/"),
  getById: (id: number) => request<User>(`/users/${id}`),
  create: (data: { username: string; email: string; password: string }) =>
    request<User>("/users/", { method: "POST", body: JSON.stringify(data) }),
};

// ---------------------------------------------------------------------------
// Plants API
// ---------------------------------------------------------------------------

export const plantsApi = {
  getAll: () => request<Plant[]>("/plants/"),
  getById: (id: number) => request<Plant>(`/plants/${id}`),
  getByUser: (userId: number) => request<Plant[]>(`/plants/user/${userId}`),
  create: (data: { plant_name: string; user_id: number }) =>
    request<Plant>("/plants/", { method: "POST", body: JSON.stringify(data) }),
};

// ---------------------------------------------------------------------------
// Disease Records API
// ---------------------------------------------------------------------------

export const diseaseRecordsApi = {
  getByPlant: (plantId: number) =>
    request<DiseaseRecord[]>(`/disease-records/plant/${plantId}`),
  create: (data: { plant_id: number; disease_name: string; confidence_score?: number }) =>
    request<DiseaseRecord>("/disease-records/", { method: "POST", body: JSON.stringify(data) }),
};

// ---------------------------------------------------------------------------
// AI Detection API
// ---------------------------------------------------------------------------

export const aiApi = {
  analyze: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return requestFormData<FullAnalysisResult>("/ai/analyze", formData);
  },
  chat: (message: string) =>
    request<ChatResponse>("/ai/chat", { method: "POST", body: JSON.stringify({ message }) }),
};

// ---------------------------------------------------------------------------
// Sprint 3 API
// ---------------------------------------------------------------------------

export const sprint3Api = {
  predictRisk: (data: {
    temperature: number;
    humidity: number;
    rainfall: number;
    wind_speed: number;
    season: string;
    plant_health_status?: string;
    disease_name?: string;
  }) =>
    request<RiskScoreResponse>("/sprint3/predict_risk", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getPlantFuture: (data: { observations: number[][]; location_label?: string }) =>
    request<PlantFutureResponse>("/sprint3/get_plant_future", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getFarmingAdvice: (data: {
    temperature: number;
    humidity: number;
    rainfall: number;
    wind_speed: number;
    season: string;
    plant_health_status: string;
    disease_name?: string;
    crop_type?: string;
  }) =>
    request<FarmingAdviceResponse>("/sprint3/get_farming_advice", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
