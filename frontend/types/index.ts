// types/index.ts — TypeScript interfaces matching FastAPI Pydantic schemas

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
  model_loaded: boolean;
  environment: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  user_id: string;
  email: string;
  created_at: string;
  is_active: boolean;
}

export interface AllocationItem {
  rank: number;
  policy: string;
  allocated_crore: number;
  aqi_improvement: number;
  efficiency: number;
  pct_of_budget: number;
}

export interface OptimizeResponse {
  total_budget_crore: number;
  total_aqi_improvement: number;
  remaining_budget: number;
  allocation: AllocationItem[];
  message: string;
}

export interface PolicySimulationResult {
  policy: string;
  description: string;
  baseline_aqi: number;
  simulated_aqi: number;
  aqi_delta: number;
  pct_improvement: number;
}

export interface SimulateAllResponse {
  results: PolicySimulationResult[];
  total_policies: number;
}

export interface PredictAqiResponse {
  city: string;
  predicted_aqi: number;
  confidence: number;
  category: "Good" | "Moderate" | "Unhealthy" | "Hazardous";
  color: string;
  prediction_id: string;
  health_advisory: string;
}

export interface HistoryResponse {
  user_id: string;
  optimizations: Array<{
    id: string;
    budget: Record<string, number>;
    aqi_improvement: number;
    created_at: string;
  }>;
  predictions: Array<{
    id: string;
    allocation: Record<string, number | string>;
    confidence: number;
    created_at: string;
  }>;
  simulations: Array<{
    id: string;
    policy_name: string;
    result_json: Record<string, number | string>;
    created_at: string;
  }>;
}

export type AqiCategory = "Good" | "Moderate" | "Unhealthy" | "Hazardous";

export const CITIES = [
  "Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata", "Hyderabad"
] as const;
export type City = typeof CITIES[number];
