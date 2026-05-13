import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Leaf, ChevronRight, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { getUser, saveProfile } from "@/lib/auth";
import { userProfileApi } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CITY_NAMES } from "@/lib/weather";

const CROPS = [
  "Buğday", "Mısır", "Domates", "Biber", "Patlıcan", "Patates",
  "Kayısı", "Üzüm", "Zeytin", "Elma", "Armut", "Şeftali",
  "Kiraz", "Çilek", "Ayçiçeği", "Pamuk", "Nohut", "Fasulye",
  "Mercimek", "Fıstık",
];

type Errors = Record<string, string>;

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
      {children}
    </label>
  );
}

function FieldError({ msg }: { msg?: string }) {
  if (!msg) return null;
  return <p className="mt-1 text-[11px] text-destructive">{msg}</p>;
}

export default function ProfileSetup() {
  const navigate = useNavigate();
  const user = getUser();

  const [fullName, setFullName] = useState(user?.name ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [city, setCity] = useState(user?.city ?? "");
  const [district, setDistrict] = useState(user?.district ?? "");
  const [fieldSize, setFieldSize] = useState(user?.fieldSize ? String(user.fieldSize) : "");
  const [crops, setCrops] = useState<string[]>(user?.crops ?? []);
  const [errors, setErrors] = useState<Errors>({});
  const [saving, setSaving] = useState(false);

  const clear = (field: string) =>
    setErrors((prev) => ({ ...prev, [field]: "" }));

  const toggleCrop = (crop: string) => {
    setCrops((prev) =>
      prev.includes(crop) ? prev.filter((c) => c !== crop) : [...prev, crop]
    );
    clear("crops");
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const errs: Errors = {};
    if (!fullName.trim()) errs.fullName = "Ad Soyad gerekli.";
    if (!phone.trim()) errs.phone = "Telefon numarası gerekli.";
    if (!city) errs.city = "İl seçimi zorunludur.";
    if (!fieldSize || isNaN(Number(fieldSize)) || Number(fieldSize) <= 0)
      errs.fieldSize = "Geçerli bir tarla büyüklüğü girin.";
    if (crops.length === 0) errs.crops = "En az bir ürün seçin.";
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }

    setSaving(true);
    try {
      const profileData = {
        fullName: fullName.trim(),
        phone: phone.trim(),
        city,
        district: district.trim(),
        fieldSize: Number(fieldSize),
        crops,
      };

      // localStorage'a kaydet
      saveProfile({
        name: fullName.trim(),
        phone: phone.trim(),
        city,
        district: district.trim(),
        fieldSize: Number(fieldSize),
        crops,
        profileComplete: true,
      });

      // Backend'e kaydet (best-effort — başarısız olsa bile devam et)
      if (user?.email) {
        try {
          await userProfileApi.upsert({
            email: user.email,
            full_name: profileData.fullName,
            phone: profileData.phone,
            city: profileData.city,
            district: profileData.district || undefined,
            field_size: profileData.fieldSize,
            crops: profileData.crops,
          });
        } catch {
          // Backend çalışmıyor olabilir, sadece localStorage yeterli
          console.warn("Backend profil kaydı başarısız, localStorage'a kaydedildi.");
        }
      }

      navigate("/", { replace: true });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex min-h-dvh flex-col bg-earth-gradient">
      <div className="flex flex-1 flex-col px-5 py-8 overflow-y-auto no-scrollbar">
        {/* Başlık */}
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-3xl bg-leaf-gradient shadow-soft">
            <Leaf className="h-7 w-7 text-primary-foreground" />
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">
            Profilinizi Tamamlayın
          </h1>
          <p className="mt-1 text-xs text-muted-foreground">
            Kişiselleştirilmiş öneriler için birkaç bilgi verin.
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-5">
          {/* Kişisel Bilgiler */}
          <div className="rounded-3xl bg-card/80 p-5 shadow-card backdrop-blur space-y-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Kişisel Bilgiler
            </p>

            <div>
              <FieldLabel>Ad Soyad</FieldLabel>
              <Input
                type="text"
                value={fullName}
                onChange={(e) => { setFullName(e.target.value); clear("fullName"); }}
                placeholder="Ahmet Yılmaz"
                className={cn(
                  "h-12 rounded-2xl border-border/60 bg-background",
                  errors.fullName && "border-destructive"
                )}
              />
              <FieldError msg={errors.fullName} />
            </div>

            <div>
              <FieldLabel>Telefon Numarası</FieldLabel>
              <Input
                type="tel"
                value={phone}
                onChange={(e) => { setPhone(e.target.value); clear("phone"); }}
                placeholder="05XX XXX XX XX"
                className={cn(
                  "h-12 rounded-2xl border-border/60 bg-background",
                  errors.phone && "border-destructive"
                )}
              />
              <FieldError msg={errors.phone} />
            </div>
          </div>

          {/* Konum */}
          <div className="rounded-3xl bg-card/80 p-5 shadow-card backdrop-blur space-y-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Konum
            </p>

            <div>
              <FieldLabel>İl</FieldLabel>
              <select
                value={city}
                onChange={(e) => { setCity(e.target.value); clear("city"); }}
                className={cn(
                  "h-12 w-full rounded-2xl border border-border/60 bg-background px-3 text-sm text-foreground",
                  "focus:outline-none focus:ring-2 focus:ring-ring",
                  errors.city && "border-destructive"
                )}
              >
                <option value="">İl seçin...</option>
                {CITY_NAMES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              <FieldError msg={errors.city} />
            </div>

            <div>
              <FieldLabel>İlçe (opsiyonel)</FieldLabel>
              <Input
                type="text"
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                placeholder="Merkez"
                className="h-12 rounded-2xl border-border/60 bg-background"
              />
            </div>
          </div>

          {/* Tarla Bilgileri */}
          <div className="rounded-3xl bg-card/80 p-5 shadow-card backdrop-blur space-y-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Tarla Bilgileri
            </p>

            <div>
              <FieldLabel>Tarla Büyüklüğü (dönüm)</FieldLabel>
              <Input
                type="number"
                value={fieldSize}
                onChange={(e) => { setFieldSize(e.target.value); clear("fieldSize"); }}
                placeholder="50"
                min="0.1"
                step="0.1"
                className={cn(
                  "h-12 rounded-2xl border-border/60 bg-background",
                  errors.fieldSize && "border-destructive"
                )}
              />
              <FieldError msg={errors.fieldSize} />
            </div>

            <div>
              <FieldLabel>Yetiştirdiğiniz Ürünler</FieldLabel>
              <div className="mt-2 flex flex-wrap gap-2">
                {CROPS.map((crop) => {
                  const selected = crops.includes(crop);
                  return (
                    <button
                      key={crop}
                      type="button"
                      onClick={() => toggleCrop(crop)}
                      className={cn(
                        "rounded-full px-3 py-1.5 text-xs font-medium transition",
                        selected
                          ? "bg-leaf-gradient text-primary-foreground shadow-soft"
                          : "border border-border/60 bg-background text-muted-foreground hover:bg-accent/40"
                      )}
                    >
                      {crop}
                    </button>
                  );
                })}
              </div>
              <FieldError msg={errors.crops} />
            </div>
          </div>

          <Button
            type="submit"
            disabled={saving}
            className="h-12 w-full rounded-2xl bg-leaf-gradient text-base font-semibold shadow-soft"
          >
            {saving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ChevronRight className="mr-2 h-4 w-4" />
            )}
            {saving ? "Kaydediliyor..." : "Dashboard'a Git"}
          </Button>
        </form>

        <p className="mt-6 text-center text-[11px] text-muted-foreground">
          AI Plant Health System · Doğa dostu tarım için
        </p>
      </div>
    </div>
  );
}
