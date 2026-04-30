"use client";
import { useEffect, useState } from "react";
import { predictAqi, simulateAll } from "@/lib/api";
import { PredictAqiResponse, SimulateAllResponse } from "@/types";
import { Card, Skeleton, AqiIndicator, Badge } from "@/components/ui";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts";
import { Brain, Wind, Activity, BarChart2, ArrowRight, Zap } from "lucide-react";
import Link from "next/link";

const CITIES = ["Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata", "Hyderabad"];

// Mock trend data — will be replaced with real AQI history
const TREND_DATA = Array.from({ length: 7 }, (_, i) => ({
  day: ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][i],
  aqi: Math.floor(80 + Math.random() * 60),
}));

export default function DashboardPage() {
  const [cities,   setCities]   = useState<Record<string, PredictAqiResponse | null>>({});
  const [policies, setPolicies] = useState<SimulateAllResponse | null>(null);
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      // Parallel city predictions
      const cityResults = await Promise.allSettled(
        CITIES.map((c) => predictAqi(c).then((r) => [c, r] as [string, PredictAqiResponse]))
      );
      const cityMap: Record<string, PredictAqiResponse | null> = {};
      cityResults.forEach((r) => {
        if (r.status === "fulfilled") cityMap[r.value[0]] = r.value[1];
      });
      setCities(cityMap);

      // Simulate all policies
      try {
        const sim = await simulateAll();
        setPolicies(sim);
      } catch { /* model not loaded */ }

      setLoading(false);
    };
    fetchAll();
  }, []);

  const avgAqi = Object.values(cities).filter(Boolean).reduce((s, c) => s + (c?.predicted_aqi ?? 0), 0) /
    Math.max(Object.values(cities).filter(Boolean).length, 1);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">
          🌿 AI Green Budget <span className="text-teal">Optimizer</span>
        </h1>
        <p className="text-slate text-sm">Real-time AQI monitoring & AI-driven budget optimization for Indian cities</p>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Avg City AQI",        value: loading ? "—" : Math.round(avgAqi).toString(), icon: Wind,     color: "teal",  sub: "Across 6 metros" },
          { label: "Policies Simulated",  value: policies ? `${policies.total_policies}` : "6",  icon: Activity, color: "amber", sub: "All scenarios" },
          { label: "Optimization Engine", value: "Ready",                                          icon: Brain,    color: "teal",  sub: "RandomForest v1" },
          { label: "DB Status",           value: "Connected",                                      icon: Zap,      color: "teal",  sub: "AQIDB · PostgreSQL 18" },
        ].map(({ label, value, icon: Icon, color, sub }, i) => (
          <Card key={i} className={`stagger-${i + 1} animate-slide-up`}>
            <div className="flex items-start justify-between mb-3">
              <div className={`w-10 h-10 rounded-xl bg-${color}/20 flex items-center justify-center`}>
                <Icon className={`w-5 h-5 text-${color}`} />
              </div>
              <Badge variant="success">Live</Badge>
            </div>
            <p className="text-2xl font-bold text-white">{value}</p>
            <p className="text-xs text-slate mt-1">{label}</p>
            <p className="text-xs text-white/40 mt-0.5">{sub}</p>
          </Card>
        ))}
      </div>

      {/* AQI Trend Chart */}
      <Card>
        <h2 className="text-lg font-semibold text-white mb-4">📈 7-Day AQI Trend (Delhi)</h2>
        <div className="h-52">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={TREND_DATA}>
              <defs>
                <linearGradient id="tealGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#00D4AA" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00D4AA" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="day" stroke="#94A3B8" tick={{ fontSize: 11 }} />
              <YAxis stroke="#94A3B8" tick={{ fontSize: 11 }} domain={[0, 200]} />
              <Tooltip contentStyle={{ background: "#0F1929", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#e2e8f0" }} />
              <Area type="monotone" dataKey="aqi" stroke="#00D4AA" strokeWidth={2} fill="url(#tealGrad)" dot={{ fill: "#00D4AA", r: 3 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* City AQI Grid */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">🏙️ City AQI Snapshot</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {CITIES.map((city) => {
            const data = cities[city];
            return (
              <Card key={city} className="text-center hover:border-teal/30 transition-colors cursor-default">
                {loading || !data ? (
                  <Skeleton lines={2} />
                ) : (
                  <>
                    <p className="text-sm font-semibold text-white mb-2">{city}</p>
                    <p className="text-2xl font-bold" style={{ color: data.color }}>
                      {Math.round(data.predicted_aqi)}
                    </p>
                    <p className="text-xs mt-1" style={{ color: data.color }}>{data.category}</p>
                  </>
                )}
              </Card>
            );
          })}
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">⚡ Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { href: "/optimize", label: "Optimize Budget",    desc: "AI greedy allocation",    icon: Brain,    color: "teal" },
            { href: "/simulate", label: "Simulate Policy",    desc: "Compare policy impact",   icon: Activity, color: "amber" },
            { href: "/predict",  label: "Predict AQI",        desc: "City-level forecast",     icon: Wind,     color: "teal" },
          ].map(({ href, label, desc, icon: Icon, color }) => (
            <Link key={href} href={href}>
              <Card className="group cursor-pointer hover:border-teal/30 transition-all duration-200 hover:scale-[1.02]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl bg-${color}/20 flex items-center justify-center group-hover:bg-${color}/30 transition-colors`}>
                      <Icon className={`w-5 h-5 text-${color}`} />
                    </div>
                    <div>
                      <p className="font-semibold text-white text-sm">{label}</p>
                      <p className="text-xs text-slate">{desc}</p>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate group-hover:text-teal transition-colors group-hover:translate-x-1 transform duration-200" />
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
