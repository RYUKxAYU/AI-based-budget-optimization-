# AQI Green Budget Optimizer — Agent Build Prompt

## Project State (Global Context)
```
Stack:        FastAPI + PostgreSQL (Alembic, 5 tables) + Docker Compose (7 services)
Frontend:     Next.js 14 (App Router) + Tailwind CSS
Auth:         JWT (keys in .env: JWT_PRIVATE_KEY, JWT_PUBLIC_KEY) — no endpoints yet
Deploy:       Vercel (frontend) + Railway/Render (backend)
API ready:    GET /health, POST /optimize, POST /simulate
API missing:  POST /register, POST /login, GET /me, POST /predict/aqi, POST /admin/train
DB tables:    users, predictions, optimizations, simulations, training_jobs
Model path:   green_budget_optimizer/outputs/aqi_forest_model.pkl
.env bug:     MODEL_PATH=services/model-service/models/aqj_forest_model.pkl (wrong)
```
Refer to existing files for schemas, configs, and imports. No placeholders. Complete code only.

---

## STEP 1 — Fix MODEL_PATH + Health Check
```
TASK:
1. Fix: MODEL_PATH → green_budget_optimizer/outputs/aqi_forest_model.pkl
2. Write scripts/verify_backend.py:
   - Load .env via python-dotenv
   - Check MODEL_PATH exists on disk
   - Ping GET /health (localhost:8000)
   - Print pass/fail per check
```

---

## STEP 2 — Auth Endpoints
```
TASK: Write routers/auth.py + register in main.py

POST /register
  In:  {email, password} | Validate: RFC email, len>=8 | Hash: bcrypt | Save: users table
  Out: {message, user_id} | Errors: 400 duplicate email

POST /login
  In:  {email, password} | Verify bcrypt | Sign JWT: {sub: user_id, email, exp: +3600}
  Out: {access_token, token_type:"bearer", expires_in:3600} | Errors: 401 bad creds

GET /me
  Auth: Bearer token required
  Out: {user_id, email, created_at, is_active}

ALSO: Export get_current_user() dependency for use in other routes
DEPS: python-jose, passlib[bcrypt]
```

---

## STEP 3 — DB Writes + /predict/aqi
```
TASK:

POST /optimize (existing route — add DB write):
  After ML result → INSERT into optimizations(user_id nullable, budget, allocation_json, expected_aqi_reduction)
  Response: add optimization_id field

POST /simulate (existing route — add DB write):
  After result → INSERT into simulations(user_id nullable, policy_name, scenario_json, result_json)
  Response: add simulation_id field

POST /predict/aqi (implement missing route):
  In:  {city:str, date?:str}
  Load model from MODEL_PATH | Run inference
  Out: {city, predicted_aqi, confidence, category:"Good"|"Moderate"|"Unhealthy"|"Hazardous"}
  Write: INSERT into predictions(user_id nullable, city, aqi_value, predicted_at, model_version)

GET /history (new, auth required):
  Out: {optimizations:[last 20], simulations:[last 20], predictions:[last 20]} for current user
```

---

## STEP 4 — Training Trigger
```
TASK:

Alembic migration:
  - users: ADD COLUMN is_admin BOOLEAN DEFAULT false
  - CREATE TABLE training_jobs(id UUID PK, status, started_at, finished_at, metrics_json, error)

POST /admin/train (admin JWT required):
  - BackgroundTask: run training pipeline, update training_jobs row on finish/fail
  - Immediate out: {message:"Training started", job_id}

GET /admin/train/{job_id}:
  Out: {job_id, status, started_at, finished_at, metrics_json, error}
```

---

## STEP 5 — Security Hardening
```
TASK: Update main.py

CORS:
  allow_origins = ALLOWED_ORIGINS env var (comma-split) | fallback: ["http://localhost:3000"]

Security headers middleware (add all):
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  X-XSS-Protection: 1; mode=block

Rate limits via slowapi:
  POST /login       → 5/min per IP
  POST /register    → 3/min per IP
  POST /optimize    → 20/min per user
  POST /predict/aqi → 30/min per user

Add to .env.example: ALLOWED_ORIGINS=https://myapp.vercel.app
```

---

## STEP 6 — Next.js Project Scaffold + API Client
```
TASK: Scaffold Next.js 14 App Router project

Directory structure:
  app/ → layout.tsx, page.tsx, optimize/, simulate/, predict/, login/, register/, history/
  components/ → ui/, charts/, layout/
  lib/ → api.ts, auth.ts, hooks/useAuth.ts
  types/ → index.ts
  middleware.ts

lib/api.ts:
  Base: NEXT_PUBLIC_API_URL env var
  Typed functions: login, register, getMe, optimize, simulate, predictAqi, getHistory
  Auto-attach: Bearer token from localStorage
  On 401: redirect to /login

lib/auth.ts:
  saveToken(t), getToken(), removeToken(), isLoggedIn(), decodeToken()

types/index.ts:
  TypeScript interfaces matching all FastAPI Pydantic response schemas

tailwind.config.ts — custom theme:
  navy:#0F1929, teal:#00D4AA, amber:#F59E0B, danger:#EF4444, slate:#94A3B8
  Dark mode default. CSS variables for all colors.

middleware.ts:
  /history → redirect /login if no token
  /login,/register → redirect / if token exists
```

