// =============================================================================
// AI Plant Health System — Mock Backend Server
//
// Gerçek Python backend yerine çalışan sahte API sunucusu.
// API dokümantasyonundaki tüm endpoint'leri mock data ile döndürür.
//
// Çalıştırmak için:
//   cd mock-server
//   npm install
//   npm run dev
//
// Sunucu: http://localhost:8000
// =============================================================================

const express = require("express");
const cors = require("cors");
const multer = require("multer");

const app = express();
const PORT = 8000;

// Multer — dosya yükleme (belleğe, diske kaydetmeye gerek yok)
const upload = multer({ storage: multer.memoryStorage() });

// Middleware
app.use(cors({ origin: "*" }));
app.use(express.json({ limit: "50mb" }));

// =============================================================================
// MOCK DATA
// =============================================================================

let nextUserId = 4;
let nextPlantId = 5;
let nextRecordId = 6;
let nextAnalysisId = 4;

const users = [
  { id: 1, username: "mehmet_ciftci", email: "mehmet@tarla.com" },
  { id: 2, username: "ayse_bahce", email: "ayse@sera.com" },
  { id: 3, username: "ali_toprak", email: "ali@toprak.com" },
];

const plants = [
  { id: 1, plant_name: "🍅 Domates", user_id: 1, created_at: "2026-03-15T10:00:00Z", plant_type: "Domates", plant_emoji: "🍅", growth_stage: "fruiting", location: "1. Sera", irrigation_method: "drip", irrigation_frequency: "daily", area_size: 2.5, planting_date: "2026-03-01", notes: null },
  { id: 2, plant_name: "🫑 Biber", user_id: 1, created_at: "2026-03-20T08:30:00Z", plant_type: "Biber", plant_emoji: "🫑", growth_stage: "flowering", location: "Açık Alan", irrigation_method: "furrow", irrigation_frequency: "every2days", area_size: 1.0, planting_date: "2026-03-15", notes: null },
  { id: 3, plant_name: "🥒 Salatalık", user_id: 1, created_at: "2026-04-01T14:00:00Z", plant_type: "Salatalık", plant_emoji: "🥒", growth_stage: "vegetative", location: "2. Sera", irrigation_method: "drip", irrigation_frequency: "daily", area_size: 1.5, planting_date: "2026-03-25", notes: null },
  { id: 4, plant_name: "🍓 Çilek", user_id: 2, created_at: "2026-04-10T09:00:00Z", plant_type: "Çilek", plant_emoji: "🍓", growth_stage: "harvest", location: "Bahçe", irrigation_method: "sprinkler", irrigation_frequency: "daily", area_size: 0.5, planting_date: "2026-02-20", notes: null },
];

const diseaseRecords = [
  { id: 1, plant_id: 1, disease_name: "Yaprak Yanıklığı", confidence_score: 0.94, created_at: "2026-05-10T14:30:00Z" },
  { id: 2, plant_id: 1, disease_name: "Külleme", confidence_score: 0.87, created_at: "2026-05-08T11:00:00Z" },
  { id: 3, plant_id: 2, disease_name: "Sağlıklı", confidence_score: 0.98, created_at: "2026-05-09T16:00:00Z" },
  { id: 4, plant_id: 3, disease_name: "Külleme", confidence_score: 0.88, created_at: "2026-05-07T10:15:00Z" },
  { id: 5, plant_id: 4, disease_name: "Sağlıklı", confidence_score: 0.96, created_at: "2026-05-06T12:45:00Z" },
];

const analysisRecords = [
  { id: 1, user_email: "mehmet@tarla.com", disease_name_tr: "Külleme", disease_name_en: "Powdery Mildew", confidence_score: 0.87, risk_level: 3, pathogen_type: "fungal", spread_risk: "high", affected_percentage: 45, enrichment_json: null, created_at: "2026-05-10T14:30:00Z" },
  { id: 2, user_email: "mehmet@tarla.com", disease_name_tr: "Sağlıklı Bitki", disease_name_en: "Healthy", confidence_score: 0.96, risk_level: 1, pathogen_type: "none", spread_risk: "low", affected_percentage: 0, enrichment_json: null, created_at: "2026-05-08T11:00:00Z" },
  { id: 3, user_email: "mehmet@tarla.com", disease_name_tr: "Pas Hastalığı", disease_name_en: "Rust", confidence_score: 0.91, risk_level: 4, pathogen_type: "fungal", spread_risk: "high", affected_percentage: 60, enrichment_json: null, created_at: "2026-05-06T09:15:00Z" },
];

