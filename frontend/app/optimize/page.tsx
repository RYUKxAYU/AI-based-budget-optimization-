"use client";
import { useState } from "react";
import { optimize } from "@/lib/api";
import { OptimizeResponse } from "@/types";
import { Card, Button, Badge } from "@/components/ui";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Brain, DollarSign, TrendingDown, Printer } from "lucide-react";

const COLORS = ["#00D4AA","#F59E0B","#6366F1","#EC4899","#0EA5E9","#14B8A6"];

export default function OptimizePage() {
  const [budget,   setBudget]   = useState(1000);
  const [intensity, setIntensity] = useState(1.0);
  const [result,   setResult]   = useState<OptimizeResponse | null>(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  const run = async () => {
    setLoading(true); setError(""); setResult(null);
    try {
      const data = await optimize(budget, intensity);
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Optimization failed");
    } finally {
      setLoading(false);
    }
  };

  const pieData = result?.allocation.map((a) => ({
    name: a.policy.replace(/_/g, " "),
    value: Math.round(a.allocated_crore),
  })) ?? [];

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">
          🧠 Budget <span className="text-teal">Optimizer</span>
        </h1>
        <p className="text-slate text-sm">AI-driven greedy allocation to maximize AQI improvement</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left — Controls */}
        <Card>
          <h2 className="text-lg font-semibold text-white mb-6">Configure Budget</h2>

          <div className="space-y-6">
            {/* Budget Slider */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm text-slate font-medium">Total Budget</label>
                <span className="text-teal font-bold">₹{budget.toLocaleString()} Crore</span>
              </div>
              <input type="range" min="100" max="10000" step="100" value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                className="w-full h-2 bg-white/10 rounded-full appearance-none cursor-pointer accent-teal" />
              <div className="flex justify-between text-xs text-slate mt-1">
                <span>₹100 Cr</span><span>₹10,000 Cr</span>
              </div>
            </div>

            {/* Intensity */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm text-slate font-medium">Policy Intensity</label>
                <span className="text-amber font-bold">{(intensity * 100).toFixed(0)}%</span>
              </div>
              <input type="range" min="0.1" max="1" step="0.1" value={intensity}
                onChange={(e) => setIntensity(Number(e.target.value))}
                className="w-full h-2 bg-white/10 rounded-full appearance-none cursor-pointer accent-amber" />
              <div className="flex justify-between text-xs text-slate mt-1">
                <span>Minimal</span><span>Full Impact</span>
              </div>
            </div>

            {error && <p className="text-danger text-sm bg-danger/10 border border-danger/20 rounded-lg px-4 py-3">{error}</p>}

            <Button onClick={run} loading={loading} className="w-full justify-center">
              <Brain className="w-4 h-4" /> Run Optimization
            </Button>
          </div>
        </Card>

        {/* Right — Results */}
        <div className="space-y-4">
          {result ? (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-2 gap-3">
                <Card className="text-center">
                  <TrendingDown className="w-6 h-6 text-teal mx-auto mb-2" />
                  <p className="text-2xl font-bold text-teal">{result.total_aqi_improvement.toFixed(1)}</p>
                  <p className="text-xs text-slate mt-1">AQI Reduction</p>
                </Card>
                <Card className="text-center">
                  <DollarSign className="w-6 h-6 text-amber mx-auto mb-2" />
                  <p className="text-2xl font-bold text-amber">₹{result.remaining_budget.toFixed(0)}Cr</p>
                  <p className="text-xs text-slate mt-1">Remaining Budget</p>
                </Card>
              </div>

              {/* Pie Chart */}
              <Card>
                <h3 className="text-sm font-semibold text-white mb-4">Allocation Breakdown</h3>
                <div className="h-52">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" label={({ name, percent }) => `${((percent || 0) * 100).toFixed(0)}%`} labelLine={false}>
                        {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip contentStyle={{ background: "#0F1929", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#e2e8f0" }} />
                      <Legend wrapperStyle={{ fontSize: "11px", color: "#94A3B8" }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              {/* Allocation Table */}
              <Card>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-white">Allocation Details</h3>
                  <button onClick={() => window.print()} className="flex items-center gap-1 text-xs text-slate hover:text-teal transition-colors">
                    <Printer className="w-3.5 h-3.5" /> Export
                  </button>
                </div>
                <div className="space-y-2">
                  {result.allocation.map((a, i) => (
                    <div key={i} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                        <span className="text-sm text-white">{a.policy.replace(/_/g, " ")}</span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate">
                        <span className="text-teal font-medium">₹{a.allocated_crore.toFixed(0)}Cr</span>
                        <span>↓{a.aqi_improvement.toFixed(1)} AQI</span>
                        <Badge variant="success">{a.pct_of_budget.toFixed(1)}%</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </>
          ) : (
            <Card className="flex flex-col items-center justify-center min-h-[300px] text-center">
              <Brain className="w-12 h-12 text-teal/30 mb-4" />
              <p className="text-slate text-sm">Configure your budget and click<br /><span className="text-teal">Run Optimization</span> to see results</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
