import { BarChart3, Bug, ShieldCheck, AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const stats = [
  { label: "Toplam Analiz", value: "1,284", icon: BarChart3, color: "text-primary" },
  { label: "Tespit Edilen Hastalık", value: "156", icon: Bug, color: "text-destructive" },
  { label: "Sağlıklı Bitki Oranı", value: "%87.8", icon: ShieldCheck, color: "text-success" },
  { label: "Aktif Risk Uyarısı", value: "12", icon: AlertTriangle, color: "text-warning" },
];

export function StatsCards() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => (
        <Card key={stat.label} className="animate-fade-in">
          <CardContent className="flex items-center gap-4 p-5">
            <div className={`flex h-12 w-12 items-center justify-center rounded-xl bg-accent ${stat.color}`}>
              <stat.icon className="h-6 w-6" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">{stat.value}</p>
              <p className="text-sm text-muted-foreground">{stat.label}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