// =============================================================================
// HEALTH CHECK
// =============================================================================

app.get("/", (req, res) => {
  res.json({
    status: "🌱 Mock API is running!",
    project: "AI Plant Health Detection System",
    version: "1.0.0-mock",
    docs: "http://localhost:8000/docs",
    sprint: "Mock Backend",
    ai_models_loaded: true,
    ai_device: "mock",
    message: "Bu bir mock sunucudur. Frontend test için kullanılmaktadır.",
  });
});

// =============================================================================
// 1. USERS
// =============================================================================

// POST /users/ — Yeni kullanıcı oluştur
app.post("/users/", (req, res) => {
  const { username, email, password } = req.body;

  if (!username || !email || !password) {
    return res.status(400).json({ detail: "username, email ve password zorunludur." });
  }
  if (username.length < 3) {
    return res.status(400).json({ detail: "Kullanıcı adı en az 3 karakter olmalı." });
  }
  if (password.length < 8) {
    return res.status(400).json({ detail: "Şifre en az 8 karakter olmalı." });
  }
  if (users.find((u) => u.email === email)) {
    return res.status(400).json({ detail: "Bu email adresi zaten kayıtlı." });
  }
  if (users.find((u) => u.username === username)) {
    return res.status(400).json({ detail: "Bu kullanıcı adı zaten alınmış." });
  }

  const newUser = { id: nextUserId++, username, email };
  users.push(newUser);
  console.log(`✅ Yeni kullanıcı: ${username} (${email})`);
  res.status(201).json(newUser);
});

// GET /users/ — Tüm kullanıcıları listele
app.get("/users/", (req, res) => {
  res.json(users);
});

// GET /users/:id — Belirli kullanıcı
app.get("/users/:id", (req, res) => {
  const user = users.find((u) => u.id === parseInt(req.params.id));
  if (!user) return res.status(404).json({ detail: `ID=${req.params.id} olan kullanıcı bulunamadı.` });
  res.json(user);
});

// =============================================================================
// 2. PLANTS
// =============================================================================

// POST /plants/ — Yeni bitki ekle
app.post("/plants/", (req, res) => {
  const { plant_name, user_id, plant_type, plant_emoji, planting_date, location, growth_stage, irrigation_method, irrigation_frequency, area_size, notes } = req.body;

  if (!plant_name || !user_id) {
    return res.status(400).json({ detail: "plant_name ve user_id zorunludur." });
  }
  if (!users.find((u) => u.id === user_id)) {
    return res.status(404).json({ detail: `ID=${user_id} olan kullanıcı bulunamadı.` });
  }

  const newPlant = {
    id: nextPlantId++,
    plant_name,
    user_id,
    created_at: new Date().toISOString(),
    plant_type: plant_type ?? null,
    plant_emoji: plant_emoji ?? null,
    planting_date: planting_date ?? null,
    location: location ?? null,
    growth_stage: growth_stage ?? null,
    irrigation_method: irrigation_method ?? null,
    irrigation_frequency: irrigation_frequency ?? null,
    area_size: area_size ?? null,
    notes: notes ?? null,
  };
  plants.push(newPlant);
  console.log(`🌿 Yeni bitki: ${plant_name} (user: ${user_id})`);
  res.status(201).json(newPlant);
});

// GET /plants/ — Tüm bitkiler
app.get("/plants/", (req, res) => {
  res.json(plants);
});

// GET /plants/:id — Belirli bitki
app.get("/plants/:id", (req, res) => {
  const plant = plants.find((p) => p.id === parseInt(req.params.id));
  if (!plant) return res.status(404).json({ detail: `ID=${req.params.id} olan bitki bulunamadı.` });
  res.json(plant);
});

// GET /plants/user/:userId — Kullanıcının bitkileri
app.get("/plants/user/:userId", (req, res) => {
  const userId = parseInt(req.params.userId);
  const userPlants = plants.filter((p) => p.user_id === userId);
  res.json(userPlants);
});

// =============================================================================
// 3. DISEASE RECORDS
// =============================================================================

// POST /disease-records/ — Yeni hastalık kaydı
app.post("/disease-records/", (req, res) => {
  const { plant_id, disease_name, confidence_score } = req.body;

  if (!plant_id || !disease_name) {
    return res.status(400).json({ detail: "plant_id ve disease_name zorunludur." });
  }
  if (!plants.find((p) => p.id === plant_id)) {
    return res.status(404).json({ detail: `ID=${plant_id} olan bitki bulunamadı.` });
  }

  const newRecord = {
    id: nextRecordId++,
    plant_id,
    disease_name,
    confidence_score: confidence_score ?? null,
    created_at: new Date().toISOString(),
  };
  diseaseRecords.push(newRecord);
  console.log(`🔬 Yeni hastalık kaydı: ${disease_name} (bitki: ${plant_id})`);
  res.status(201).json(newRecord);
});

