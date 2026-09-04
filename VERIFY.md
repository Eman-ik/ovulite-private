# Ovulite — Phase Verification Guide

> **How to use:** Follow each phase sequentially. Every step has a **command** and an **expected result**.  
> Mark each step ✓ or ✗ as you go. If any step fails, see the Troubleshooting section in [SETUP.md](SETUP.md).

**Prerequisites:** Complete [SETUP.md](SETUP.md) first — services running, admin seeded, CSV imported.

---

## Quick Token Setup (needed for all API tests)

Run this once before starting verification. All `curl` / PowerShell examples below use `$token`.

```powershell
# Get JWT token
$response = Invoke-RestMethod -Method POST -Uri http://localhost:8000/auth/token `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=admin&password=ovulite2026"

$token = $response.access_token
$headers = @{ Authorization = "Bearer $token" }
```

---

## Phase 0 — Foundation & Scaffold

**Goal:** Docker infrastructure, database schema (12 tables), auth system (JWT + RBAC), structured JSON logging

### 0.1 — Health Check

```powershell
Invoke-RestMethod -Uri http://localhost:8000/health
```

**Expected:**
```json
{ "status": "healthy", "service": "ovulite-api" }
```

### 0.2 — Database Has 12+ Tables

```powershell
# Docker setup:
docker compose exec db psql -U ovulite -d ovulite -c "\dt"

# Manual setup:
psql -U ovulite -d ovulite -c "\dt"
```

**Expected:** At least these tables:
| Table |
|-------|
| alembic_version |
| anomalies |
| donors |
| embryo_images |
| embryos |
| et_transfers |
| predictions |
| protocol_logs |
| protocols |
| recipients |
| sires |
| technicians |
| users |

### 0.3 — Swagger API Docs Load

Open in browser: **http://localhost:8000/docs**

**Expected:** Interactive Swagger UI loads with all endpoint groups: auth, donors, sires, recipients, embryos, transfers, technicians, protocols, import, predictions, grading, qc, analytics

### 0.4 — Seed Admin User

```powershell
Invoke-RestMethod -Method POST -Uri http://localhost:8000/auth/seed
```

**Expected:** Returns user object with `"username": "admin"` and `"role": "admin"`.  
*(If already seeded, returns existing admin — this is OK.)*

### 0.5 — Login Flow (JWT Token)

```powershell
$response = Invoke-RestMethod -Method POST -Uri http://localhost:8000/auth/token `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=admin&password=ovulite2026"

$response
```

**Expected:**
```json
{ "access_token": "<jwt-string>", "token_type": "bearer" }
```

### 0.6 — Protected Endpoint (GET /auth/me)

```powershell
Invoke-RestMethod -Uri http://localhost:8000/auth/me -Headers $headers
```

**Expected:** Returns the admin user profile with `username`, `role`, `full_name`.

### 0.7 — Unauthorized Access Blocked

```powershell
try {
    Invoke-RestMethod -Uri http://localhost:8000/auth/me
} catch {
    $_.Exception.Response.StatusCode.value__
}
```

**Expected:** Status `401` (Unauthorized).

### 0.8 — Structured JSON Logging

Check backend terminal output for log lines like:
```
{"timestamp": "...", "level": "INFO", "message": "GET /health → 200 (1.23ms)", "request_id": "..."}
```

**Expected:** Every request produces a structured JSON log line with `request_id`, `method`, `path`, `status_code`.

### 0.9 — X-Request-ID Header

```powershell
$resp = Invoke-WebRequest -Uri http://localhost:8000/health
$resp.Headers["X-Request-ID"]
```

**Expected:** Returns a UUID string (e.g., `a1b2c3d4-e5f6-...`).

### 0.10 — Frontend Loads

Open: **http://localhost:5173**

**Expected:** Redirects to `/login` page. Login form visible with username/password fields.

### 0.11 — Frontend Login

Enter `admin` / `ovulite2026` and click Login.

**Expected:** Redirects to Dashboard (`/`). Navigation sidebar visible with: Dashboard, Data Entry, Predictions, Embryo Grading, Lab QC, Analytics.

### 0.12 — CORS Working

After frontend login, open browser DevTools → Network tab. Check that API calls to `localhost:8000` succeed (no CORS errors).

**Expected:** No `Access-Control-Allow-Origin` errors in console.

---

## Phase 1 — Data Intake & Validation

**Goal:** Ingest 488 ET records from CSV, expose CRUD API, frontend data entry with validation

### 1.1 — CSV Import (AT-1: Data ingestion)

```powershell
# Upload the CSV file via curl
curl -X POST http://localhost:8000/import/csv `
  -H "Authorization: Bearer $token" `
  -F "file=@docs/dataset/ET Summary - ET Data.csv"
```

