"use client";
import { useState } from "react";
import { predictAqi } from "@/lib/api";
import { PredictAqiResponse } from "@/types";
import { Card, Button, AqiIndicator } from "@/components/ui";
import { Wind } from "lucide-react";

const CITIES = ["Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata", "Hyderabad"];

export default function PredictPage() {
  const [selected, setSelected] = useState<string | null>(null);
  const [result,   setResult]   = useState<PredictAqiResponse | null>(null);
  const [allResults, setAllResults] = useState<PredictAqiResponse[]>([]);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  const predict = async (city: string) => {
    setSelected(city); setLoading(true); setError(""); setResult(null); setAllResults([]);
    try { setResult(await predictAqi(city)); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setLoading(false); }
  };

  const predictAllCities = async () => {
    setLoading(true); setError(""); setResult(null); setSelected(null);
    try {
      const res = await Promise.all(CITIES.map((c) => predictAqi(c)));
      setAllResults(res);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">🌬️ AQI <span className="text-teal">Predictor</span></h1>
        <p className="text-slate text-sm">ML-powered air quality forecasting for Indian metros</p>
      </div>

      {/* City selector */}
      <Card>
        <h2 className="text-base font-semibold text-white mb-4">Select City</h2>
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-4">
          {CITIES.map((city) => (
            <button key={city} onClick={() => predict(city)}
              className={`py-2.5 px-2 rounded-xl text-sm font-medium transition-all duration-200 hover:scale-105
                ${selected === city ? "bg-teal/20 text-teal border border-teal/40" : "bg-white/5 text-slate hover:text-white border border-white/10 hover:border-white/20"}`}>
              {city}
            </button>
          ))}
        </div>
        <div className="flex gap-2 items-center">
          <Button onClick={predictAllCities} loading={loading && !selected} variant="ghost" className="text-sm">
            <Wind className="w-4 h-4" /> Predict All Cities
          </Button>
        </div>
        {error && <p className="text-danger text-sm mt-3">{error}</p>}
      </Card>

      {/* Single city result */}
      {result && (
        <Card className="animate-slide-up">
          <h2 className="text-lg font-semibold text-white mb-4">{result.city} — AQI Forecast</h2>
          <div className="flex items-center gap-6 mb-4">
            <div className="w-24 h-24 rounded-full flex items-center justify-center text-3xl font-bold border-4"
              style={{ borderColor: result.color, color: result.color, background: `${result.color}15` }}>
              {Math.round(result.predicted_aqi)}
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{result.category}</p>
              <p className="text-slate text-sm mt-1">Confidence: {(result.confidence * 100).toFixed(1)}%</p>
              <div className="w-40 h-2 bg-white/10 rounded-full mt-2">
                <div className="h-2 rounded-full bg-teal transition-all" style={{ width: `${result.confidence * 100}%` }} />
              </div>
            </div>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <p className="text-xs text-slate font-medium mb-1">Health Advisory</p>
            <p className="text-sm text-white">{result.health_advisory}</p>
          </div>
        </Card>
      )}

      {/* All cities comparison */}
      {allResults.length > 0 && (
        <Card className="animate-slide-up">
          <h2 className="text-lg font-semibold text-white mb-4">🏙️ All Cities Comparison</h2>
          <div className="space-y-3">
            {allResults.sort((a, b) => b.predicted_aqi - a.predicted_aqi).map((r) => (
              <div key={r.city} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                <span className="text-sm text-white w-24">{r.city}</span>
                <div className="flex-1 mx-4">
                  <div className="h-2 bg-white/10 rounded-full">
                    <div className="h-2 rounded-full transition-all" style={{ width: `${(r.predicted_aqi / 200) * 100}%`, background: r.color }} />
                  </div>
                </div>
                <AqiIndicator value={r.predicted_aqi} />
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
