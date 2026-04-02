import { useState, useRef, useEffect } from "react";
import { MessageCircle, X, Send, Bot, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface Message {
  id: number;
  role: "user" | "bot";
  content: string;
}

const defaultMessages: Message[] = [
  { id: 1, role: "bot", content: "Merhaba! 🌱 Ben AgriAI asistanınız. Bitki hastalıkları, bakım önerileri veya tarım planlaması hakkında sorularınızı yanıtlayabilirim. Size nasıl yardımcı olabilirim?" },
];

const botResponses: Record<string, string> = {
  hastalık: "Bitki hastalıklarını tespit etmek için Dashboard'daki fotoğraf yükleme alanını kullanabilirsiniz. Yapay zeka modelimiz yaprak, meyve ve gövde hastalıklarını yüksek doğrulukla tespit edebilir.",
  ilaç: "İlaç önerileri için önce hastalık tespiti yapmanız gerekmektedir. Analiz sonuçlarında hastalığa özel ilaç ve dozaj bilgileri sunulmaktadır.",
  sulama: "Sulama planlaması için Planlama sayfasını ziyaret edebilirsiniz. Bitki türüne ve mevsime göre öneriler sunuyoruz.",
  ekim: "Ekim takvimi önerileri Planlama sayfasında mevcuttur. Bölgenize ve iklim koşullarına göre en uygun ekim zamanlarını görebilirsiniz.",
  default: "Anlıyorum. Bu konuda size daha detaylı bilgi sunmak için çalışıyoruz. Başka bir sorunuz var mı?",
};

export function Chatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>(defaultMessages);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;
    const userMsg: Message = { id: Date.now(), role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    setTimeout(() => {
      const lower = input.toLowerCase();
      const key = Object.keys(botResponses).find((k) => lower.includes(k)) || "default";
      const botMsg: Message = { id: Date.now() + 1, role: "bot", content: botResponses[key] };
      setMessages((prev) => [...prev, botMsg]);
    }, 800);
  };

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-primary shadow-lg transition-all hover:scale-105 hover:shadow-xl",
          open && "rotate-90"
        )}
      >
        {open ? (
          <X className="h-6 w-6 text-primary-foreground" />
        ) : (
          <MessageCircle className="h-6 w-6 text-primary-foreground" />
        )}
      </button>

      {/* Chat window */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 flex h-[28rem] w-[22rem] flex-col overflow-hidden rounded-2xl border bg-card shadow-2xl animate-slide-up">
          {/* Header */}
          <div className="flex items-center gap-3 bg-primary px-4 py-3">
            <Bot className="h-6 w-6 text-primary-foreground" />
            <div>
              <p className="text-sm font-semibold text-primary-foreground">AgriAI Asistan</p>
              <p className="text-xs text-primary-foreground/70">Çevrimiçi</p>
            </div>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  "flex gap-2",
                  msg.role === "user" ? "flex-row-reverse" : "flex-row"
                )}
              >
                <div
                  className={cn(
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
                    msg.role === "user" ? "bg-secondary" : "bg-primary"
                  )}
                >
                  {msg.role === "user" ? (
                    <User className="h-3.5 w-3.5 text-secondary-foreground" />
                  ) : (
                    <Bot className="h-3.5 w-3.5 text-primary-foreground" />
                  )}
                </div>
                <div
                  className={cn(
                    "max-w-[75%] rounded-2xl px-3 py-2 text-sm",
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                  )}
                >
                  {msg.content}
                </div>
              </div>
            ))}
          </div>

          {/* Input */}
          <div className="border-t p-3">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex gap-2"
            >
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Bir soru sorun..."
                className="flex-1"
              />
              <Button size="icon" type="submit" className="shrink-0">
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
