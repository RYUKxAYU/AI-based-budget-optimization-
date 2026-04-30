"use client";
import { useEffect, useState } from "react";
import { getHistory } from "@/lib/api";
import { HistoryResponse } from "@/types";
import { Card, Badge, Skeleton } from "@/components/ui";
import { History, TrendingDown, Activity, Wind } from "lucide-react";

type Tab = "all" | "optimizations" | "predictions" | "simulations";

export default function HistoryPage() {
  const [data,    setData]    = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState("");
  const [tab,     setTab]     = useState<Tab>("all");

  useEffect(() => {
    getHistory()
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: "all",           label: "All",           icon: History  },
    { id: "optimizations", label: "Optimizations", icon: TrendingDown },
    { id: "predictions",   label: "Predictions",   icon: Wind     },
    { id: "simulations",   label: "Simulations",   icon: Activity },
  ];

  const formatDate = (s: string) =>
    new Date(s).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">📋 Query <span className="text-teal">History</span></h1>
        <p className="text-slate text-sm">Your recent optimizations, predictions, and simulations</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-white/5 rounded-xl w-fit">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm transition-all duration-200
              ${tab === id ? "bg-teal/20 text-teal" : "text-slate hover:text-white"}`}>
            <Icon className="w-4 h-4" />{label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <Card><Skeleton lines={6} /></Card>
      ) : error ? (
        <Card className="text-center py-8">
          <p className="text-danger text-sm">{error}</p>
          <p className="text-slate text-xs mt-2">Make sure you are logged in.</p>
        </Card>
      ) : !data ? null : (
        <div className="space-y-4">
          {/* Optimizations */}
          {(tab === "all" || tab === "optimizations") && data.optimizations.length > 0 && (
            <Card>
              <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <TrendingDown className="w-4 h-4 text-teal" /> Optimizations
              </h2>
              <div className="space-y-2">
                {data.optimizations.map((o) => (
                  <div key={o.id} className="flex items-center justify-between py-2.5 border-b border-white/5 last:border-0">
                    <div>
                      <p className="text-sm text-white">AQI Improvement: <span className="text-teal font-bold">{o.aqi_improvement?.toFixed(1) ?? "—"}</span></p>
                      <p className="text-xs text-slate">{formatDate(o.created_at)}</p>
                    </div>
                    <Badge variant="success">optimization</Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Predictions */}
          {(tab === "all" || tab === "predictions") && data.predictions.length > 0 && (
            <Card>
              <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Wind className="w-4 h-4 text-teal" /> Predictions
              </h2>
              <div className="space-y-2">
                {data.predictions.map((p) => (
                  <div key={p.id} className="flex items-center justify-between py-2.5 border-b border-white/5 last:border-0">
                    <div>
                      <p className="text-sm text-white">Confidence: <span className="text-amber font-bold">{((p.confidence ?? 0) * 100).toFixed(1)}%</span></p>
                      <p className="text-xs text-slate">{formatDate(p.created_at)}</p>
                    </div>
                    <Badge variant="info">prediction</Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Empty state */}
          {(tab === "all" && data.optimizations.length === 0 && data.predictions.length === 0) && (
            <Card className="text-center py-12">
              <History className="w-12 h-12 text-teal/20 mx-auto mb-4" />
              <p className="text-slate text-sm">No history yet.</p>
              <p className="text-slate/60 text-xs mt-1">Run an optimization or prediction to get started.</p>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
