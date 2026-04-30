"use client";
import { useState } from "react";
import { login as apiLogin } from "@/lib/api";
import { saveToken } from "@/lib/auth";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card, Button } from "@/components/ui";
import { Wind, Mail, Lock } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError("");
    try {
      const data = await apiLogin(email, password);
      saveToken(data.access_token);
      document.cookie = `aqi_token=${data.access_token}; path=/; max-age=3600`;
      router.push("/");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-md animate-slide-up">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-teal/20 flex items-center justify-center mx-auto mb-4 animate-pulse-glow">
            <Wind className="w-8 h-8 text-teal" />
          </div>
          <h1 className="text-2xl font-bold text-white">Welcome Back</h1>
          <p className="text-slate text-sm mt-1">Sign in to your AQI Optimizer account</p>
        </div>

        <Card>
          <form onSubmit={submit} className="space-y-4">
            {/* Email */}
            <div>
              <label className="text-sm text-slate mb-1.5 block">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate" />
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
                  placeholder="you@example.com"
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder:text-slate/50 text-sm focus:outline-none focus:border-teal/50 focus:bg-white/8 transition-all" />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="text-sm text-slate mb-1.5 block">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate" />
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
                  placeholder="••••••••"
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder:text-slate/50 text-sm focus:outline-none focus:border-teal/50 transition-all" />
              </div>
            </div>

            {error && (
              <div className="bg-danger/10 border border-danger/20 rounded-xl px-4 py-3 text-danger text-sm">{error}</div>
            )}

            <Button type="submit" loading={loading} className="w-full justify-center">
              Sign In
            </Button>
          </form>

          <p className="text-center text-slate text-sm mt-4">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-teal hover:underline">Create one</Link>
          </p>
        </Card>
      </div>
    </div>
  );
}
