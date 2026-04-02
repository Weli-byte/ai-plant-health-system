import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { History, Search } from "lucide-react";

const allAnalyses = [
  { id: 1, date: "2 Nisan 2026", plant: "Domates", result: "Yaprak Yanıklığı", risk: "high" },
  { id: 2, date: "1 Nisan 2026", plant: "Üzüm", result: "Külleme", risk: "medium" },
  { id: 3, date: "31 Mart 2026", plant: "Patates", result: "Sağlıklı", risk: "low" },
  { id: 4, date: "30 Mart 2026", plant: "Elma", result: "Karaleke", risk: "high" },
  { id: 5, date: "29 Mart 2026", plant: "Buğday", result: "Pas Hastalığı", risk: "medium" },
  { id: 6, date: "28 Mart 2026", plant: "Mısır", result: "Sağlıklı", risk: "low" },
  { id: 7, date: "27 Mart 2026", plant: "Domates", result: "Mildiyö", risk: "high" },
  { id: 8, date: "26 Mart 2026", plant: "Üzüm", result: "Sağlıklı", risk: "low" },
];

const riskBadge = (risk: string) => {
  switch (risk) {
    case "high": return <Badge variant="destructive">Yüksek</Badge>;
    case "medium": return <Badge className="bg-warning text-warning-foreground">Orta</Badge>;
    default: return <Badge className="bg-success text-success-foreground">Düşük</Badge>;
  }
};

export default function AnalysisHistory() {
  const [search, setSearch] = useState("");
  const [filterRisk, setFilterRisk] = useState("all");

  const filtered = allAnalyses.filter((a) => {
    const matchesSearch = a.plant.toLowerCase().includes(search.toLowerCase()) || a.result.toLowerCase().includes(search.toLowerCase());
    const matchesRisk = filterRisk === "all" || a.risk === filterRisk;
    return matchesSearch && matchesRisk;
  });

  return (
    <div className="container space-y-6 py-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Analiz Geçmişi</h1>
        <p className="text-muted-foreground">Tüm geçmiş analizlerinizi görüntüleyin</p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input placeholder="Bitki veya hastalık ara..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
        <Select value={filterRisk} onValueChange={setFilterRisk}>
          <SelectTrigger className="w-full sm:w-48">
            <SelectValue placeholder="Risk filtrele" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tümü</SelectItem>
            <SelectItem value="high">Yüksek Risk</SelectItem>
            <SelectItem value="medium">Orta Risk</SelectItem>
            <SelectItem value="low">Düşük Risk</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="divide-y">
            {filtered.map((a) => (
              <Link key={a.id} to={`/analysis/${a.id}`} className="flex items-center justify-between p-4 transition-colors hover:bg-accent">
                <div className="space-y-1">
                  <p className="text-sm font-medium text-foreground">{a.plant} — {a.result}</p>
                  <p className="text-xs text-muted-foreground">{a.date}</p>
                </div>
                {riskBadge(a.risk)}
              </Link>
            ))}
            {filtered.length === 0 && (
              <div className="p-8 text-center text-muted-foreground">
                <History className="mx-auto mb-2 h-8 w-8" />
                <p>Sonuç bulunamadı</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
