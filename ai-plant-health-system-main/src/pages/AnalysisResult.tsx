import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Target, TrendingUp, Pill, Clock, CheckCircle, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

const mockResult = {
  plant: "Domates",
  disease: "Yaprak Yanıklığı (Late Blight)",
  confidence: 94.2,
  description: "Phytophthora infestans kaynaklı fungal enfeksiyon tespit edildi. Yapraklarda koyu kahverengi-siyah lekeler ve beyaz sporlar gözlemlenmektedir.",
  severity: "high" as const,
  timeline: [
    { day: "Bugün", status: "Erken evre lekeler", severity: "medium" },
    { day: "3 Gün Sonra", status: "Lekelerin yayılması bekleniyor", severity: "high" },
    { day: "7 Gün Sonra", status: "Müdahalesiz yaprak kaybı riski", severity: "high" },
    { day: "14 Gün Sonra", status: "Tedavi ile iyileşme bekleniyor", severity: "low" },
  ],
  medications: [
    { name: "Bakır Oksiklorür", dosage: "3-5 g/L su", method: "Yaprak spreyi, 7 gün aralıkla" },
    { name: "Metalaksil", dosage: "2.5 g/L su", method: "Sistemik uygulama, 10 gün aralıkla" },
    { name: "Mancozeb", dosage: "2-3 g/L su", method: "Koruyucu sprey, 5-7 gün aralıkla" },
  ],
};

export default function AnalysisResult() {
  const { id } = useParams();

  return (
    <div className="container space-y-6 py-6">
      <div className="flex items-center gap-3">
        <Link to="/">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-foreground">Analiz Sonucu #{id}</h1>
          <p className="text-muted-foreground">{mockResult.plant} — {mockResult.disease}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Image with overlay */}
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Target className="h-5 w-5 text-primary" />
              Karar Bölgesi
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="relative overflow-hidden rounded-xl bg-muted">
              <div className="flex h-64 items-center justify-center bg-accent">
                <div className="text-center text-muted-foreground">
                  <Target className="mx-auto mb-2 h-16 w-16" />
                  <p className="text-sm">Yüklenen fotoğraf burada gösterilir</p>
                  <p className="text-xs">Hastalıklı bölgeler işaretlenir</p>
                </div>
              </div>
              {/* Mock overlay markers */}
              <div className="absolute left-[20%] top-[30%] h-16 w-16 rounded-full border-2 border-destructive/70 bg-destructive/10" />
              <div className="absolute left-[55%] top-[45%] h-12 w-12 rounded-full border-2 border-destructive/70 bg-destructive/10" />
              <div className="absolute left-[40%] top-[60%] h-10 w-10 rounded-full border-2 border-warning/70 bg-warning/10" />
            </div>
          </CardContent>
        </Card>

        {/* Diagnosis info */}
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle className="text-lg">Teşhis Bilgileri</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Hastalık</span>
              <span className="font-medium text-foreground">{mockResult.disease}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Güven Oranı</span>
              <span className="font-bold text-primary">%{mockResult.confidence}</span>
            </div>
            <Progress value={mockResult.confidence} className="h-2" />
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Risk Seviyesi</span>
              <Badge variant="destructive">Yüksek</Badge>
            </div>
            <p className="rounded-lg bg-accent p-3 text-sm text-foreground">{mockResult.description}</p>
          </CardContent>
        </Card>
      </div>

      {/* Future prediction timeline */}
      <Card className="animate-fade-in">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <TrendingUp className="h-5 w-5 text-primary" />
            Gelecek Durum Tahmini
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {mockResult.timeline.map((step, i) => (
              <div key={i} className="flex flex-col items-center rounded-xl border p-4 text-center">
                <div className={`mb-2 flex h-10 w-10 items-center justify-center rounded-full ${
                  step.severity === "high"
                    ? "bg-destructive/10 text-destructive"
                    : step.severity === "medium"
                    ? "bg-warning/10 text-warning"
                    : "bg-success/10 text-success"
                }`}>
                  {step.severity === "low" ? (
                    <CheckCircle className="h-5 w-5" />
                  ) : step.severity === "high" ? (
                    <AlertTriangle className="h-5 w-5" />
                  ) : (
                    <Clock className="h-5 w-5" />
                  )}
                </div>
                <p className="text-sm font-semibold text-foreground">{step.day}</p>
                <p className="text-xs text-muted-foreground">{step.status}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Medications */}
      <Card className="animate-fade-in">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Pill className="h-5 w-5 text-primary" />
            İlaç ve Bakım Önerileri
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockResult.medications.map((med) => (
              <div key={med.name} className="rounded-lg border p-4">
                <p className="font-medium text-foreground">{med.name}</p>
                <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <div>
                    <p className="text-xs text-muted-foreground">Dozaj</p>
                    <p className="text-sm text-foreground">{med.dosage}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Uygulama</p>
                    <p className="text-sm text-foreground">{med.method}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
