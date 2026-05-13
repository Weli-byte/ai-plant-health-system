# =============================================================================
# routes/reports.py
# Analitik dashboard için özet, risk tahmini ve hava tahmini endpoint'leri.
# =============================================================================

import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, Query
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.connection import get_db
from app.models.analysis_record import AnalysisRecord

router = APIRouter(prefix="/api", tags=["Reports"])

_DAYS_TR = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
_MONTHS_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


# =============================================================================
# GET /api/reports/summary
# =============================================================================

@router.get("/reports/summary")
def get_summary(email: str = Query(...), db: Session = Depends(get_db)):
    records = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_email == email)
        .order_by(AnalysisRecord.created_at.desc())
        .all()
    )

    if not records:
        return _demo_summary()

    now = datetime.now(timezone.utc)
    total = len(records)
    healthy = sum(1 for r in records if (r.risk_level or 3) == 1)
    diseased = total - healthy
    week_start = now - timedelta(days=7)
    this_week = sum(1 for r in records if r.created_at and r.created_at.replace(tzinfo=timezone.utc) > week_start)
    health_score = round((healthy / total) * 100) if total > 0 else 0

    # Günlük veri: son 7 gün
    daily_data = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        ds = day.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        de = ds + timedelta(days=1)
        day_recs = [
            r for r in records
            if r.created_at and ds <= r.created_at.replace(tzinfo=timezone.utc) < de
        ]
        h = sum(1 for r in day_recs if (r.risk_level or 3) == 1)
        daily_data.append({
            "date": day.strftime("%Y-%m-%d"),
            "label": _DAYS_TR[day.weekday()],
            "healthy": h,
            "diseased": len(day_recs) - h,
            "total": len(day_recs),
        })

    # Hastalık dağılımı
    disease_counts: Counter = Counter()
    disease_last: dict = {}
    for r in records:
        name = r.disease_name_tr or "Bilinmiyor"
        disease_counts[name] += 1
        created = r.created_at.replace(tzinfo=timezone.utc) if r.created_at else now
        prev = disease_last.get(name)
        if prev is None or created > prev["dt"]:
            disease_last[name] = {"dt": created, "str": created.strftime("%d.%m.%Y")}

    disease_distribution = [
        {"name": name, "count": cnt, "last_date": disease_last[name]["str"]}
        for name, cnt in disease_counts.most_common(7)
    ]

    active_diseases = sum(
        1 for n in disease_counts
        if "sağlıklı" not in n.lower() and "healthy" not in n.lower()
    )
    risk_level = "Düşük" if health_score >= 70 else "Orta" if health_score >= 40 else "Yüksek"

    # Aylık raporlar (son 3 ay)
    monthly_data = _build_monthly(records)

    return {
        "total": total,
        "healthy": healthy,
        "diseased": diseased,
        "this_week": this_week,
        "daily_data": daily_data,
        "disease_distribution": disease_distribution,
        "health_score": health_score,
        "active_diseases": active_diseases,
        "risk_level": risk_level,
        "monthly_data": monthly_data,
        "is_demo": False,
    }


def _build_monthly(records: list) -> list:
    groups: dict = {}
    for r in records:
        if not r.created_at:
            continue
        d = r.created_at
        key = (d.year, d.month)
        if key not in groups:
            groups[key] = {"total": 0, "healthy": 0, "disease_counts": Counter()}
        groups[key]["total"] += 1
        if (r.risk_level or 3) == 1:
            groups[key]["healthy"] += 1
        else:
            groups[key]["disease_counts"][r.disease_name_tr or "Bilinmiyor"] += 1

    result = []
    for (year, month) in sorted(groups.keys(), reverse=True)[:3]:
        g = groups[(year, month)]
        top = g["disease_counts"].most_common(1)
        result.append({
            "year": year,
            "month": month,
            "label": f"{_MONTHS_TR[month - 1]} {year}",
            "total": g["total"],
            "healthy": g["healthy"],
            "health_pct": round(g["healthy"] / g["total"] * 100) if g["total"] else 0,
            "top_disease": top[0][0] if top else "—",
        })
    return result


