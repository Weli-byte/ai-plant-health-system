import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Leaf, Sprout } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { loginMock } from "@/lib/auth";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    loginMock(email || "ciftci@plant-health.app");
    navigate("/");
  };

  return (
    <div className="flex min-h-dvh flex-col justify-between bg-earth-gradient px-6 py-10">
      <div className="mx-auto w-full max-w-sm flex-1 flex flex-col justify-center">
        <div className="mb-10 text-center">
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-3xl bg-leaf-gradient shadow-soft">
            <Leaf className="h-8 w-8 text-primary-foreground" />
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            AI Plant Health System'e hoş geldin
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Tarlanı yapay zekâ ile izle, hastalıkları erken yakala.
          </p>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              E-posta
            </label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ornek@tarla.com"
              className="h-12 rounded-2xl border-border/60 bg-card"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Şifre
            </label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="h-12 rounded-2xl border-border/60 bg-card"
            />
          </div>
          <Button
            type="submit"
            className="h-12 w-full rounded-2xl bg-leaf-gradient text-base font-semibold shadow-soft"
          >
            <Sprout className="mr-2 h-4 w-4" />
            Giriş yap
          </Button>
          <p className="text-center text-xs text-muted-foreground">
            Hesabın yok mu?{" "}
            <button
              type="button"
              onClick={submit}
              className="font-semibold text-primary underline-offset-2 hover:underline"
            >
              Hemen başla
            </button>
          </p>
        </form>
      </div>

      <p className="text-center text-[11px] text-muted-foreground">
        AI Plant Health System · Doğa dostu tarım için
      </p>
    </div>
  );
}
