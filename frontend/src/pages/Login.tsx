import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, Leaf } from "lucide-react";
import { cn } from "@/lib/utils";
import { loginMock } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type Tab = "login" | "register";
type Errors = Record<string, string>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function GoogleButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex h-12 w-full items-center justify-center gap-3 rounded-2xl border border-border/70 bg-white text-sm font-medium text-gray-700 shadow-card transition hover:bg-gray-50 active:scale-[.98]"
    >
      {/* Official Google "G" logo */}
      <svg viewBox="0 0 24 24" className="h-5 w-5" xmlns="http://www.w3.org/2000/svg">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
      </svg>
      {label}
    </button>
  );
}

function OrDivider() {
  return (
    <div className="flex items-center gap-3">
      <div className="h-px flex-1 bg-border/60" />
      <span className="text-[11px] font-medium text-muted-foreground">veya</span>
      <div className="h-px flex-1 bg-border/60" />
    </div>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
      {children}
    </label>
  );
}

function FieldError({ msg }: { msg?: string }) {
  if (!msg) return null;
  return <p className="mt-1 text-[11px] text-destructive">{msg}</p>;
}

function PasswordInput({
  value,
  onChange,
  placeholder = "••••••••",
  hasError,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  hasError?: boolean;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <Input
        type={show ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={cn(
          "h-12 rounded-2xl border-border/60 bg-background pr-11",
          hasError && "border-destructive focus-visible:ring-destructive"
        )}
      />
      <button
        type="button"
        tabIndex={-1}
        onClick={() => setShow((s) => !s)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition hover:text-foreground"
        aria-label={show ? "Şifreyi gizle" : "Şifreyi göster"}
      >
        {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Login Form
// ---------------------------------------------------------------------------
function LoginForm({ onSuccess }: { onSuccess: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [forgotSent, setForgotSent] = useState(false);

  const clear = (field: string) =>
    setErrors((prev) => ({ ...prev, [field]: "" }));

  const handleForgot = () => {
    if (!email.trim() || !isValidEmail(email)) {
      setErrors((prev) => ({ ...prev, email: "Önce geçerli bir e-posta girin." }));
      return;
    }
    console.log("[Auth] Şifre sıfırlama isteği:", email);
    setForgotSent(true);
    setTimeout(() => setForgotSent(false), 4000);
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const errs: Errors = {};
    if (!email.trim()) errs.email = "E-posta adresi gerekli.";
    else if (!isValidEmail(email)) errs.email = "Geçerli bir e-posta adresi girin.";
    if (!password) errs.password = "Şifre gerekli.";
    if (Object.keys(errs).length) { setErrors(errs); return; }
    loginMock(email.trim());
    onSuccess();
  };

  return (
    <div className="space-y-4">
      <GoogleButton
        label="Google ile Giriş Yap"
        onClick={() => {
          console.log("[Auth] Google ile giriş — OAuth henüz entegre edilmedi.");
          loginMock("google@demo.com", "Google Kullanıcısı");
          onSuccess();
        }}
      />
      <OrDivider />

      <form onSubmit={handleSubmit} noValidate className="space-y-3">
        <div>
          <FieldLabel>E-posta</FieldLabel>
          <Input
            type="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); clear("email"); }}
            placeholder="ornek@tarla.com"
            className={cn(
              "h-12 rounded-2xl border-border/60 bg-background",
              errors.email && "border-destructive"
            )}
            autoComplete="email"
          />
          <FieldError msg={errors.email} />
        </div>

        <div>
          <FieldLabel>Şifre</FieldLabel>
          <PasswordInput
            value={password}
            onChange={(v) => { setPassword(v); clear("password"); }}
            hasError={!!errors.password}
          />
          <FieldError msg={errors.password} />
        </div>

        {/* Forgot password */}
        <div className="flex items-center justify-end">
          {forgotSent ? (
            <span className="text-[11px] text-primary animate-fade-in">
              Sıfırlama bağlantısı e-postanıza gönderildi.
            </span>
          ) : (
            <button
              type="button"
              onClick={handleForgot}
              className="text-[11px] text-primary hover:underline underline-offset-2"
            >
              Şifremi unuttum
            </button>
          )}
        </div>

        <Button
          type="submit"
          className="h-12 w-full rounded-2xl bg-leaf-gradient text-base font-semibold shadow-soft"
        >
          Giriş Yap
        </Button>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Register Form
// ---------------------------------------------------------------------------
function RegisterForm({ onSuccess }: { onSuccess: () => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [terms, setTerms] = useState(false);
  const [errors, setErrors] = useState<Errors>({});

  const clear = (field: string) =>
    setErrors((prev) => ({ ...prev, [field]: "" }));

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const errs: Errors = {};
    if (!name.trim()) errs.name = "Ad Soyad gerekli.";
    if (!email.trim()) errs.email = "E-posta adresi gerekli.";
    else if (!isValidEmail(email)) errs.email = "Geçerli bir e-posta adresi girin.";
    if (!password) errs.password = "Şifre gerekli.";
    else if (password.length < 8) errs.password = "Şifre en az 8 karakter olmalı.";
    if (confirm !== password) errs.confirm = "Şifreler eşleşmiyor.";
    if (!terms) errs.terms = "Devam etmek için koşulları kabul etmelisiniz.";
    if (Object.keys(errs).length) { setErrors(errs); return; }
    loginMock(email.trim(), name.trim());
    onSuccess();
  };

  return (
    <div className="space-y-4">
      <GoogleButton
        label="Google ile Kayıt Ol"
        onClick={() => {
          console.log("[Auth] Google ile kayıt — OAuth henüz entegre edilmedi.");
          loginMock("google@demo.com", "Google Kullanıcısı");
          onSuccess();
        }}
      />
      <OrDivider />

      <form onSubmit={handleSubmit} noValidate className="space-y-3">
        <div>
          <FieldLabel>Ad Soyad</FieldLabel>
          <Input
            type="text"
            value={name}
            onChange={(e) => { setName(e.target.value); clear("name"); }}
            placeholder="Ahmet Yılmaz"
            className={cn(
              "h-12 rounded-2xl border-border/60 bg-background",
              errors.name && "border-destructive"
            )}
            autoComplete="name"
          />
          <FieldError msg={errors.name} />
        </div>

        <div>
          <FieldLabel>E-posta</FieldLabel>
          <Input
            type="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); clear("email"); }}
            placeholder="ornek@tarla.com"
            className={cn(
              "h-12 rounded-2xl border-border/60 bg-background",
              errors.email && "border-destructive"
            )}
            autoComplete="email"
          />
          <FieldError msg={errors.email} />
        </div>

        <div>
          <FieldLabel>Şifre</FieldLabel>
          <PasswordInput
            value={password}
            onChange={(v) => { setPassword(v); clear("password"); }}
            hasError={!!errors.password}
          />
          <FieldError msg={errors.password} />
        </div>

        <div>
          <FieldLabel>Şifre tekrar</FieldLabel>
          <PasswordInput
            value={confirm}
            onChange={(v) => { setConfirm(v); clear("confirm"); }}
            placeholder="••••••••"
            hasError={!!errors.confirm}
          />
          <FieldError msg={errors.confirm} />
        </div>

        {/* Terms checkbox */}
        <div>
          <label className="flex cursor-pointer items-start gap-2.5">
            <input
              type="checkbox"
              checked={terms}
              onChange={(e) => { setTerms(e.target.checked); clear("terms"); }}
              className="mt-0.5 h-4 w-4 rounded accent-primary cursor-pointer"
            />
            <span className="text-xs leading-relaxed text-muted-foreground">
              <span className="cursor-pointer text-primary underline-offset-2 hover:underline">
                Kullanım koşullarını
              </span>{" "}
              okudum ve kabul ediyorum.
            </span>
          </label>
          <FieldError msg={errors.terms} />
        </div>

        <Button
          type="submit"
          className="h-12 w-full rounded-2xl bg-leaf-gradient text-base font-semibold shadow-soft"
        >
          Kayıt Ol
        </Button>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------
export default function Login() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("login");
  const [animClass, setAnimClass] = useState("animate-fade-in");

  const switchTab = (next: Tab) => {
    if (next === tab) return;
    setAnimClass(next === "register" ? "animate-slide-in-right" : "animate-slide-in-left");
    setTab(next);
  };

  const onSuccess = () => navigate("/");

  return (
    <div className="flex min-h-dvh flex-col bg-earth-gradient">
      {/* Scrollable content */}
      <div className="flex flex-1 flex-col px-5 py-8 overflow-y-auto no-scrollbar">

        {/* Logo & headline */}
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-3xl bg-leaf-gradient shadow-soft">
            <Leaf className="h-7 w-7 text-primary-foreground" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            AI Plant Health
          </h1>
          <p className="mt-1 text-xs text-muted-foreground">
            Tarlanı yapay zekâ ile izle, hastalıkları erken yakala.
          </p>
        </div>

        {/* Tab switcher */}
        <div className="mb-5 flex rounded-2xl bg-card/70 p-1 shadow-card backdrop-blur">
          {(["login", "register"] as Tab[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => switchTab(t)}
              className={cn(
                "flex-1 rounded-xl py-2.5 text-sm font-semibold transition-all duration-200",
                tab === t
                  ? "bg-leaf-gradient text-primary-foreground shadow-soft"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {t === "login" ? "Giriş Yap" : "Kayıt Ol"}
            </button>
          ))}
        </div>

        {/* Card */}
        <div className="rounded-3xl bg-card/80 p-5 shadow-card backdrop-blur">
          {tab === "login" ? (
            <div key="login" className={animClass}>
              <LoginForm onSuccess={onSuccess} />
            </div>
          ) : (
            <div key="register" className={animClass}>
              <RegisterForm onSuccess={onSuccess} />
            </div>
          )}
        </div>

        <p className="mt-6 text-center text-[11px] text-muted-foreground">
          AI Plant Health System · Doğa dostu tarım için
        </p>
      </div>
    </div>
  );
}
