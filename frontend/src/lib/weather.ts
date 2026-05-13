export interface CityCoords {
  lat: number;
  lon: number;
}

// Türkiye'nin 81 ilinin yaklaşık koordinatları
export const TURKEY_CITIES: Record<string, CityCoords> = {
  "Adana": { lat: 37.00, lon: 35.32 },
  "Adıyaman": { lat: 37.76, lon: 38.28 },
  "Afyonkarahisar": { lat: 38.76, lon: 30.54 },
  "Ağrı": { lat: 39.72, lon: 43.05 },
  "Aksaray": { lat: 38.37, lon: 34.03 },
  "Amasya": { lat: 40.65, lon: 35.84 },
  "Ankara": { lat: 39.93, lon: 32.85 },
  "Antalya": { lat: 36.91, lon: 30.70 },
  "Ardahan": { lat: 41.11, lon: 42.70 },
  "Artvin": { lat: 41.18, lon: 41.82 },
  "Aydın": { lat: 37.84, lon: 27.85 },
  "Balıkesir": { lat: 39.65, lon: 27.89 },
  "Bartın": { lat: 41.64, lon: 32.34 },
  "Batman": { lat: 37.88, lon: 41.13 },
  "Bayburt": { lat: 40.26, lon: 40.23 },
  "Bilecik": { lat: 40.15, lon: 29.98 },
  "Bingöl": { lat: 38.88, lon: 40.50 },
  "Bitlis": { lat: 38.40, lon: 42.12 },
  "Bolu": { lat: 40.74, lon: 31.61 },
  "Burdur": { lat: 37.72, lon: 30.29 },
  "Bursa": { lat: 40.20, lon: 29.06 },
  "Çanakkale": { lat: 40.16, lon: 26.41 },
  "Çankırı": { lat: 40.60, lon: 33.61 },
  "Çorum": { lat: 40.55, lon: 34.96 },
  "Denizli": { lat: 37.77, lon: 29.09 },
  "Diyarbakır": { lat: 37.92, lon: 40.22 },
  "Düzce": { lat: 40.84, lon: 31.16 },
  "Edirne": { lat: 41.68, lon: 26.56 },
  "Elazığ": { lat: 38.68, lon: 39.22 },
  "Erzincan": { lat: 39.74, lon: 39.49 },
  "Erzurum": { lat: 39.91, lon: 41.27 },
  "Eskişehir": { lat: 39.77, lon: 30.52 },
  "Gaziantep": { lat: 37.06, lon: 37.38 },
  "Giresun": { lat: 40.91, lon: 38.39 },
  "Gümüşhane": { lat: 40.46, lon: 39.48 },
  "Hakkari": { lat: 37.58, lon: 43.74 },
  "Hatay": { lat: 36.40, lon: 36.35 },
  "Iğdır": { lat: 39.92, lon: 44.05 },
  "Isparta": { lat: 37.76, lon: 30.56 },
  "İstanbul": { lat: 41.01, lon: 28.97 },
  "İzmir": { lat: 38.42, lon: 27.14 },
  "Kahramanmaraş": { lat: 37.57, lon: 36.93 },
  "Karabük": { lat: 41.20, lon: 32.62 },
  "Karaman": { lat: 37.18, lon: 33.22 },
  "Kars": { lat: 40.61, lon: 43.10 },
  "Kastamonu": { lat: 41.38, lon: 33.78 },
  "Kayseri": { lat: 38.73, lon: 35.49 },
  "Kilis": { lat: 36.72, lon: 37.12 },
  "Kırıkkale": { lat: 39.85, lon: 33.51 },
  "Kırklareli": { lat: 41.74, lon: 27.22 },
  "Kırşehir": { lat: 39.15, lon: 34.16 },
  "Kocaeli": { lat: 40.85, lon: 29.88 },
  "Konya": { lat: 37.87, lon: 32.49 },
  "Kütahya": { lat: 39.42, lon: 29.99 },
  "Malatya": { lat: 38.35, lon: 38.31 },
  "Manisa": { lat: 38.62, lon: 27.43 },
  "Mardin": { lat: 37.31, lon: 40.74 },
  "Mersin": { lat: 36.81, lon: 34.64 },
  "Muğla": { lat: 37.21, lon: 28.37 },
  "Muş": { lat: 38.73, lon: 41.49 },
  "Nevşehir": { lat: 38.63, lon: 34.71 },
  "Niğde": { lat: 37.97, lon: 34.69 },
  "Ordu": { lat: 40.98, lon: 37.88 },
  "Osmaniye": { lat: 37.07, lon: 36.25 },
  "Rize": { lat: 41.02, lon: 40.52 },
  "Sakarya": { lat: 40.69, lon: 30.43 },
  "Samsun": { lat: 41.29, lon: 36.33 },
  "Siirt": { lat: 37.93, lon: 41.95 },
  "Sinop": { lat: 42.03, lon: 35.15 },
  "Sivas": { lat: 39.75, lon: 37.02 },
  "Şanlıurfa": { lat: 37.16, lon: 38.79 },
  "Şırnak": { lat: 37.52, lon: 42.46 },
  "Tekirdağ": { lat: 40.98, lon: 27.52 },
  "Tokat": { lat: 40.31, lon: 36.55 },
  "Trabzon": { lat: 41.00, lon: 39.72 },
  "Tunceli": { lat: 39.11, lon: 39.55 },
  "Uşak": { lat: 38.68, lon: 29.41 },
  "Van": { lat: 38.49, lon: 43.38 },
  "Yalova": { lat: 40.65, lon: 29.27 },
  "Yozgat": { lat: 39.82, lon: 34.81 },
  "Zonguldak": { lat: 41.45, lon: 31.80 },
};

export const CITY_NAMES = Object.keys(TURKEY_CITIES).sort();

export interface WeatherData {
  temperature: number;
  humidity: number;
  windSpeed: number;
}

export async function fetchWeather(city: string): Promise<WeatherData | null> {
  const coords = TURKEY_CITIES[city];
  if (!coords) return null;

  try {
    const url =
      `https://api.open-meteo.com/v1/forecast` +
      `?latitude=${coords.lat}&longitude=${coords.lon}` +
      `&current=temperature_2m,relative_humidity_2m,wind_speed_10m`;

    const res = await fetch(url);
    if (!res.ok) return null;

    const data = await res.json();
    const cur = data.current;
    return {
      temperature: Math.round(cur.temperature_2m),
      humidity: Math.round(cur.relative_humidity_2m),
      windSpeed: Math.round(cur.wind_speed_10m),
    };
  } catch {
    return null;
  }
}
