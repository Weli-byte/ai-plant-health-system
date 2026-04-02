import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Pill, Droplets, Sun, Wind } from "lucide-react";

const recommendations = [
  { icon: Pill, title: "Bakır Sülfat Uygulaması", desc: "Domates yaprak yanıklığı için haftada bir uygulayın", color: "text-primary" },
  { icon: Droplets, title: "Sulama Azaltma", desc: "Külleme riski yüksek, sulamayı %30 azaltın", color: "text-info" },
  { icon: Sun, title: "Güneş Koruma", desc: "Aşırı sıcaklarda gölgeleme örtüsü kullanın", color: "text-warning" },
  { icon: Wind, title: "Havalandırma", desc: "Sera havalandırmasını artırarak nem oranını düşürün", color: "text-success" },
];

export function CareRecommendations() {
  return (
    <Card className="animate-fade-in">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Pill className="h-5 w-5 text-primary" />
          İlaç & Bakım Önerileri
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {recommendations.map((rec) => (
          <div key={rec.title} className="flex items-start gap-3 rounded-lg border p-3">
            <div className={`mt-0.5 ${rec.color}`}>
              <rec.icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">{rec.title}</p>
              <p className="text-xs text-muted-foreground">{rec.desc}</p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
