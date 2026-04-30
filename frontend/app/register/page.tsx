"use client";
import { useState } from "react";
import { register as apiRegister, login as apiLogin } from "@/lib/api";
import { saveToken } from "@/lib/auth";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card, Button } from "@/components/ui";
import { Wind, Mail, Lock, CheckCircle2 } from "lucide-react";

function PasswordStrength({ password }: { password: string }) {
  const score = [/.{8,}/, /[A-Z]/, /[0-9]/, /[^a-zA-Z0-9]/].filter((r) => r.test(password)).length;
  const labels = ["", "Weak", "Fair", "Good", "Strong"];
  const colors = ["", "bg-danger", "bg-amber", "bg-teal/70", "bg-teal"];
  return password ? (
    <div className="mt-1.5">
      <div className="flex gap-1">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className={`h-1 flex-1 rounded-full transition-all ${score >= i ? colors[score] : "bg-white/10"}`} />
        ))}
      </div>
      <p className="text-xs text-slate mt-1">{labels[score]}</p>
    </div>
  ) : null;
}

export default function RegisterPage() {
  const router = useRouter();
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [confirm,  setConfirm]  = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) return setError("Passwords do not match");
    if (password.length < 8)  return setError("Password must be at least 8 characters");
    setLoading(true); setError("");
    try {
      await apiRegister(email, password);
      const token = await apiLogin(email, password);
      saveToken(token.access_token);
      document.cookie = `aqi_token=${token.access_token}; path=/; max-age=3600`;
      router.push("/");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Registration failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-md animate-slide-up">
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-teal/20 flex items-center justify-center mx-auto mb-4 animate-pulse-glow">
            <Wind className="w-8 h-8 text-teal" />
          </div>
          <h1 className="text-2xl font-bold text-white">Create Account</h1>
          <p className="text-slate text-sm mt-1">Join the AI Green Budget Optimizer</p>
        </div>

        <Card>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-sm text-slate mb-1.5 block">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate" />
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
                  placeholder="you@example.com"
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder:text-slate/50 text-sm focus:outline-none focus:border-teal/50 transition-all" />
              </div>
            </div>

            <div>
              <label className="text-sm text-slate mb-1.5 block">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate" />
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
                  placeholder="Min 8 characters"
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder:text-slate/50 text-sm focus:outline-none focus:border-teal/50 transition-all" />
              </div>
              <PasswordStrength password={password} />
            </div>

            <div>
              <label className="text-sm text-slate mb-1.5 block">Confirm Password</label>
              <div className="relative">
                <CheckCircle2 className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${confirm && confirm === password ? "text-teal" : "text-slate"}`} />
                <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required
                  placeholder="Repeat password"
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder:text-slate/50 text-sm focus:outline-none focus:border-teal/50 transition-all" />
              </div>
            </div>

            {error && <div className="bg-danger/10 border border-danger/20 rounded-xl px-4 py-3 text-danger text-sm">{error}</div>}

            <Button type="submit" loading={loading} className="w-full justify-center">Create Account</Button>
          </form>

          <p className="text-center text-slate text-sm mt-4">
            Already have an account?{" "}
            <Link href="/login" className="text-teal hover:underline">Sign in</Link>
          </p>
        </Card>
      </div>
    </div>
  );
}
