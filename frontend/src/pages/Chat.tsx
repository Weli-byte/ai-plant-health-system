import { FormEvent, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Send, Sparkles, Sprout, Sun, Droplets, Wheat } from "lucide-react";
import { cn } from "@/lib/utils";
import { aiApi, ChatHistoryMessage } from "@/services/api";

type Msg = {
  id: number;
  role: "user" | "ai";
  content: string;
};

const suggestions = [
  { icon: Sprout, text: "Bu hastalık neden olur?" },
  { icon: Droplets, text: "Sulamayı artırayım mı?" },
  { icon: Sun, text: "Hangi ilacı kullanmalıyım?" },
  { icon: Wheat, text: "Bu hafta ne ekmeliyim?" },
];

export default function Chat() {
  const location = useLocation();
  const prefill: string | undefined = location.state?.prefill;

  const [messages, setMessages] = useState<Msg[]>([
    {
      id: 1,
      role: "ai",
      content:
        "Merhaba 🌿 Ben deneyimli bir Türk ziraat mühendisiyim. Bitkilerin, hastalıklar, sulama ya da ne ekeceğin hakkında istediğini sorabilirsin. Fotoğraf yükleyerek anında analiz de yaptırabilirsin.",
    },
  ]);
  const [input, setInput] = useState(prefill ?? "");
  const [thinking, setThinking] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  const send = async (text: string) => {
    if (!text.trim()) return;

    // Konuşma geçmişini Anthropic formatına çevir:
    // - messages[0] ilk AI selamlama mesajıdır, atlanır (Anthropic "user" ile başlamalı).
    // - "ai" rolü "assistant" olarak eşlenir.
    const history: ChatHistoryMessage[] = messages.slice(1).map((m) => ({
      role: m.role === "user" ? "user" : "assistant",
      content: m.content,
    }));

    const userMsg: Msg = { id: Date.now(), role: "user", content: text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setThinking(true);

    try {
      const data = await aiApi.chat(text, history);
      setMessages((m) => [...m, { id: Date.now() + 1, role: "ai", content: data.response }]);
    } catch (error) {
      console.error("Chat API hatası:", error);
      setMessages((m) => [
        ...m,
        {
          id: Date.now() + 1,
          role: "ai",
          content: "Üzgünüm, şu an yanıt veremiyorum. Sunucu bağlantısını kontrol edin.",
        },
      ]);
    } finally {
      setThinking(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    send(input);
  };

  return (
    <div
      className="-mx-4 -mb-24 flex h-[calc(100dvh-9rem)] flex-col"
      style={{ background: "var(--gradient-earth)" }}
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-5 pb-3 pt-2" style={{ background: "var(--renk-koyu-yesil)" }}>
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl text-white shadow-soft" style={{ background: "var(--renk-acik-yesil)" }}>
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <p className="text-base font-semibold text-white">Tarla Asistanı</p>
          <p className="text-xs" style={{ color: "var(--renk-soluk-yesil)" }}>Ziraat mühendisi · Fotoğraf analizi</p>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3 no-scrollbar">
        {messages.map((m) => (
          <Bubble key={m.id} msg={m} />
        ))}
        {thinking && (
          <div className="flex items-center gap-2 px-2">
            <div className="flex gap-1 rounded-2xl bg-card/80 px-3 py-2 shadow-card">
              <Dot delay="0s" />
              <Dot delay="0.15s" />
              <Dot delay="0.3s" />
            </div>
          </div>
        )}

        {messages.length <= 1 && (
          <div className="grid grid-cols-2 gap-2 pt-2">
            {suggestions.map((s) => (
              <button
                key={s.text}
                onClick={() => send(s.text)}
                className="flex items-start gap-2 rounded-2xl bg-card/70 p-3 text-left shadow-card backdrop-blur transition hover:bg-card"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-accent text-accent-foreground">
                  <s.icon className="h-4 w-4" />
                </span>
                <span className="text-xs font-medium leading-snug text-foreground">{s.text}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Input area */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-border/60 bg-card/80 px-3 py-3 backdrop-blur"
      >
        <div className="flex items-end gap-2 rounded-3xl bg-background px-3 py-2.5 shadow-card">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            rows={1}
            placeholder="Bir şey sor… mesela 'sulamayı artırayım mı?'"
            className="max-h-32 flex-1 resize-none bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
          />

          <button
            type="submit"
            disabled={!input.trim()}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white shadow-soft transition disabled:opacity-50"
            style={{ background: "var(--renk-acik-yesil)" }}
          >
            <Send className="h-4 w-4" />
          </button>
        </div>

        <p className="mt-2 text-center text-[10px] text-muted-foreground">
          AI cevapları öneridir · Sorularınızı yazarak iletin
        </p>
      </form>
    </div>
  );
}

function Bubble({ msg }: { msg: Msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex w-full flex-col gap-1", isUser ? "items-end" : "items-start")}>
      <div
        className={cn(
          "max-w-[82%] rounded-3xl px-4 py-2.5 text-sm leading-relaxed shadow-card animate-slide-up",
          isUser ? "rounded-br-lg text-white" : "rounded-bl-lg bg-white text-foreground"
        )}
        style={isUser
          ? { background: "var(--renk-acik-yesil)" }
          : { border: "1px solid var(--renk-bej-border)" }
        }
      >
        <span dangerouslySetInnerHTML={{ __html: format(msg.content) }} />
      </div>
    </div>
  );
}

function format(s: string) {
  return s
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n\n/g, "<br/><br/>")
    .replace(/\n/g, "<br/>");
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="h-2 w-2 animate-bounce rounded-full bg-primary/70"
      style={{ animationDelay: delay }}
    />
  );
}