// GET /disease-records/plant/:plantId — Bitkinin hastalık geçmişi
app.get("/disease-records/plant/:plantId", (req, res) => {
  const plantId = parseInt(req.params.plantId);
  const plant = plants.find((p) => p.id === plantId);
  if (!plant) return res.status(404).json({ detail: `ID=${plantId} olan bitki bulunamadı.` });

  const records = diseaseRecords
    .filter((r) => r.plant_id === plantId)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  res.json(records);
});

// =============================================================================
// 3b. ANALYSIS RECORDS (Sprint 3+)
// =============================================================================

// POST /analyses/ — Yeni analiz kaydı
app.post("/analyses/", (req, res) => {
  const { user_email, disease_name_tr, disease_name_en, confidence_score, risk_level, pathogen_type, spread_risk, affected_percentage, enrichment_json } = req.body;
  if (!user_email || !disease_name_tr) {
    return res.status(400).json({ detail: "user_email ve disease_name_tr zorunludur." });
  }
  const record = {
    id: nextAnalysisId++,
    user_email,
    disease_name_tr,
    disease_name_en: disease_name_en ?? null,
    confidence_score: confidence_score ?? null,
    risk_level: risk_level ?? null,
    pathogen_type: pathogen_type ?? null,
    spread_risk: spread_risk ?? null,
    affected_percentage: affected_percentage ?? null,
    enrichment_json: enrichment_json ?? null,
    created_at: new Date().toISOString(),
  };
  analysisRecords.push(record);
  console.log(`✅ Analiz kaydedildi: ${disease_name_tr} (${user_email})`);
  res.status(201).json(record);
});

// GET /analyses/ — Kullanıcının analizleri (?email=...)
app.get("/analyses/", (req, res) => {
  const email = req.query.email;
  if (!email) return res.status(400).json({ detail: "email query parametresi zorunludur." });
  const records = analysisRecords
    .filter((r) => r.user_email === email)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  res.json(records);
});

// =============================================================================
// 4. AI DETECTION (Sprint 2)
// =============================================================================

// POST /ai/detect_leaf — Mock yaprak tespiti (multipart file)
app.post("/ai/detect_leaf", upload.single("file"), (req, res) => {
  console.log("🍃 Yaprak tespiti isteği alındı");
  res.json({
    success: true,
    leaf_detected: true,
    bounding_box: { x1: 42, y1: 58, x2: 310, y2: 290 },
    confidence: 0.9231,
    cropped_leaf_base64: "MOCK_BASE64_CROPPED_LEAF_DATA",
    original_width: 640,
    original_height: 480,
    message: "Yaprak başarıyla tespit edildi.",
  });
});

// POST /ai/classify_disease — Mock hastalık sınıflandırma
app.post("/ai/classify_disease", (req, res) => {
  console.log("🔬 Hastalık sınıflandırma isteği alındı");
  res.json({
    success: true,
    predicted_class: "Powdery Mildew",
    predicted_class_index: 1,
    confidence: 0.8743,
    all_scores: {
      Healthy: 0.0412,
      "Powdery Mildew": 0.8743,
      "Leaf Blight": 0.0521,
      Rust: 0.0324,
    },
    message: "'Powdery Mildew' hastalığı %87.4 güven ile tespit edildi.",
  });
});

// POST /ai/explain_prediction — Mock Grad-CAM
app.post("/ai/explain_prediction", (req, res) => {
  console.log("🌡️ Grad-CAM isteği alındı");
  res.json({
    success: true,
    heatmap_base64: "MOCK_HEATMAP_BASE64",
    overlay_base64: "MOCK_OVERLAY_BASE64",
    target_class: "Powdery Mildew",
    target_class_index: 1,
    message: "'Powdery Mildew' sınıfı için Grad-CAM oluşturuldu.",
  });
});

