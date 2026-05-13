import { useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Camera, UploadCloud, Loader2, X, Zap, SwitchCamera, AlertTriangle, LockKeyhole } from "lucide-react";
import { Button } from "@/components/ui/button";
import { aiApi } from "@/services/api";

type Mode = "idle" | "camera" | "preview";

export default function CameraAnalysis() {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<Mode>("idle");
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<"environment" | "user">("environment");

  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [capturedFile, setCapturedFile] = useState<File | null>(null);

  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Kamera başlat (yalnızca kullanıcı istediğinde)
  // ---------------------------------------------------------------------------
  const startCamera = useCallback(async (facing: "environment" | "user" = facingMode) => {
    if (!window.isSecureContext) {
      setCameraError("https");
      setMode("camera");
      return;
    }

    setCameraError(null);
    setCameraReady(false);
    setMode("camera");

    // Önceki stream'i kapat
    stream?.getTracks().forEach((t) => t.stop());
    setStream(null);

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: facing }, width: { ideal: 1080 }, height: { ideal: 1080 } },
        audio: false,
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        videoRef.current.onloadedmetadata = () => setCameraReady(true);
      }
    } catch (err: unknown) {
      const error = err as { name?: string };
      if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
        setCameraError("permission");
      } else if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
        setCameraError("notfound");
      } else {
        setCameraError("generic");
      }
    }
  }, [facingMode, stream]);

  const stopCamera = useCallback(() => {
    stream?.getTracks().forEach((t) => t.stop());
    setStream(null);
    setCameraReady(false);
    setCameraError(null);
    setMode("idle");
  }, [stream]);

  // ---------------------------------------------------------------------------
  // Kamera geçişi
  // ---------------------------------------------------------------------------
  const toggleCamera = () => {
    const next = facingMode === "environment" ? "user" : "environment";
    setFacingMode(next);
    startCamera(next);
  };

  // ---------------------------------------------------------------------------
  // Fotoğraf çek
  // ---------------------------------------------------------------------------
  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const size = Math.min(video.videoWidth, video.videoHeight);
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const sx = (video.videoWidth - size) / 2;
    const sy = (video.videoHeight - size) / 2;
    ctx.drawImage(video, sx, sy, size, size, 0, 0, size, size);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const file = new File([blob], "captured_leaf.jpg", { type: "image/jpeg" });
        setCapturedFile(file);
        setCapturedImage(canvas.toDataURL("image/jpeg", 0.92));
        stream?.getTracks().forEach((t) => t.stop());
        setStream(null);
        setMode("preview");
      },
      "image/jpeg",
      0.92
    );
  };

  // ---------------------------------------------------------------------------
  // Galeriden yükle
  // ---------------------------------------------------------------------------
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    stream?.getTracks().forEach((t) => t.stop());
    setStream(null);
    setCapturedFile(file);
    setCapturedImage(URL.createObjectURL(file));
    setMode("preview");
    e.target.value = "";
  };

  // ---------------------------------------------------------------------------
  // Sıfırla
  // ---------------------------------------------------------------------------
  const reset = () => {
    stream?.getTracks().forEach((t) => t.stop());
    setStream(null);
    setCapturedImage(null);
    setCapturedFile(null);
    setCameraReady(false);
    setCameraError(null);
    setMode("idle");
  };

  // ---------------------------------------------------------------------------
  // Analiz gönder
  // ---------------------------------------------------------------------------
  const handleAnalyze = async () => {
    if (!capturedFile) return;
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      const resultData = await aiApi.analyze(capturedFile);
      navigate("/results", { state: { image: capturedImage, resultData } });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Bilinmeyen hata";
      console.error("Analiz hatası:", msg);
      setAnalyzeError(msg);
    } finally {
      setAnalyzing(false);
    }
  };

  // ---------------------------------------------------------------------------
  // RENDER: Önizleme ekranı
  // ---------------------------------------------------------------------------
  if (mode === "preview" && capturedImage) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="relative mx-auto w-full max-w-sm overflow-hidden rounded-3xl shadow-card border border-border/60">
          <img
            src={capturedImage}
            alt="Seçilen yaprak fotoğrafı"
            className="w-full aspect-square object-cover"
          />
          <button
            onClick={reset}
            className="absolute top-3 right-3 flex h-10 w-10 items-center justify-center rounded-full bg-background/80 backdrop-blur shadow-card"
          >
            <X className="h-5 w-5" />
          </button>
          <div className="absolute bottom-3 left-3 rounded-full bg-background/85 px-3 py-1 text-xs font-medium backdrop-blur">
            Yaprak fotoğrafı hazır
          </div>
        </div>

        <Button
          onClick={handleAnalyze}
          disabled={analyzing}
          className="h-14 w-full rounded-2xl bg-leaf-gradient text-base font-bold shadow-soft"
        >
          {analyzing ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              AI Analiz Ediyor...
            </>
          ) : (
            <>
              <Zap className="mr-2 h-5 w-5" />
              Hastalık Analizi Başlat
            </>
          )}
        </Button>

        {analyzeError && (
          <div className="rounded-2xl bg-red-50 border border-red-200 p-3 text-sm text-red-800">
            <p className="font-semibold mb-0.5">Analiz başarısız</p>
            <p className="text-xs">{analyzeError}</p>
          </div>
        )}

        <button
          onClick={reset}
          disabled={analyzing}
          className="w-full rounded-2xl border border-border/60 bg-card py-3 text-sm font-semibold transition hover:bg-accent/40"
        >
          Farklı Fotoğraf Seç
        </button>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // RENDER: Kamera ekranı
  // ---------------------------------------------------------------------------
  if (mode === "camera") {
    const errorContent = () => {
      if (cameraError === "https") {
        return (
          <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
            <LockKeyhole className="h-12 w-12 text-amber-400" />
            <p className="text-sm font-semibold text-foreground">HTTPS Gerekli</p>
            <p className="text-xs text-muted-foreground">
              Kamera yalnızca güvenli bağlantılarda (HTTPS veya localhost) çalışır.
              Bunun yerine galeriden fotoğraf yükleyebilirsiniz.
            </p>
          </div>
        );
      }
      if (cameraError === "permission") {
        return (
          <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
            <AlertTriangle className="h-12 w-12 text-red-400" />
            <p className="text-sm font-semibold text-foreground">Kamera İzni Reddedildi</p>
            <p className="text-xs text-muted-foreground">
              İzin vermek için:
            </p>
            <ol className="text-xs text-muted-foreground text-left space-y-1 list-decimal list-inside">
              <li>Tarayıcı adres çubuğundaki kilit/bilgi ikonuna tıklayın</li>
              <li>"Site ayarları" veya "İzinler"i açın</li>
              <li>Kamerayı "İzin Ver" olarak değiştirin</li>
              <li>Sayfayı yenileyin ve tekrar deneyin</li>
            </ol>
          </div>
        );
      }
      if (cameraError === "notfound") {
        return (
          <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
            <Camera className="h-12 w-12 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">Bu cihazda kamera bulunamadı.</p>
          </div>
        );
      }
      return (
        <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
          <Camera className="h-12 w-12 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">Kamera başlatılamadı.</p>
        </div>
      );
    };

    return (
      <div className="space-y-4 animate-fade-in">
        <div className="overflow-hidden rounded-3xl border border-border/60 shadow-card">
          <div className="relative w-full aspect-square overflow-hidden bg-black">
            {cameraError ? (
              errorContent()
            ) : (
              <>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="h-full w-full object-cover"
                  style={{ transform: facingMode === "user" ? "scaleX(-1)" : "none" }}
                />
                {!cameraReady && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/80">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  </div>
                )}
              </>
            )}

            {!cameraError && (
              <button
                onClick={toggleCamera}
                className="absolute top-3 right-3 flex h-10 w-10 items-center justify-center rounded-full bg-background/70 backdrop-blur transition hover:bg-background/90"
              >
                <SwitchCamera className="h-5 w-5" />
              </button>
            )}

            {!cameraError && cameraReady && (
              <div className="pointer-events-none absolute inset-[12%] rounded-3xl border-2 border-primary/50" />
            )}

            {!cameraError && (
              <div className="absolute bottom-3 left-0 right-0 text-center">
                <span className="rounded-full bg-background/80 px-3 py-1 text-[11px] font-medium backdrop-blur">
                  Yaprağı çerçevenin içine yerleştirin
                </span>
              </div>
            )}
          </div>
        </div>

        {!cameraError && (
          <div className="flex justify-center">
            <button
              onClick={capturePhoto}
              disabled={!cameraReady}
              className="flex h-[72px] w-[72px] items-center justify-center rounded-full bg-leaf-gradient shadow-soft transition active:scale-95 disabled:opacity-40"
            >
              <div className="h-[58px] w-[58px] rounded-full border-[3px] border-primary-foreground/80" />
            </button>
          </div>
        )}

        <Button
          onClick={() => fileInputRef.current?.click()}
          variant="outline"
          className="h-12 w-full rounded-2xl border-border/60 font-semibold"
        >
          <UploadCloud className="mr-2 h-5 w-5" />
          Galeriden Yükle
        </Button>

        <button
          onClick={stopCamera}
          className="w-full rounded-2xl py-2 text-sm text-muted-foreground hover:text-foreground transition"
        >
          Geri Dön
        </button>

        <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileUpload} />
        <canvas ref={canvasRef} className="hidden" />
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // RENDER: Ana ekran — galeri birincil, kamera ikincil
  // ---------------------------------------------------------------------------
  return (
    <div className="space-y-5 animate-fade-in">
      {/* Açıklama */}
      <div className="rounded-2xl bg-muted/50 px-4 py-3 text-sm text-muted-foreground">
        Yaprak fotoğrafı yükleyin veya kameranızla çekin. Yapay zeka hastalığı analiz edecek.
      </div>

      {/* BİRİNCİL: Galeriden yükle */}
      <Button
        onClick={() => fileInputRef.current?.click()}
        className="h-16 w-full rounded-2xl bg-leaf-gradient text-base font-bold shadow-soft"
      >
        <UploadCloud className="mr-2 h-6 w-6" />
        Galeriden Fotoğraf Yükle
      </Button>

      {/* Ayırıcı */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-border" />
        <span className="text-xs text-muted-foreground font-medium">veya</span>
        <div className="flex-1 h-px bg-border" />
      </div>

      {/* İKİNCİL: Kamerayı aç */}
      <Button
        onClick={() => startCamera()}
        variant="outline"
        className="h-14 w-full rounded-2xl border-border/60 text-base font-semibold"
      >
        <Camera className="mr-2 h-5 w-5" />
        Kamerayla Çek
      </Button>

      {/* HTTPS uyarısı */}
      {!window.isSecureContext && (
        <div className="flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800">
          <LockKeyhole className="h-4 w-4 mt-0.5 shrink-0" />
          <span>
            Güvenli bağlantı (HTTPS) olmadan kamera çalışmayabilir. Galeriden yükleme önerilir.
          </span>
        </div>
      )}

      <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileUpload} />
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