**Expected:** Returns import summary with counts — records created/skipped. Total should reach ~488 records across tables.

### 1.2 — Verify Record Counts

```powershell
# Check donors
(Invoke-RestMethod -Uri "http://localhost:8000/donors/?limit=1" -Headers $headers).total

# Check transfers
(Invoke-RestMethod -Uri "http://localhost:8000/transfers/?limit=1" -Headers $headers).total
```

**Expected:** 
- Donors: multiple distinct donors created
- Transfers: close to 488 transfer records

### 1.3 — Donor CRUD

```powershell
# List donors
Invoke-RestMethod -Uri "http://localhost:8000/donors/?limit=5" -Headers $headers | ConvertTo-Json -Depth 5

# Get a specific donor (use ID from list)
Invoke-RestMethod -Uri "http://localhost:8000/donors/1" -Headers $headers
```

**Expected:** Returns paginated donor list with `items`, `total`, `page`, `size` fields. Individual donor has `id`, `name`, `breed`, etc.

### 1.4 — Transfer CRUD

```powershell
# List transfers
Invoke-RestMethod -Uri "http://localhost:8000/transfers/?limit=5" -Headers $headers | ConvertTo-Json -Depth 5

# Get specific transfer
Invoke-RestMethod -Uri "http://localhost:8000/transfers/1" -Headers $headers
```

**Expected:** Returns paginated transfer list. Each transfer has `id`, `transfer_date`, `donor`, `recipient`, `sire`, `embryo`, pregnancy result fields, etc.

### 1.5 — CRUD for Other Entities

```powershell
# Sires
Invoke-RestMethod -Uri "http://localhost:8000/sires/?limit=3" -Headers $headers | ConvertTo-Json -Depth 3

# Recipients
Invoke-RestMethod -Uri "http://localhost:8000/recipients/?limit=3" -Headers $headers | ConvertTo-Json -Depth 3

# Embryos
Invoke-RestMethod -Uri "http://localhost:8000/embryos/?limit=3" -Headers $headers | ConvertTo-Json -Depth 3

# Technicians
Invoke-RestMethod -Uri "http://localhost:8000/technicians/?limit=3" -Headers $headers | ConvertTo-Json -Depth 3

# Protocols
Invoke-RestMethod -Uri "http://localhost:8000/protocols/?limit=3" -Headers $headers | ConvertTo-Json -Depth 3
```

**Expected:** All return paginated responses with populated data from the CSV import.

### 1.6 — CL Validation (AT-2: Invalid CL rejected)

```powershell
# Try to create a transfer with out-of-range CL size (> 50mm)
$invalidBody = @{
    recipient_id = 1
    donor_id = 1
    sire_id = 1
    transfer_date = "2025-01-01"
    cl_size_mm = 999
} | ConvertTo-Json

try {
    Invoke-RestMethod -Method POST -Uri "http://localhost:8000/transfers/" `
      -Headers ($headers + @{ "Content-Type" = "application/json" }) `
      -Body $invalidBody
} catch {
    $_.Exception.Response.StatusCode.value__
}
```

**Expected:** Status `422` (Validation Error) — CL value 999 rejected as out of valid range (0–50mm).

### 1.7 — Frontend: Data Entry Page

Navigate to: **http://localhost:5173/data-entry**

**Expected:**
- Paginated table showing imported ET records
- Columns visible: date, donor, recipient, sire, protocol, result, etc.
- Sortable/paginated

### 1.8 — Frontend: New Transfer Form

