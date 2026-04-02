import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const data = [
  { name: "Oca", risk: 12 },
  { name: "Şub", risk: 19 },
  { name: "Mar", risk: 28 },
  { name: "Nis", risk: 35 },
  { name: "May", risk: 42 },
  { name: "Haz", risk: 30 },
  { name: "Tem", risk: 25 },
  { name: "Ağu", risk: 38 },
  { name: "Eyl", risk: 22 },
  { name: "Eki", risk: 15 },
  { name: "Kas", risk: 10 },
  { name: "Ara", risk: 8 },
];

export function RiskChart() {
  return (
    <Card className="animate-fade-in">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <AlertTriangle className="h-5 w-5 text-warning" />
          Aylık Risk Tahmini
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(100 15% 85%)" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} stroke="hsl(120 10% 40%)" />
              <YAxis tick={{ fontSize: 12 }} stroke="hsl(120 10% 40%)" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(40 30% 98%)",
                  border: "1px solid hsl(100 15% 85%)",
                  borderRadius: "0.5rem",
                }}
              />
              <Bar dataKey="risk" fill="hsl(122 39% 49%)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