// POST /ai/analyze — Mock Tam Pipeline (YOLO → EfficientNet → Grad-CAM) (multipart file)
app.post("/ai/analyze", upload.single("file"), (req, res) => {
  console.log("🚀 Tam AI analiz pipeline isteği alındı");

  // Küçük bir gecikme ekleyelim — gerçekçi olsun
  setTimeout(() => {
    res.json({
      success: true,
      leaf_detection: {
        success: true,
        leaf_detected: true,
        bounding_box: { x1: 85, y1: 120, x2: 420, y2: 380 },
        confidence: 0.9456,
        cropped_leaf_base64: "MOCK_CROPPED_BASE64",
        original_width: 640,
        original_height: 480,
        message: "Yaprak tespit edildi.",
      },
      disease_classification: {
        success: true,
        predicted_class: "Powdery Mildew",
        predicted_class_index: 1,
        confidence: 0.9120,
        all_scores: {
          Healthy: 0.0280,
          "Powdery Mildew": 0.9120,
          "Leaf Blight": 0.0350,
          Rust: 0.0250,
        },
        message: "'Powdery Mildew' hastalığı %91.2 güven ile tespit edildi.",
      },
      gradcam: {
        success: true,
        heatmap_base64: "MOCK_HEATMAP_BASE64",
        overlay_base64: "MOCK_OVERLAY_BASE64",
        target_class: "Powdery Mildew",
        target_class_index: 1,
        message: "'Powdery Mildew' için Grad-CAM oluşturuldu.",
      },
      message: "Tam AI analizi tamamlandı.",
    });
  }, 1500);
});

// POST /ai/chat — Mock Chatbot
app.post("/ai/chat", (req, res) => {
  const msg = (req.body.message || "").toLowerCase();
  console.log(`💬 Chat mesajı: "${req.body.message}"`);

  let response;
  if (msg.includes("külleme") || msg.includes("mildew") || msg.includes("beyaz")) {
    response =
      "Külleme (Powdery Mildew) mantar kaynaklı bir hastalıktır. Kükürt bazlı ilaçlar etkilidir ancak uygulama sırasında hava sıcaklığının 30 derecenin altında olmasına dikkat edin. Akşam saatlerini tercih edin.";
  } else if (msg.includes("su") || msg.includes("sulama") || msg.includes("nem")) {
    response =
      "Bitki sulamasında temel kural toprağın üst yüzeyinin kurumuş olmasıdır. Mantar hastalıklarını önlemek için yapraklara su değdirmemeye ve sabahın erken saatlerinde sulama yapmaya özen gösterin.";
  } else if (msg.includes("gübre") || msg.includes("besin") || msg.includes("npk")) {
    response =
      "Bitkinizin gelişim evresine göre gübreleme yapmalısınız. Yaprak gelişimi için Azot (N), çiçeklenme için Fosfor (P) ağırlıklı organik gübreler tavsiye edilir. Hastalıklı bitkiye ağır gübreleme yapmayın.";
  } else if (msg.includes("pas") || msg.includes("rust") || msg.includes("turuncu")) {
    response =
      "Pas hastalığı genellikle yüksek nemden kaynaklanır. Bakır içerikli fungisitler (Bordo bulamacı gibi) bu hastalıkta oldukça etkilidir. Hastalıklı yaprakları derhal imha edin.";
  } else if (msg.includes("merhaba") || msg.includes("selam")) {
    response = "Merhaba! Ben Agro AI. Bitkileriniz hakkında her türlü soruyu bana sorabilirsiniz. Size nasıl yardımcı olabilirim?";
  } else if (msg.includes("hastalık") || msg.includes("neden")) {
    response =
      "Yaprak yanıklığı genellikle nemli ve serin havalarda Phytophthora mantarı ile ortaya çıkar. Yağmurdan sonra suyun yapraklarda uzun süre kalması en büyük tetikleyicidir. Hava akımını artırmak ve sabah sulamak riski azaltır.";
  } else if (msg.includes("ilaç") || msg.includes("ilac")) {
    response =
      "Erken evre yaprak yanıklığı için bakır oksiklorür (3-5 g/L) etkili bir koruyucu seçenektir. 7 günde bir, akşamüstü uygulayın. Yayılma görürseniz mancozeb ile değiştirme yapılabilir.";
  } else {
    response =
      "Bu konuda size en doğru bilgiyi verebilmem için bitkinizin bir fotoğrafını 'Tahlil' kısmından yüklemenizi öneririm. Genel bir tavsiye olarak; bitkinizin havalandırmasını artırmak ve nem dengesini korumak çoğu hastalığı önleyecektir.";
  }

  res.json({
    success: true,
    response,
    message: "AI asistanı yanıtı başarıyla oluşturdu.",
  });
});

// =============================================================================
// 5. SPRINT 3 — Tarım Karar Destek
// =============================================================================

