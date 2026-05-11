import { useRef, useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Camera, UploadCloud, SwitchCamera, Loader2, X, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { aiApi } from "@/services/api";

export default function CameraAnalysis() {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [stream, setStream] = useState<MediaStream | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<"environment" | "user">("environment");

  // Çekilmiş / yüklenmiş fotoğraf
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [capturedFile, setCapturedFile] = useState<File | null>(null);

  // Analiz durumu
  const [analyzing, setAnalyzing] = useState(false);

  // ---------------------------------------------------------------------------
  // Kamera başlat
  // ---------------------------------------------------------------------------
  const startCamera = useCallback(async () => {
    // Önceki stream'i kapat
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
    }

    setCameraError(null);
    setCameraReady(false);

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode,
          width: { ideal: 1080 },
          height: { ideal: 1080 },
        },
        audio: false,
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        videoRef.current.onloadedmetadata = () => setCameraReady(true);
      }
    } catch (err) {
      console.error("Kamera erişim hatası:", err);
      setCameraError(
        "Kamera erişimi reddedildi veya cihazda kamera bulunamadı. Tarayıcı ayarlarından kamera iznini kontrol edin."
      );
    }
  }, [facingMode]);

  // İlk açılışta kamerayı başlat
  useEffect(() => {
    startCamera();
    return () => {
      // Cleanup: kamerayı kapat
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [facingMode]);

  // ---------------------------------------------------------------------------
  // Fotoğraf çek
  // ---------------------------------------------------------------------------
  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    // Kare kırpma: video'nun kısa kenarını al
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
        // Kamerayı durdur
        stream?.getTracks().forEach((t) => t.stop());
      },
      "image/jpeg",
      0.92
    );
  };

  // ---------------------------------------------------------------------------
  // Dosyadan yükle
  // ---------------------------------------------------------------------------
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setCapturedFile(file);
    setCapturedImage(URL.createObjectURL(file));
    // Kamerayı durdur
    stream?.getTracks().forEach((t) => t.stop());
  };

  // ---------------------------------------------------------------------------
  // Yeniden çek
  // ---------------------------------------------------------------------------
  const retake = () => {
    setCapturedImage(null);
    setCapturedFile(null);
    startCamera();
  };

  // ---------------------------------------------------------------------------
  // Analiz et — API'ye gönder
  // ---------------------------------------------------------------------------
  const handleAnalyze = async () => {
    if (!capturedFile) return;
    setAnalyzing(true);

    try {
      const resultData = await aiApi.analyze(capturedFile);
      navigate("/results", { state: { image: capturedImage, resultData } });
    } catch (err) {
      console.error("Analiz hatası:", err);
      alert("Analiz yapılamadı. Sunucu bağlantısını kontrol edin.");
    } finally {
      setAnalyzing(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Kamera geçişi (ön/arka)
  // ---------------------------------------------------------------------------
  const toggleCamera = () => {
    setFacingMode((prev) => (prev === "environment" ? "user" : "environment"));
  };

  // ---------------------------------------------------------------------------
  // RENDER
  // ---------------------------------------------------------------------------

  // Fotoğraf çekilmiş → önizleme ekranı
  if (capturedImage) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="relative mx-auto w-full max-w-sm overflow-hidden rounded-3xl shadow-card border border-border/60">
          <img
            src={capturedImage}
            alt="Çekilen yaprak fotoğrafı"
            className="w-full aspect-square object-cover"
          />
          <div className="absolute top-3 right-3">
            <button
              onClick={retake}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-background/80 text-foreground backdrop-blur shadow-card"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="absolute bottom-3 left-3 rounded-full bg-background/85 px-3 py-1 text-xs font-medium text-foreground backdrop-blur">
            📷 Yaprak fotoğrafı hazır
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

        <button
          onClick={retake}
          disabled={analyzing}
          className="w-full rounded-2xl border border-border/60 bg-card py-3 text-sm font-semibold text-foreground transition hover:bg-accent/40"
        >
          Tekrar Çek
        </button>
      </div>
    );
  }

  // Kamera ekranı
  return (
    <div className="space-y-4 animate-fade-in">
      {/* Kare kamera görüntüsü */}
      <Card className="overflow-hidden rounded-3xl border-border/60 shadow-card">
        <CardContent className="relative p-0">
          {/* Video */}
          <div className="relative w-full aspect-square overflow-hidden bg-black">
            {cameraError ? (
              <div className="flex h-full flex-col items-center justify-center p-6 text-center">
                <Camera className="mb-3 h-12 w-12 text-muted-foreground/40" />
                <p className="text-sm text-muted-foreground">{cameraError}</p>
              </div>
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

            {/* Kamera geçiş butonu */}
            {!cameraError && (
              <button
                onClick={toggleCamera}
                className="absolute top-3 right-3 flex h-10 w-10 items-center justify-center rounded-full bg-background/70 text-foreground backdrop-blur transition hover:bg-background/90"
              >
                <SwitchCamera className="h-5 w-5" />
              </button>
            )}

            {/* Hedefleme çerçevesi */}
            {!cameraError && cameraReady && (
              <div className="pointer-events-none absolute inset-[12%] rounded-3xl border-2 border-primary/50" />
            )}

            {/* Alt bilgi */}
            {!cameraError && (
              <div className="absolute bottom-3 left-0 right-0 text-center">
                <span className="rounded-full bg-background/80 px-3 py-1 text-[11px] font-medium text-foreground backdrop-blur">
                  Yaprağı çerçevenin içine yerleştirin
                </span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Çek butonu */}
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

      {/* Galeriden yükle butonu */}
      <Button
        onClick={() => fileInputRef.current?.click()}
        variant="outline"
        className="h-14 w-full rounded-2xl border-border/60 text-base font-semibold"
      >
        <UploadCloud className="mr-2 h-5 w-5" />
        Galeriden Fotoğraf Yükle
      </Button>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileUpload}
      />

      {/* Gizli canvas — fotoğraf kırpma için */}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