Navigate to: **http://localhost:5173/data-entry/new**

**Expected:**
- Form with fields: recipient, donor, sire, transfer date, CL size, protocol, etc.
- Client-side validation visible (e.g., CL must be 0–50)
- Submit creates a new record

### 1.9 — Frontend: Edit Transfer

Click on any record in the Data Entry table (or navigate to `/data-entry/1`).

**Expected:** Form pre-populated with existing record data. Can edit and save.

---

## Phase 2 — Pregnancy Prediction Pipeline

**Goal:** Train & serve pregnancy prediction model with probability, confidence interval, SHAP explanations

### 2.1 — Model Info Endpoint

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/predict/model-info" -Headers $headers
```

**Expected:** Returns model metadata: `model_type`, `version`, `features`, `metrics` (ROC-AUC, PR-AUC, Brier score). If no model trained yet, returns info about available model types.

### 2.2 — Pregnancy Prediction (AT-3: Prediction returns probability + CI + SHAP)

```powershell
$predBody = @{
    donor_id = 1
    sire_id = 1
    recipient_id = 1
    cl_size_mm = 25
    embryo_stage = "Morula"
    cl_side = "Left"
    protocol_name = "CIDR"
    semen_type = "Conventional"
    technician_name = "Dr. Ahmad"
} | ConvertTo-Json

Invoke-RestMethod -Method POST -Uri "http://localhost:8000/predict/pregnancy" `
  -Headers ($headers + @{ "Content-Type" = "application/json" }) `
  -Body $predBody
```

**Expected response contains:**
- `probability` — float between 0.0 and 1.0
- `risk_band` — "Low", "Medium", or "High"
- `confidence_interval` — object with `lower` and `upper` bounds
- `shap_values` — dictionary of feature → contribution values (AT-9: SHAP explanations)
- `model_version` — which model was used

*(If model is not yet trained, endpoint may return an error or fallback. This is OK — verify the endpoint structure works.)*

### 2.3 — SHAP Feature Contributions (AT-9)

From the prediction response above, check `shap_values`:

**Expected:** Dictionary like:
```json
{
  "cl_size_mm": 0.12,
  "embryo_stage": -0.05,
  "protocol_name": 0.08,
  ...
}
```

Each feature has a signed contribution value explaining its impact on the prediction.

### 2.4 — Confidence Interval (AT-7: Uncertainty)

From the prediction response, check `confidence_interval`:

**Expected:**
```json
{
  "lower": 0.35,
  "upper": 0.65
}
```

Interval width reflects model uncertainty. For 488-record dataset, expect relatively wide CIs.

### 2.5 — Frontend: Prediction Page

Navigate to: **http://localhost:5173/predictions**

**Expected:**
- Input form with fields matching prediction API (donor, sire, protocol, CL size, etc.)
- Submit → shows probability gauge/meter
- Risk band displayed (color-coded)
- Confidence interval visualized
- SHAP feature importance bar chart (which features help/hurt)

### 2.6 — Model Artifacts Exist

```powershell
# Check model artifact directory
Get-ChildItem -Path ml/artifacts/ -Recurse -ErrorAction SilentlyContinue | Select-Object FullName
```

**Expected:** Model files present (`.joblib`, `.json` metadata, etc.) if training has been run. Directory structure: `ml/artifacts/{version}/`.

---

## Phase 3 — Embryo Similarity Assist

**Update:** `/grade/embryo` and `/grade/embryo-with-heatmap` are back and now backed by a
real trained classifier — the 482 images turned out to be a published, openly licensed
dataset (Rocha et al. 2017) with real IETS-style grade labels; see
`docs/dataset/external/rocha2017_bovine_blastocyst/DATASET_CARD.md` and
`ml/grading/train_real_grading.py`. This section's "why not a grade classifier" reasoning
below describes why they were removed at an earlier point — it's kept for history, but the
endpoints it describes as gone are available again. Verification steps for them live in
`backend/tests/integration/test_grading_api.py`.

**Goal:** honest visual reference tool — nearest-neighbor similarity search against known
cases, built from unsupervised SimCLR pretraining on the raw images (no labels required).
This remains available as a complementary tool alongside the grade classifier above.

**Why not a grade classifier (historical):** the ET dataset is 482/488 rows = Grade 1
(near-zero variance), so there was no exploitable signal in *that* dataset to train a
Grade 1/2/3 classifier from. Earlier revisions of this document described a classifier +
Grad-CAM heatmap; that was never backed by a real trained model (its checkpoint was an
explicitly-labeled ~1.4KB placeholder) and the `/grade/embryo` / `/grade/embryo-with-heatmap`
endpoints were removed rather than continuing to serve a fabricated grade. There was no
Grad-CAM here —
there's no grade classifier left to explain.

### 3.1 — Grading Model Info

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/grade/model-info" -Headers $headers
```

