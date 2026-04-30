// components/ui/index.tsx — reusable primitives

import { Loader2 } from "lucide-react";

// ── Badge ─────────────────────────────────────────────────────────────────────
type BadgeVariant = "success" | "warning" | "danger" | "info";
const BADGE_STYLES: Record<BadgeVariant, string> = {
  success: "bg-teal/20 text-teal border-teal/30",
  warning: "bg-amber/20 text-amber border-amber/30",
  danger:  "bg-danger/20 text-danger border-danger/30",
  info:    "bg-blue-500/20 text-blue-400 border-blue-400/30",
};
export function Badge({ variant = "info", children }: { variant?: BadgeVariant; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${BADGE_STYLES[variant]}`}>
      {children}
    </span>
  );
}

// ── Card ──────────────────────────────────────────────────────────────────────
export function Card({ glass = true, children, className = "" }: {
  glass?: boolean; children: React.ReactNode; className?: string;
}) {
  return (
    <div className={`${glass ? "glass" : "bg-slate-800 rounded-2xl"} p-6 ${className}`}>
      {children}
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="animate-pulse space-y-3">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={`h-4 bg-white/10 rounded ${i % 3 === 2 ? "w-2/3" : "w-full"}`} />
      ))}
    </div>
  );
}

// ── Button ────────────────────────────────────────────────────────────────────
type ButtonVariant = "primary" | "ghost" | "danger";
const BTN_STYLES: Record<ButtonVariant, string> = {
  primary: "btn-primary",
  ghost:   "btn-ghost",
  danger:  "border border-danger/40 text-danger px-6 py-2.5 rounded-xl hover:bg-danger/10 transition-all",
};
export function Button({
  variant = "primary", loading = false, children, className = "", ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; loading?: boolean }) {
  return (
    <button className={`${BTN_STYLES[variant]} ${className} disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2`}
      disabled={loading || props.disabled} {...props}>
      {loading && <Loader2 className="w-4 h-4 animate-spin" />}
      {children}
    </button>
  );
}

// ── AQI Indicator ─────────────────────────────────────────────────────────────
const AQI_CONFIG = {
  Good:      { color: "#00C851", bg: "rgba(0,200,81,0.15)" },
  Moderate:  { color: "#FFD700", bg: "rgba(255,215,0,0.15)" },
  Unhealthy: { color: "#FF8C00", bg: "rgba(255,140,0,0.15)" },
  Hazardous: { color: "#DC143C", bg: "rgba(220,20,60,0.15)" },
};
export function AqiIndicator({ value }: { value: number }) {
  const category =
    value < 50 ? "Good" : value < 100 ? "Moderate" : value < 150 ? "Unhealthy" : "Hazardous";
  const { color, bg } = AQI_CONFIG[category];
  return (
    <div className="flex items-center gap-3">
      <div className="w-12 h-12 rounded-full flex items-center justify-center font-bold text-sm"
        style={{ background: bg, border: `2px solid ${color}`, color }}>
        {Math.round(value)}
      </div>
      <div>
        <p className="font-semibold text-white">{Math.round(value)} AQI</p>
        <p className="text-xs" style={{ color }}>{category}</p>
      </div>
    </div>
  );
}