def _demo_summary() -> dict:
    now = datetime.now(timezone.utc)
    daily: list = []
    day_h = [2, 3, 1, 4, 2, 3, 5]
    day_d = [1, 0, 2, 1, 1, 2, 1]
    for i in range(7):
        day = now - timedelta(days=6 - i)
        daily.append({
            "date": day.strftime("%Y-%m-%d"),
            "label": _DAYS_TR[day.weekday()],
            "healthy": day_h[i],
            "diseased": day_d[i],
            "total": day_h[i] + day_d[i],
        })
    return {
        "total": 24,
        "healthy": 17,
        "diseased": 7,
        "this_week": 8,
        "daily_data": daily,
        "disease_distribution": [
            {"name": "Sağlıklı Bitki", "count": 17, "last_date": "12.05.2026"},
            {"name": "Külleme", "count": 4, "last_date": "10.05.2026"},
            {"name": "Yaprak Yanıklığı", "count": 2, "last_date": "08.05.2026"},
            {"name": "Pas Hastalığı", "count": 1, "last_date": "05.05.2026"},
        ],
        "health_score": 71,
        "active_diseases": 3,
        "risk_level": "Orta",
        "monthly_data": [
            {"year": 2026, "month": 5, "label": "May 2026", "total": 15, "healthy": 11, "health_pct": 73, "top_disease": "Külleme"},
            {"year": 2026, "month": 4, "label": "Nis 2026", "total": 9, "healthy": 6, "health_pct": 67, "top_disease": "Yaprak Yanıklığı"},
        ],
        "is_demo": True,
    }


# =============================================================================
# POST /api/risk-prediction  (OpenAI destekli)
# =============================================================================

class RiskPredictionRequest(BaseModel):
    temp: float
    humidity: float
    rain: float
    wind: float
    soil: str
    crop: str
    stage: str


@router.post("/risk-prediction")
async def predict_risk(req: RiskPredictionRequest):
    if not settings.OPENAI_API_KEY:
        return _mock_risk(req)

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    system_prompt = (
        "Sen deneyimli bir tarım hastalık risk analisti ve epidemiyoloğusun. "
        "Verilen çevre koşullarını analiz edip Türkiye tarım koşullarına özgü hastalık "
        "risklerini bilimsel metodoloji ile hesapla. SADECE JSON döndür, açıklama yazma."
    )
    user_prompt = (
        f"Parametreler: Sıcaklık:{req.temp}°C Nem:{req.humidity}% "
        f"Yağış:{req.rain}mm Rüzgar:{req.wind}km/s Toprak:{req.soil} "
        f"Bitki:{req.crop} Evre:{req.stage}\n\n"
        'JSON:\n{\n'
        '  "overall_risk": "Düşük/Orta/Yüksek/Kritik",\n'
        '  "risk_score": 0-100,\n'
        '  "confidence": 0-100,\n'
        '  "disease_risks": [\n'
        '    {"name": "", "probability": 0-100, "severity": "Düşük/Orta/Yüksek", "reason": "", "prevention": ""}\n'
        '  ],\n'
        '  "immediate_actions": ["", "", ""],\n'
        '  "week_forecast": "",\n'
        '  "optimal_spray_window": {"start_day": 1, "end_day": 3, "reason": ""},\n'
        '  "economic_risk_percent": 0-100,\n'
        '  "economic_risk_tl_per_dekar": 0\n'
        '}'
    )

    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1000,
            temperature=0.3,
        )
        raw = resp.choices[0].message.content or ""
        m = re.search(r"\{[\s\S]+\}", raw)
        return json.loads(m.group(0) if m else raw)
    except Exception:
        return _mock_risk(req)