// POST /sprint3/predict_risk — Mock risk skoru
app.post("/sprint3/predict_risk", (req, res) => {
  const { temperature = 24, humidity = 70, season = "spring" } = req.body;
  console.log(`📊 Risk tahmin isteği: ${temperature}°C, %${humidity} nem, ${season}`);

  // Basit kural tabanlı mock risk hesaplama
  let riskScore = 20;
  if (humidity > 75) riskScore += 25;
  if (temperature > 20 && temperature < 30 && humidity > 60) riskScore += 15;
  if (season === "spring" || season === "autumn") riskScore += 10;
  riskScore = Math.min(riskScore, 95);

  const riskLevel = riskScore < 25 ? "Low" : riskScore < 50 ? "Medium" : riskScore < 75 ? "High" : "Critical";
  const riskColor = riskScore < 25 ? "#22c55e" : riskScore < 50 ? "#eab308" : riskScore < 75 ? "#f97316" : "#ef4444";

  res.json({
    success: true,
    risk_score: riskScore,
    risk_level: riskLevel,
    risk_label: `${riskLevel} Risk`,
    risk_color: riskColor,
    action: riskScore > 50
      ? "Bitkileri günlük kontrol edin. Koruyucu fungisit uygulamayı düşünün."
      : "Standart bakım rutinine devam edin.",
    recommendations: [
      humidity > 75 ? `🌫️ Nem yüksek (%${humidity}). Hava sirkülasyonunu artırın.` : `✅ Nem seviyesi uygun (%${humidity}).`,
      `🌡️ Sıcaklık ${temperature}°C — ${temperature > 28 ? "sıcak stres riski var" : "uygun aralıkta"}.`,
      `🍂 Mevsim: ${season}. ${season === "spring" ? "Kükürt bazlı koruyucu tedaviye başlayın." : "Mevsime uygun bakım önerilir."}`,
    ],
    model_used: "rule_based",
    message: "Hastalık risk skoru başarıyla hesaplandı.",
  });
});

// POST /sprint3/get_plant_future — Mock digital twin
app.post("/sprint3/get_plant_future", (req, res) => {
  console.log("🔮 Dijital ikiz tahmin isteği alındı");
  res.json({
    success: true,
    location_label: req.body.location_label || "Tarla-A",
    forecast_3_day: { day: 3, risk_score: 0.45, risk_score_pct: 45.0, risk_level: "Medium" },
    forecast_7_day: { day: 7, risk_score: 0.72, risk_score_pct: 72.0, risk_level: "High" },
    trend: "increasing",
    model_version: "1.0.0-mock",
    message: "Dijital ikiz simülasyonu başarıyla tamamlandı.",
  });
});

// POST /sprint3/get_farming_advice — Mock tarım danışma
app.post("/sprint3/get_farming_advice", (req, res) => {
  const { humidity = 70, season = "spring", disease_name } = req.body;
  console.log(`🌾 Tarım danışma isteği: %${humidity} nem, ${season}, hastalık: ${disease_name || "yok"}`);

  const pesticides = disease_name
    ? [
        {
          disease: disease_name,
          product_type: "fungicide",
          active_ingredient: "sulfur",
          product_name: "Thiovit Jet",
          application_notes: "7-10 günde bir, sabah erken saatlerde uygulayın. 30°C üzeri sıcaklıkta uygulamayın.",
        },
        {
          disease: disease_name,
          product_type: "fungicide",
          active_ingredient: "copper hydroxide",
          product_name: "Kocide 2000",
          application_notes: "10-14 günde bir, akşam saatlerinde uygulayın.",
        },
      ]
    : [];

  res.json({
    success: true,
    risk_level: humidity > 75 ? "High" : "Medium",
    farming_advice: [
      humidity > 75 ? `🌫️ Nem %${humidity} — bitkilerin arasındaki hava sirkülasyonunu artırın.` : `✅ Nem seviyesi kabul edilebilir (%${humidity}).`,
      disease_name ? `⚠️ ${disease_name} risk altında. Kükürt bazlı fungisit uygulayın.` : "✅ Aktif hastalık bildirimi yok.",
      `🍂 Mevsim: ${season}. ${season === "spring" ? "İlkbahar koruyucu ilaçlama dönemidir." : "Mevsime uygun bakım yapın."}`,
    ],
    pesticide_recommendations: pesticides,
    irrigation_advice: "Sabah erken sulayın; akşam sulamaktan kaçının. Damla sulama tercih edin.",
    general_notes: humidity > 75
      ? "Yüksek nem mantar hastalıkları için elverişli ortam oluşturuyor. Dikkatli olun."
      : "Koşullar genel olarak uygun. Rutin bakıma devam edin.",
    message: "Tarım danışma raporu başarıyla hazırlandı.",
  });
});

