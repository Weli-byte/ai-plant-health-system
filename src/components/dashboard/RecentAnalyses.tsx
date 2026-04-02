import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { History } from "lucide-react";

const analyses = [
  { id: 1, date: "2 Nisan 2026", plant: "Domates", result: "Yaprak Yanıklığı", risk: "high" },
  { id: 2, date: "1 Nisan 2026", plant: "Üzüm", result: "Külleme", risk: "medium" },
  { id: 3, date: "31 Mart 2026", plant: "Patates", result: "Sağlıklı", risk: "low" },
  { id: 4, date: "30 Mart 2026", plant: "Elma", result: "Karaleke", risk: "high" },
  { id: 5, date: "29 Mart 2026", plant: "Buğday", result: "Pas Hastalığı", risk: "medium" },
];

const riskBadge = (risk: string) => {
  switch (risk) {
    case "high":
      return <Badge variant="destructive">Yüksek Risk</Badge>;
    case "medium":
      return <Badge className="bg-warning text-warning-foreground">Orta Risk</Badge>;
    default:
      return <Badge className="bg-success text-success-foreground">Düşük Risk</Badge>;
  }
};

export function RecentAnalyses() {
  return (
    <Card className="animate-fade-in">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-lg">
          <History className="h-5 w-5 text-primary" />
          Son Analizler
        </CardTitle>
        <Link to="/history" className="text-sm text-primary hover:underline">
          Tümünü Gör
        </Link>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {analyses.map((a) => (
            <Link
              key={a.id}
              to={`/analysis/${a.id}`}
              className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-accent"
            >
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">{a.plant} — {a.result}</p>
                <p className="text-xs text-muted-foreground">{a.date}</p>
              </div>
              {riskBadge(a.risk)}
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