---

## STEP 7 — Dashboard Page (/)
```
TASK: Build app/page.tsx. Refer to lib/api.ts for data-fetching, types/index.ts for types.

Sections:
1. Stats bar (4 cards): Current AQI | Budget Utilized | Simulations Run | Model Status badge
2. AQI Trend Chart: Recharts LineChart, 7-day data, teal gradient fill, animated on load
3. Recent Activity: last 5 /history entries — icon + type + timestamp + summary
4. Quick Actions: 3 buttons → /optimize, /simulate, /predict
5. City AQI Grid: 6 cities (Delhi, Mumbai, Bangalore, Chennai, Kolkata, Hyderabad)
   - Parallel POST /predict/aqi for all 6 | color-coded AQI + category badge

UI rules:
  - Background: #0F1929 | Glassmorphism cards (backdrop-blur, border-opacity)
  - Staggered fade-in on load | Skeleton loaders while fetching | Fully responsive
```

---

## STEP 8 — Optimize Page (/optimize)
```
TASK: Build app/optimize/page.tsx. Refer to lib/api.ts → optimize().

Layout: two-column desktop / stacked mobile

Left panel (inputs):
  - Budget slider: ₹1L–₹100Cr, formatted labels
  - City dropdown: 6 metros
  - Constraint toggles: min % per category (Transport, Industry, Residential, Agriculture)
  - Submit button with loading state

Right panel (results, shown after API response):
  - Recharts PieChart: allocation breakdown, labeled slices
  - Expected AQI reduction: animated count-up number
  - Allocation table: Category | Amount (₹) | % Budget | Impact
  - Buttons: "Save to History" | "Export PDF" (window.print)
```

---

## STEP 9 — Simulate + Predict Pages
```
TASK:

app/simulate/page.tsx — refer to lib/api.ts → simulate()
  - Policy card grid: EV Transition | Industrial Regulation | Green Zones | Crop Burning Ban
  - Inputs: city + duration (months)
  - Results: before/after AQI (animated) | 12-month LineChart | reduction % progress bar

app/predict/page.tsx — refer to lib/api.ts → predictAqi()
  - City selector: button grid (6 metros)
  - Optional date picker (default today)
  - Result card: big AQI number (green<50, yellow<100, orange<150, red 150+)
    + category + confidence bar + health advisory tooltip
  - "Predict All Cities" → comparison table
```

---

## STEP 10 — Auth Pages + Navbar
```
TASK:

app/login/page.tsx:
  Fields: email, password | Loading + error states | Link to /register | On success: save token → /

app/register/page.tsx:
  Fields: email, password, confirm password
  Inline validation: RFC email | match | len>=8 | password strength indicator
  On success: auto-login → /

components/layout/Navbar.tsx:
  Links: Dashboard | Optimize | Simulate | Predict
  Unauthed: Login button | Authed: avatar dropdown (History, Logout)
  Mobile: hamburger menu

lib/hooks/useAuth.ts:
  { user, isLoading, login(), logout(), register() }
  Auto-fetch GET /me on mount if token present
```

---

## STEP 11 — History Page + UI Primitives
```
TASK:

app/history/page.tsx (auth-protected):
  Tabs: All | Optimizations | Simulations | Predictions
  Table per tab: timestamp | city | key metric | status badge | expandable JSON row
  Empty state + CTA | Pagination: 20/page

Per-route files (add to every app/ route dir):
  loading.tsx → skeleton | error.tsx → error boundary | not-found.tsx → global 404

components/ui/ — build these primitives:
  Badge        → variant: success|warning|danger|info
  Card         → prop: glass:boolean (glassmorphism)
  Skeleton     → prop: lines:number
  Button       → variant: primary|ghost|danger, prop: loading:boolean
  AqiIndicator → prop: value:number → colored circle + category label
```

---

## STEP 12 — Deployment Config
```
TASK:

Dockerfile.prod (multi-stage):
  Stage 1: pip install deps | Stage 2: copy app, CMD uvicorn --workers 2 --port 8000

railway.json:
  build.builder: DOCKERFILE | build.dockerfilePath: Dockerfile.prod
  deploy.healthcheckPath: /health

vercel.json:
  framework: nextjs
  rewrites: /api/:path* → BACKEND_URL/:path* (avoids CORS in prod)

Required env vars:
  Railway:  DATABASE_URL, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY, MODEL_PATH,
            ALLOWED_ORIGINS, SECRET_KEY, ENVIRONMENT=production
  Vercel:   NEXT_PUBLIC_API_URL, NEXT_PUBLIC_APP_NAME

.github/workflows/deploy.yml — on push to main:
  jobs: run pytest → next build → vercel --prod (via Vercel CLI + VERCEL_TOKEN secret)
```