**Expected:** Returns similarity-model info: backbone type (EfficientNet-B0, SimCLR
self-supervised pretraining), whether the embedding index is trained/built, and the
number of known cases in the index.

### 3.2 — Image Upload

```powershell
# Upload a test embryo image
curl -X POST http://localhost:8000/grade/upload `
  -H "Authorization: Bearer $token" `
  -F "file=@docs/Blastocystimages/Blastocyst images/blq1.jpg"
```

**Expected:** Returns `image_id` and stored file path. Image saved to uploads directory.

*(If image directory doesn't have files, use any JPG/PNG image for testing.)*

### 3.3 — Embryo Similarity Search (AT-4: Upload image → nearest known cases)

```powershell
# Find visually similar known cases
curl -X POST http://localhost:8000/grade/similar-cases `
  -H "Authorization: Bearer $token" `
  -F "image=@docs/Blastocystimages/Blastocyst images/blq1.jpg" `
  -F "k=5"
```

**Expected response contains:**
- `matches` — list of up to `k` nearest known cases, each with `rank`, `filename`,
  `similarity` (cosine similarity, not a confidence/accuracy score), and `metadata`
  (donor, breed, ET date, pregnancy outcome, etc. where linkable — may be sparse)
- `n_index_cases` — total known cases in the similarity index
- `model_type` — `simclr_efficientnet_b0`

Returns `503` if the SimCLR backbone / embedding index haven't been built yet in this
environment (run `python -m ml.grading.run_training --simclr` then
`python -m ml.grading.build_index`).

### 3.4 — Frontend: Embryo Similarity Page

Navigate to: **http://localhost:5173/embryo-grading**

**Expected:**
- Drag-and-drop or file picker for embryo image upload
- A separate "Your Assessment" panel where the embryologist can record their own manual
  grade — this is a plain human input field, not produced by or sent to the AI
- After upload → "Find Similar Cases" displays a ranked list of visually similar known
  cases with similarity scores and available historical context
- No grade, viability score, confidence percentage, or Grad-CAM heatmap is shown — this
  page does not claim to classify or predict, only to surface visual references

### 3.6 — ML Pipeline Files Exist

```powershell
# Check grading model code exists
Test-Path ml/grading/model.py
Test-Path ml/grading/dataset.py
Test-Path ml/grading/grad_cam.py
```

**Expected:** All return `True`. Core grading pipeline files present.

---

## Phase 4 — Lab QC & Anomaly Detection

**Goal:** Unsupervised monitoring of lab process health — anomaly detection, control charts, alerts

### 4.1 — Run QC Pipeline

```powershell
# Via API
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/qc/run" -Headers $headers
```

**Or via CLI:**
```powershell
cd backend
python -m ml.qc.run_pipeline --with-synthetic
```

**Expected:** Pipeline executes and returns/prints summary of anomalies detected.

### 4.2 — QC Summary

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/qc/summary" -Headers $headers | ConvertTo-Json -Depth 5
```

**Expected:** Returns QC summary with:
- `total_anomalies` — count of detected anomalies
- `anomaly_types` — breakdown by type
- `severity_distribution` — low/medium/high counts
- `last_run` — timestamp of last pipeline execution

### 4.3 — Anomaly List (AT-5: Synthetic anomalies detected)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/qc/anomalies" -Headers $headers | ConvertTo-Json -Depth 5
```

**Expected:** Returns list of anomaly records, each with:
- `id`, `anomaly_type` (e.g., "low_preg_rate", "cl_drift", "volume_spike")
- `severity` (low/medium/high)
- `description` — human-readable explanation
- `detected_at` — timestamp
- `entity_type`, `entity_id` — what triggered the anomaly

If `--with-synthetic` was used, should detect injected anomalies.

### 4.4 — Control Charts (EWMA/CUSUM)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/qc/charts" -Headers $headers | ConvertTo-Json -Depth 5
```

**Expected:** Returns control chart data with:
- `ewma` — EWMA chart points with values and control limits
- `cusum` — CUSUM chart with cumulative sum and decision boundaries
- Chart data includes `ucl` (upper control limit), `lcl` (lower control limit)

### 4.5 — Technician QC Stats

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/qc/technicians" -Headers $headers | ConvertTo-Json -Depth 5
```

**Expected:** Per-technician QC metrics (pregnancy rates, anomaly counts, performance indicators).

### 4.6 — Frontend: Lab QC Dashboard

Navigate to: **http://localhost:5173/lab-qc**

**Expected:**
- Summary cards showing total anomalies, severity breakdown
- Anomaly list/table with type, severity, description, timestamp
- Control chart visualization (EWMA/CUSUM trend lines)
- Technician performance section
- Button to trigger QC pipeline re-run

### 4.7 — QC Pipeline Artifacts

```powershell
# Check QC module exists
Test-Path ml/qc/isolation_forest.py
Test-Path ml/qc/control_charts.py
Test-Path ml/qc/synthetic.py
Test-Path ml/qc/run_pipeline.py
```

**Expected:** All return `True`.

---

## Phase 5 — Analytics Dashboard & Final Evaluation

**Goal:** Unified reproductive dashboard, protocol analytics, biomarker analysis, full system evaluation

### 5.1 — Run Analytics Pipeline

```powershell
# Via API
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/analytics/run" -Headers $headers
```

**Or via CLI:**
```powershell
cd backend
python -m ml.analytics.run_analytics
```

**Expected:** Pipeline processes all data and caches results.

### 5.2 — KPI Dashboard (AT-6: All KPIs render)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/analytics/kpis" -Headers $headers | ConvertTo-Json -Depth 5
```

**Expected:** Returns KPI metrics including:
- `total_transfers` — total ET procedures
- `pregnancy_rate` — overall success rate (with CI)
- `embryo_utilization` — embryo usage metrics
- Other reproductive KPIs

### 5.3 — Trends Analysis

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/analytics/trends" -Headers $headers | ConvertTo-Json -Depth 5
```

**Expected:** Time-series trend data — pregnancy rates over time, volume trends.

### 5.4 — IVF Funnel

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/analytics/funnel" -Headers $headers | ConvertTo-Json -Depth 5
```

**Expected:** Funnel stages: donors → embryos → transfers → pregnancies, with counts at each stage.

### 5.5 — Protocol Analysis

```powershell
# Protocol effectiveness
Invoke-RestMethod -Uri "http://localhost:8000/analytics/protocols" -Headers $headers | ConvertTo-Json -Depth 5

# Protocol regression analysis
Invoke-RestMethod -Uri "http://localhost:8000/analytics/protocols/regression" -Headers $headers | ConvertTo-Json -Depth 5

# Feature importance for protocols
Invoke-RestMethod -Uri "http://localhost:8000/analytics/protocols/importance" -Headers $headers | ConvertTo-Json -Depth 5
```

**Expected:**
- `protocols` — per-protocol pregnancy rates with confidence intervals
- `regression` — logistic regression coefficients for protocol impact
- `importance` — permutation importance scores for protocol variable

### 5.6 — Donor Analytics

```powershell
# Donor performance
Invoke-RestMethod -Uri "http://localhost:8000/analytics/donors" -Headers $headers | ConvertTo-Json -Depth 5

# Donor trends
Invoke-RestMethod -Uri "http://localhost:8000/analytics/donors/trends" -Headers $headers | ConvertTo-Json -Depth 5
```

**Expected:** Per-donor success rates, transfer counts, and trend data over time.

### 5.7 — Breed Analytics

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/analytics/breeds" -Headers $headers | ConvertTo-Json -Depth 5
```

**Expected:** Pregnancy rates broken down by breed.

### 5.8 — Biomarker Sweet-Spots (AT-6)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/analytics/biomarkers" -Headers $headers | ConvertTo-Json -Depth 5
```

**Expected:** CL size analysis with:
- Binned CL ranges and corresponding pregnancy rates
- Optimal CL range identification
- Statistical significance (Wilson CI per bin)

### 5.9 — Frontend: Analytics Page

Navigate to: **http://localhost:5173/analytics**

**Expected:**
- **KPI cards** at top (total transfers, pregnancy rate, etc.)
- **Tab navigation** with sections: Overview, Protocols, Donors, Biomarkers
- **Protocol charts** — bar chart of pregnancy rate by protocol
- **Donor performance** table/chart
- **CL biomarker** visualization — pregnancy rate vs CL size curve
- **Funnel visualization** — donors → embryos → transfers → pregnancies

### 5.10 — Documentation Files Exist

```powershell
Test-Path docs/LIMITATIONS.md
Test-Path docs/MODEL_REPORT.md
Test-Path docs/USER_GUIDE.md
```

**Expected:** All return `True`. These are the final evaluation documents:
- **LIMITATIONS.md** — What the system cannot do, confidence boundaries
- **MODEL_REPORT.md** — Comprehensive model metrics and methodology
- **USER_GUIDE.md** — System guide for veterinarians and embryologists

---

## Acceptance Test Summary (AT-1 through AT-10)

These are the formal acceptance tests from the ROADMAP verification gates:

| AT | Test | Phase | How to Verify |
|----|------|-------|---------------|
| AT-1 | All 488 ET records imported | 1 | Check transfer count ≈ 488 via `GET /transfers/?limit=1` → `total` field |
| AT-2 | Invalid CL rejected | 1 | POST transfer with `cl_size_mm: 999` → `422` error |
| AT-3 | Prediction returns P + CI + SHAP | 2 | POST `/predict/pregnancy` → response has `probability`, `confidence_interval`, `shap_values` |
| AT-4 | Upload image → similar known cases | 3 | POST `/grade/similar-cases` → response has `matches` with `similarity` scores |
| AT-5 | Synthetic anomaly detected | 4 | Run QC with `--with-synthetic` → `GET /qc/anomalies` returns flagged anomalies |
| AT-6 | Dashboard renders all KPIs | 5 | Visit `/analytics` → KPI cards, protocol charts, biomarker curves render |
| AT-7 | Uncertainty displayed | 2 | Prediction response includes `confidence_interval` with lower/upper bounds |
| AT-8 | RBAC enforced | 0 | Protected endpoints return `401` without token |
| AT-9 | SHAP explanations present | 2 | Prediction response includes `shap_values` dictionary |
| AT-10 | All endpoints documented | 0 | Swagger at `/docs` shows all 13 router groups |

---

## Full System Smoke Test (5 minutes)

A quick end-to-end run after setup:

```
1. Open http://localhost:8000/health           → {"status": "healthy"}
2. Open http://localhost:8000/docs             → Swagger loads
3. POST /auth/seed                             → Admin created
4. POST /auth/token (admin/ovulite2026)        → JWT returned
5. POST /import/csv (ET Data.csv)              → Records imported
6. GET  /transfers/?limit=1                    → total ≈ 488
7. GET  /donors/?limit=1                       → Donors populated
8. POST /predict/pregnancy ({...})             → Probability + CI + SHAP
9. POST /grade/similar-cases (image file)      → Nearest similar known cases
10. POST /qc/run                               → QC pipeline executes
11. GET  /qc/anomalies                         → Anomaly list
12. POST /analytics/run                        → Analytics pipeline executes
13. GET  /analytics/kpis                       → KPI metrics
14. Open http://localhost:5173                  → Login page
15. Login as admin/ovulite2026                 → Dashboard loads
16. Navigate: Data Entry, Predictions, Grading, Lab QC, Analytics
    → All pages render with data
```

If all 16 steps pass, the system is fully operational.