def _mock_risk(req: RiskPredictionRequest) -> dict:
    score = min(int(req.humidity * 0.45 + req.temp * 0.25 + req.rain * 0.3), 95)
    overall = (
        "Düşük" if score < 30
        else "Orta" if score < 55
        else "Yüksek" if score < 78
        else "Kritik"
    )
    return {
        "overall_risk": overall,
        "risk_score": score,
        "confidence": 74,
        "disease_risks": [
            {
                "name": "Külleme",
                "probability": min(int(req.humidity * 0.75), 90),
                "severity": "Orta",
                "reason": "Yüksek nem ve ılıman sıcaklık külleme gelişimine elverişli koşullar oluşturuyor.",
                "prevention": "Kükürt bazlı fungisit 7 günde bir uygulayın.",
            },
            {
                "name": "Yaprak Yanıklığı",
                "probability": min(int(req.rain * 0.9 + 8), 85),
                "severity": "Yüksek",
                "reason": "Yağış sonrası yaprak ıslaklık süresi Phytophthora sporlanmasını tetikler.",
                "prevention": "Bakır oksiklorür (3 g/L) ile akşam saatlerinde koruyucu uygulama yapın.",
            },
            {
                "name": "Botrytis",
                "probability": min(int(req.humidity * 0.4 + req.rain * 0.3), 60),
                "severity": "Düşük",
                "reason": "Nemli ortam gri küf riskini artırır.",
                "prevention": "Hava sirkülasyonunu artırın, hasat öncesi ilaçlamayı durdurun.",
            },
        ],
        "immediate_actions": [
            f"{'Koruyucu fungisit uygulayın' if score > 50 else 'Standart bakım rutinine devam edin'}",
            "Günlük sabah yaprak ıslaklık kontrolü yapın",
            "Sulama saatini gündüz erken saatlerine alın",
        ],
        "week_forecast": (
            f"Önümüzdeki 7 gün {overall.lower()} risk düzeyinde seyredecektir. "
            f"{'Nem yüksekliği kritik eşiği aşabilir, ilaçlama takvimine uyun.' if req.humidity > 70 else 'Koşullar görece stabil, rutin kontrole devam edin.'}"
        ),
        "optimal_spray_window": {
            "start_day": 2,
            "end_day": 4,
            "reason": "Yağış arası kuru pencerede sabah 07–10 arası rüzgarsız koşullarda uygulayın.",
        },
        "economic_risk_percent": min(score + 5, 95),
        "economic_risk_tl_per_dekar": score * 130,
    }


# =============================================================================
# GET /api/weather/forecast
# =============================================================================

@router.get("/weather/forecast")
async def get_weather_forecast(
    lat: float = Query(...),
    lon: float = Query(...),
):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,precipitation_sum,windspeed_10m_max"
        f"&forecast_days=14&timezone=auto"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
        return {"days": _parse_forecast(data)}
    except Exception:
        return {"days": _mock_forecast()}


def _parse_forecast(data: dict) -> list:
    daily = data.get("daily", {})
    times = daily.get("time", [])
    temps = daily.get("temperature_2m_max", [])
    rains = daily.get("precipitation_sum", [])
    winds = daily.get("windspeed_10m_max", [])

    days = []
    for i, t in enumerate(times):
        dt = datetime.strptime(t, "%Y-%m-%d")
        temp = float(temps[i]) if i < len(temps) else 22.0
        rain = float(rains[i]) if i < len(rains) else 0.0
        wind = float(winds[i]) if i < len(winds) else 10.0

        if rain > 1 or wind > 20 or temp > 35 or temp < 5:
            suitability, suggestion = "unsuitable", "Bekleyin"
        elif rain > 0 or wind > 15 or temp > 28 or temp < 10:
            suitability, suggestion = "caution", "Dikkatli olun"
        else:
            suitability, suggestion = "ideal", "Sabah erken uygulayın"

        days.append({
            "date": t,
            "day_label": f"{dt.day} {_MONTHS_TR[dt.month - 1]}",
            "weekday": _DAYS_TR[dt.weekday()],
            "temp_max": round(temp, 1),
            "rain": round(rain, 1),
            "wind": round(wind, 1),
            "suitability": suitability,
            "suggestion": suggestion,
        })
    return days


def _mock_forecast() -> list:
    now = datetime.now(timezone.utc)
    conditions = [
        (22, 0.0, 8), (25, 0.0, 7), (28, 0.5, 12), (26, 0.0, 9),
        (20, 8.0, 25), (18, 12.0, 30), (22, 2.0, 15), (24, 0.0, 10),
        (27, 0.0, 8), (29, 0.0, 11), (30, 0.0, 9), (26, 1.0, 14),
        (23, 5.0, 18), (21, 0.0, 8),
    ]
    days = []
    for i, (temp, rain, wind) in enumerate(conditions):
        dt = now + timedelta(days=i)
        if rain > 1 or wind > 20 or temp > 35:
            suitability, suggestion = "unsuitable", "Bekleyin"
        elif rain > 0 or wind > 15 or temp > 28:
            suitability, suggestion = "caution", "Dikkatli olun"
        else:
            suitability, suggestion = "ideal", "Sabah erken uygulayın"
        days.append({
            "date": dt.strftime("%Y-%m-%d"),
            "day_label": f"{dt.day} {_MONTHS_TR[dt.month - 1]}",
            "weekday": _DAYS_TR[dt.weekday()],
            "temp_max": float(temp),
            "rain": float(rain),
            "wind": float(wind),
            "suitability": suitability,
            "suggestion": suggestion,
        })
    return days
