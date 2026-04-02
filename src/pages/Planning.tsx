import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CalendarDays, Sprout, TrendingUp, Droplets } from "lucide-react";

const calendar = [
  { month: "Nisan", tasks: ["Domates fidesi dikimi", "İlk gübreleme", "Damlama sulama kontrolü"], season: "İlkbahar" },
  { month: "Mayıs", tasks: ["Budama", "Zararlı kontrolü", "Destekleme teli kurulumu"], season: "İlkbahar" },
  { month: "Haziran", tasks: ["İkinci gübreleme", "Sulama artırma", "Meyve seyreltme"], season: "Yaz" },
  { month: "Temmuz", tasks: ["Hasat başlangıcı", "Hastalık taraması", "Gölgeleme"], season: "Yaz" },
];

const carePlan = [
  { icon: Droplets, title: "Sulama Planı", desc: "Sabah erken saatlerde, haftada 3-4 kez, damlama sulama tercih edin.", color: "text-info" },
  { icon: Sprout, title: "Gübreleme", desc: "NPK 15-15-15 gübresi, ayda bir kez toprak üstüne uygulayın.", color: "text-primary" },
  { icon: TrendingUp, title: "Verimlilik Tahmini", desc: "Mevcut koşullarda %85 verimlilik oranı beklenmektedir.", color: "text-success" },
];

export default function Planning() {
  return (
    <div className="container space-y-6 py-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Tarım Planlama</h1>
        <p className="text-muted-foreground">Ekim takvimi, bakım planı ve verimlilik tahminleri</p>
      </div>

      {/* Seasonal Calendar */}
      <Card className="animate-fade-in">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <CalendarDays className="h-5 w-5 text-primary" />
            Ekim Takvimi
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {calendar.map((month) => (
              <div key={month.month} className="rounded-xl border p-4">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="font-semibold text-foreground">{month.month}</h3>
                  <Badge variant="secondary">{month.season}</Badge>
                </div>
                <ul className="space-y-2">
                  {month.tasks.map((task) => (
                    <li key={task} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <Sprout className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                      {task}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Care Plan */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {carePlan.map((item) => (
          <Card key={item.title} className="animate-fade-in">
            <CardContent className="flex items-start gap-4 p-5">
              <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent ${item.color}`}>
                <item.icon className="h-6 w-6" />
              </div>
              <div>
                <p className="font-semibold text-foreground">{item.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{item.desc}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