// =============================================================================
// 6. SPRINT 4 — v2 Endpoints
// =============================================================================

// POST /api/v2/predict_risk — Mock XGBoost v2
app.post("/api/v2/predict_risk", (req, res) => {
  const { temperature = 24, humidity = 70 } = req.body;
  console.log(`📊 Risk V2 isteği: ${temperature}°C, %${humidity}`);

  const riskScore = Math.min(Math.round((humidity * 0.6 + temperature * 0.4) * 0.8), 95);
  const riskLevel = riskScore < 33 ? "low" : riskScore < 66 ? "medium" : "high";

  res.json({
    success: true,
    data: {
      risk_score: riskScore,
      risk_level: riskLevel,
      model_version: "2.1.0-mock",
      metrics: { mae: 4.2, rmse: 5.8 },
    },
    message: riskLevel === "low"
      ? "Low risk — conditions are favourable, continue standard care."
      : riskLevel === "medium"
      ? "Medium risk — monitor environmental parameters closely."
      : "High risk — take protective action (ventilation, irrigation, treatment).",
  });
});

// POST /api/v2/predict_future — Mock Digital Twin v2
app.post("/api/v2/predict_future", (req, res) => {
  console.log("🔮 Digital Twin V2 isteği alındı");
  res.json({
    success: true,
    data: {
      horizons_days: [1, 2, 3, 4, 5, 6, 7],
      risk_scores: [0.32, 0.38, 0.45, 0.52, 0.58, 0.63, 0.71],
      risk_levels: ["low", "medium", "medium", "medium", "medium", "high", "high"],
      model_version: "lstm-1.2.0-mock",
    },
    message: "Future risk forecast completed successfully.",
  });
});

// POST /api/v2/detect_leaf — Mock v2 leaf detection (multipart file)
app.post("/api/v2/detect_leaf", upload.single("file"), (req, res) => {
  console.log("🍃 Yaprak tespiti V2 isteği alındı");
  res.json({
    success: true,
    boxes: [
      [120.5, 200.1, 450.2, 600.8],
      [50.0, 80.3, 200.7, 250.4],
    ],
    scores: [0.94, 0.78],
    classes: ["leaf", "leaf"],
    count: 2,
    message: "Detection completed successfully.",
  });
});

// POST /api/v2/multimodal_predict — Mock multimodal
app.post("/api/v2/multimodal_predict", (req, res) => {
  console.log("🧠 Multimodal tahmin isteği alındı");
  res.json({
    success: true,
    data: {
      predicted_class: "Powdery Mildew",
      confidence: 0.89,
      risk_score: 67.5,
      risk_level: "high",
    },
    message: "Multimodal prediction completed successfully.",
  });
});

// =============================================================================
// 7. REPORTS & ANALYTICS
// =============================================================================

// GET /api/reports/summary?email= — Dashboard özet
app.get("/api/reports/summary", (req, res) => {
  const email = req.query.email || "";
  console.log(`📊 Rapor özeti isteği: ${email}`);

  const userRecords = analysisRecords.filter((r) => r.user_email === email);
  const isDemo = userRecords.length === 0;

  const now = new Date();
  const days = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];
  const months = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];

  const buildDailyData = (records) => {
    const daily = [];
    for (let i = 6; i >= 0; i--) {
      const day = new Date(now);
      day.setDate(now.getDate() - i);
      const dayStr = day.toISOString().split("T")[0];
      const dayRecs = records.filter((r) => r.created_at && r.created_at.startsWith(dayStr));
      const h = dayRecs.filter((r) => (r.risk_level || 3) === 1).length;
      daily.push({
        date: dayStr,
        label: days[(day.getDay() + 6) % 7],
        healthy: h,
        diseased: dayRecs.length - h,
        total: dayRecs.length,
      });
    }
    return daily;
  };

  if (isDemo) {
    const demoDaily = [];
    const dh = [2,3,1,4,2,3,5], dd = [1,0,2,1,1,2,1];
    for (let i = 0; i < 7; i++) {
      const day = new Date(now); day.setDate(now.getDate() - (6 - i));
      demoDaily.push({ date: day.toISOString().split("T")[0], label: days[(day.getDay()+6)%7], healthy: dh[i], diseased: dd[i], total: dh[i]+dd[i] });
    }
    return res.json({
      total: 24, healthy: 17, diseased: 7, this_week: 8,
      daily_data: demoDaily,
      disease_distribution: [
        { name: "Sağlıklı Bitki", count: 17, last_date: "12.05.2026" },
        { name: "Külleme", count: 4, last_date: "10.05.2026" },
        { name: "Yaprak Yanıklığı", count: 2, last_date: "08.05.2026" },
        { name: "Pas Hastalığı", count: 1, last_date: "05.05.2026" },
      ],
      health_score: 71, active_diseases: 3, risk_level: "Orta",
      monthly_data: [
        { year: 2026, month: 5, label: "May 2026", total: 15, healthy: 11, health_pct: 73, top_disease: "Külleme" },
        { year: 2026, month: 4, label: "Nis 2026", total: 9, healthy: 6, health_pct: 67, top_disease: "Yaprak Yanıklığı" },
      ],
      is_demo: true,
    });
  }

  const total = userRecords.length;
  const healthy = userRecords.filter((r) => (r.risk_level || 3) === 1).length;
  const weekAgo = new Date(now); weekAgo.setDate(now.getDate() - 7);
  const thisWeek = userRecords.filter((r) => new Date(r.created_at) > weekAgo).length;
  const healthScore = Math.round((healthy / total) * 100);
  const riskLevel = healthScore >= 70 ? "Düşük" : healthScore >= 40 ? "Orta" : "Yüksek";

  const diseaseCounts = {};
  userRecords.forEach((r) => {
    const n = r.disease_name_tr || "Bilinmiyor";
    diseaseCounts[n] = (diseaseCounts[n] || 0) + 1;
  });
  const distribution = Object.entries(diseaseCounts)
    .sort((a, b) => b[1] - a[1]).slice(0, 7)
    .map(([name, count]) => ({ name, count, last_date: new Date().toLocaleDateString("tr-TR") }));
  const activeDiseases = Object.keys(diseaseCounts).filter((n) => !n.toLowerCase().includes("sağlıklı") && !n.toLowerCase().includes("healthy")).length;

  res.json({
    total, healthy, diseased: total - healthy, this_week: thisWeek,
    daily_data: buildDailyData(userRecords),
    disease_distribution: distribution,
    health_score: healthScore, active_diseases: activeDiseases, risk_level: riskLevel,
    monthly_data: [],
    is_demo: false,
  });
});

// POST /api/risk-prediction — Kural tabanlı risk tahmini (mock)
app.post("/api/risk-prediction", (req, res) => {
  const { temp = 22, humidity = 65, rain = 5, wind = 12, soil = "Killi", crop = "Domates", stage = "Vejetatif" } = req.body;
  console.log(`🌡️ Risk tahmini: ${temp}°C, %${humidity} nem, ${crop}`);

  const score = Math.min(Math.round(humidity * 0.45 + temp * 0.25 + rain * 0.3), 95);
  const overall = score < 30 ? "Düşük" : score < 55 ? "Orta" : score < 78 ? "Yüksek" : "Kritik";

  setTimeout(() => {
    res.json({
      overall_risk: overall, risk_score: score, confidence: 74,
      disease_risks: [
        { name: "Külleme", probability: Math.min(Math.round(humidity * 0.75), 90), severity: "Orta",
          reason: "Yüksek nem ve ılıman sıcaklık külleme gelişimine elverişli koşullar oluşturuyor.",
          prevention: "Kükürt bazlı fungisit 7 günde bir uygulayın." },
        { name: "Yaprak Yanıklığı", probability: Math.min(Math.round(rain * 0.9 + 8), 85), severity: "Yüksek",
          reason: "Yağış sonrası yaprak ıslaklık süresi Phytophthora sporlanmasını tetikler.",
          prevention: "Bakır oksiklorür (3 g/L) ile akşam saatlerinde koruyucu uygulama yapın." },
        { name: "Botrytis", probability: Math.min(Math.round(humidity * 0.4 + rain * 0.3), 60), severity: "Düşük",
          reason: "Nemli ortam gri küf riskini artırır.",
          prevention: "Hava sirkülasyonunu artırın, hasat öncesi ilaçlamayı durdurun." },
      ],
      immediate_actions: [
        score > 50 ? "Koruyucu fungisit uygulayın" : "Standart bakım rutinine devam edin",
        "Günlük sabah yaprak ıslaklık kontrolü yapın",
        "Sulama saatini gündüz erken saatlerine alın",
      ],
      week_forecast: `Önümüzdeki 7 gün ${overall.toLowerCase()} risk düzeyinde seyredecektir. ${humidity > 70 ? "Nem yüksekliği kritik eşiği aşabilir, ilaçlama takvimine uyun." : "Koşullar görece stabil, rutin kontrole devam edin."}`,
      optimal_spray_window: { start_day: 2, end_day: 4, reason: "Yağış arası kuru pencerede sabah 07–10 arası rüzgarsız koşullarda uygulayın." },
      economic_risk_percent: Math.min(score + 5, 95),
      economic_risk_tl_per_dekar: score * 130,
    });
  }, 1200);
});

// GET /api/weather/forecast?lat=&lon= — Mock 14 günlük hava tahmini
app.get("/api/weather/forecast", (req, res) => {
  const { lat = 39.0, lon = 35.0 } = req.query;
  console.log(`☀️ Hava tahmini isteği: lat=${lat}, lon=${lon}`);

  const now = new Date();
  const days = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];
  const months = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];
  const conditions = [
    [22, 0, 8], [25, 0, 7], [28, 0.5, 12], [26, 0, 9],
    [20, 8, 25], [18, 12, 30], [22, 2, 15], [24, 0, 10],
    [27, 0, 8], [29, 0, 11], [30, 0, 9], [26, 1, 14],
    [23, 5, 18], [21, 0, 8],
  ];

  const result = conditions.map(([temp, rain, wind], i) => {
    const dt = new Date(now); dt.setDate(now.getDate() + i);
    const suitability = (rain > 1 || wind > 20 || temp > 35) ? "unsuitable"
      : (rain > 0 || wind > 15 || temp > 28) ? "caution" : "ideal";
    const suggestion = suitability === "unsuitable" ? "Bekleyin"
      : suitability === "caution" ? "Dikkatli olun" : "Sabah erken uygulayın";
    return {
      date: dt.toISOString().split("T")[0],
      day_label: `${dt.getDate()} ${months[dt.getMonth()]}`,
      weekday: days[(dt.getDay() + 6) % 7],
      temp_max: temp, rain, wind, suitability, suggestion,
    };
  });
  res.json({ days: result });
});

// =============================================================================
// START SERVER
// =============================================================================

app.listen(PORT, () => {
  console.log("");
  console.log("=".repeat(60));
  console.log("🌱 AI Plant Health — Mock Backend Server");
  console.log("=".repeat(60));
  console.log(`   URL:      http://localhost:${PORT}`);
  console.log(`   Docs:     http://localhost:${PORT}/docs (yok, mock)`);
  console.log("");
  console.log("   Aktif Endpoint'ler:");
  console.log("   ├── GET  /                        (Health Check)");
  console.log("   ├── POST /users/                   (Kayıt)");
  console.log("   ├── GET  /users/                   (Listele)");
  console.log("   ├── GET  /users/:id                (Detay)");
  console.log("   ├── POST /plants/                  (Bitki Ekle)");
  console.log("   ├── GET  /plants/                  (Tüm Bitkiler)");
  console.log("   ├── GET  /plants/:id               (Bitki Detay)");
  console.log("   ├── GET  /plants/user/:userId      (Kullanıcı Bitkileri)");
  console.log("   ├── POST /disease-records/          (Hastalık Kaydı)");
  console.log("   ├── GET  /disease-records/plant/:id (Geçmiş)");
  console.log("   ├── POST /ai/detect_leaf            (Yaprak Tespiti)");
  console.log("   ├── POST /ai/classify_disease       (Hastalık Sınıfla)");
  console.log("   ├── POST /ai/explain_prediction     (Grad-CAM)");
  console.log("   ├── POST /ai/analyze                (Tam Pipeline)");
  console.log("   ├── POST /ai/chat                   (Chatbot)");
  console.log("   ├── POST /sprint3/predict_risk      (Risk Skoru)");
  console.log("   ├── POST /sprint3/get_plant_future  (Digital Twin)");
  console.log("   ├── POST /sprint3/get_farming_advice(Tarım Danışma)");
  console.log("   ├── POST /api/v2/predict_risk       (Risk V2)");
  console.log("   ├── POST /api/v2/predict_future     (Digital Twin V2)");
  console.log("   ├── POST /api/v2/detect_leaf        (Yaprak V2)");
  console.log("   └── POST /api/v2/multimodal_predict (Multimodal)");
  console.log("");
  console.log("=".repeat(60));
  console.log("   ✅ Sunucu hazır. Frontend'i bağlayabilirsiniz.");
  console.log("=".repeat(60));
  console.log("");
});
