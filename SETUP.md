# Ovulite — Setup Guide

> **Prerequisites you already have:** Git, Node.js (with npm), Python 3.11+  
> **Time to set up:** ~15–20 minutes

---

## Table of Contents

1. [Install Remaining Tools](#1-install-remaining-tools)
2. [Clone & Navigate](#2-clone--navigate)
3. [Option A: Docker Setup (Recommended)](#3-option-a-docker-setup-recommended)
4. [Option B: Manual Setup (Without Docker)](#4-option-b-manual-setup-without-docker)
5. [Seed the Database](#5-seed-the-database)
6. [Import CSV Data](#6-import-csv-data)
7. [Run ML Pipelines (Optional)](#7-run-ml-pipelines-optional)
8. [Access the Application](#8-access-the-application)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Install Remaining Tools

### PostgreSQL 15+

**Windows (choose one):**
```powershell
# Option 1: Chocolatey
choco install postgresql15

# Option 2: Download installer
# https://www.postgresql.org/download/windows/
# During install: remember the password you set for the 'postgres' user
```

**Verify:**
```powershell
psql --version
# Should show: psql (PostgreSQL) 15.x
```

### Docker & Docker Compose (for Option A only)

```powershell
# Download Docker Desktop for Windows:
# https://docs.docker.com/desktop/install/windows-install/

# Verify after install:
docker --version
docker compose version
```

> **Note:** If you prefer not to install Docker, skip to [Option B: Manual Setup](#4-option-b-manual-setup-without-docker).

---

## 2. Clone & Navigate

```powershell
git clone <your-repo-url> "Ovulite new"
cd "Ovulite new"
```

---

## 3. Option A: Docker Setup (Recommended)

This is the easiest path — one command starts everything.

### Step 1: Create .env file

```powershell
Copy-Item .env.example .env
```

The default `.env` works as-is for local development:
```dotenv
POSTGRES_USER=ovulite
POSTGRES_PASSWORD=ovulite_dev_password
POSTGRES_DB=ovulite
DATABASE_URL=postgresql://ovulite:ovulite_dev_password@db:5432/ovulite
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
VITE_API_URL=http://localhost:8000
```

### Step 2: Build & Start

```powershell
docker compose up --build
```

Wait until you see:
```
backend-1   | INFO:     Uvicorn running on http://0.0.0.0:8000
frontend-1  | VITE v8.x.x  ready in xxx ms
db-1        | LOG:  database system is ready to accept connections
```

### Step 3: Run Database Migrations

In a **new terminal**:
```powershell
docker compose exec backend alembic upgrade head
```

**Done!** Skip to [Step 5: Seed the Database](#5-seed-the-database).

---

## 4. Option B: Manual Setup (Without Docker)

### Step 1: Create PostgreSQL Database

Open a terminal (or pgAdmin):
```powershell
# Connect to PostgreSQL as superuser
psql -U postgres

# Inside psql:
CREATE USER ovulite WITH PASSWORD 'ovulite_dev_password';
CREATE DATABASE ovulite OWNER ovulite;
GRANT ALL PRIVILEGES ON DATABASE ovulite TO ovulite;
\q
```

### Step 2: Create .env file

```powershell
Copy-Item .env.example .env
```

**Edit `.env`** — change `db` to `localhost` in DATABASE_URL:
```dotenv
DATABASE_URL=postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite
```

### Step 3: Backend Setup

```powershell
cd backend

# Create virtual environment
python -m venv venv

# Activate it (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# If you get an execution policy error, run this first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
pip install -r requirements.txt
```

> **Note on PyTorch:** If `torch` installation is slow or fails, you can install CPU-only version:
> ```powershell
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
> pip install -r requirements.txt
> ```

### Step 4: Run Database Migrations

```powershell
# Still inside backend/ with venv activated
# Set the DATABASE_URL for Alembic
$env:DATABASE_URL = "postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite"

alembic upgrade head
```

You should see:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, initial schema
```

### Step 5: Start Backend Server

```powershell
# Still inside backend/ with venv activated
$env:DATABASE_URL = "postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite"
$env:SECRET_KEY = "change-me-in-production-use-openssl-rand-hex-32"

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started reloader process
```

### Step 6: Frontend Setup

Open a **new terminal**:
```powershell
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

You should see:
```
VITE v8.x.x  ready in xxx ms
➜  Local:   http://localhost:5173/
```

---

## 5. Seed the Database

Create the default admin user. In a **new terminal**:

```powershell
# Seed the admin user (one-time only)
curl -X POST http://localhost:8000/auth/seed
```

**Or using PowerShell:**
```powershell
Invoke-RestMethod -Method POST -Uri http://localhost:8000/auth/seed
```

**Expected response:**
```json
{
  "user_id": 1,
  "username": "admin",
  "role": "admin",
  "full_name": "System Administrator"
}
```

**Default admin credentials:**
- **Username:** `admin`
- **Password:** `ovulite2026`

### Verify Login

```powershell
# Get a token
$body = @{ username = "admin"; password = "ovulite2026" }
$response = Invoke-RestMethod -Method POST -Uri http://localhost:8000/auth/token `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=admin&password=ovulite2026"

$response.access_token
# Should print a JWT token string
```

---

## 6. Import CSV Data

Import the historical ET data (488 records):

```powershell
# Store the token
$token = $response.access_token

# Import the CSV file
$headers = @{ Authorization = "Bearer $token" }

# Using curl:
curl -X POST http://localhost:8000/import/csv `
  -H "Authorization: Bearer $token" `
  -F "file=@docs/dataset/ET Summary - ET Data.csv"
```

**Or using PowerShell:**
```powershell
$filePath = "docs\dataset\ET Summary - ET Data.csv"
$fileBytes = [System.IO.File]::ReadAllBytes((Resolve-Path $filePath))
$fileName = "ET Summary - ET Data.csv"

$boundary = [System.Guid]::NewGuid().ToString()
$LF = "`r`n"
$bodyLines = (
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
    "Content-Type: text/csv",
    "",
    [System.Text.Encoding]::UTF8.GetString($fileBytes),
    "--$boundary--"
) -join $LF

Invoke-RestMethod -Method POST -Uri "http://localhost:8000/import/csv" `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "multipart/form-data; boundary=$boundary" `
  -Body $bodyLines
```

---

## 7. Run ML Pipelines (Optional)

These pre-compute analytics and QC artifacts. Requires data to be imported first.

```powershell
# From project root, with venv activated and DATABASE_URL set

# Run QC anomaly detection pipeline
python -m ml.qc.run_pipeline

# Run analytics pipeline
python -m ml.analytics.run_analytics

# With synthetic anomalies for testing
python -m ml.qc.run_pipeline --with-synthetic
```

**Or via API (after login):**
```powershell
# Run QC pipeline
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/qc/run" `
  -Headers @{ Authorization = "Bearer $token" }

# Run Analytics pipeline
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/analytics/run" `
  -Headers @{ Authorization = "Bearer $token" }
```

---

## 8. Access the Application

| Service | URL | Notes |
|---------|-----|-------|
| **Frontend** | http://localhost:5173 | Main application |
| **Backend API** | http://localhost:8000 | REST API |
| **API Docs (Swagger)** | http://localhost:8000/docs | Interactive API explorer |
| **API Docs (ReDoc)** | http://localhost:8000/redoc | Alternative API docs |
| **Health Check** | http://localhost:8000/health | Should return `{"status": "healthy"}` |

### Login

1. Open http://localhost:5173
2. Enter: **admin** / **ovulite2026**
3. You should see the Dashboard

### Key Pages

| Page | Path | Description |
|------|------|-------------|
| Dashboard | `/` | System overview |
| Data Entry | `/data-entry` | View & manage ET records |
| New Transfer | `/data-entry/new` | Add new ET record |
| Predictions | `/predictions` | Pregnancy prediction |
| Embryo Grading | `/embryo-grading` | AI grade prediction (with Grad-CAM) + similarity assist (nearest known cases) + manual grade entry |
| Lab QC | `/lab-qc` | QC anomaly dashboard |
| Analytics | `/analytics` | KPIs & protocol analysis |

---

## 8.1 Production: TLS/HTTPS

The default `docker-compose.yml` above is plain HTTP, for local development only. For a production deployment, layer the TLS-termination overlay on top:

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

This adds a Caddy service that gets HTTPS automatically (Let's Encrypt for a real domain, or a local CA for `*.localhost`). Set `API_DOMAIN` / `APP_DOMAIN` in `.env` to your real domains, set `SECRET_KEY` to a real generated secret (`openssl rand -hex 32`), and remove the direct `ports:` entries for `backend`/`frontend`/`db` in `docker-compose.yml` (or firewall them) so Caddy is the only public entry point. See `deploy/Caddyfile`.

## 9. Troubleshooting

| Problem | Solution |
|---------|----------|
| `psql: command not found` | Add PostgreSQL bin to PATH: `C:\Program Files\PostgreSQL\15\bin` |
| `venv\Scripts\Activate.ps1 cannot be loaded` | Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `pip install torch` is very slow | Use CPU-only: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu` |
| `ModuleNotFoundError: No module named 'app'` | Make sure you're inside `backend/` directory when running uvicorn |
| `Connection refused` on port 5432 | Start PostgreSQL service: `net start postgresql-x64-15` |
| `alembic upgrade head` fails | Verify DATABASE_URL points to running PostgreSQL instance |
| Frontend shows "Loading..." forever | Check backend is running on port 8000 |
| `401 Unauthorized` on API calls | Token expired; re-login at `/login` |
| Docker build fails on ARM/M1 | Add `platform: linux/amd64` to services in docker-compose.yml |
| `npm install` fails | Delete `node_modules` and `package-lock.json`, then retry |
| Port 5173 already in use | Kill existing process: `Get-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess \| Stop-Process` |
| Port 8000 already in use | Kill existing process: `Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess \| Stop-Process` |

---

## Quick Reference — All Commands

```powershell
# === ONE-TIME SETUP ===
Copy-Item .env.example .env                         # Create env file
# Edit .env: change @db → @localhost for manual setup

# Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = "postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite"
alembic upgrade head

# Frontend
cd ..\frontend
npm install

# === DAILY STARTUP ===
# Terminal 1: Backend
cd backend
.\venv\Scripts\Activate.ps1
$env:DATABASE_URL = "postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite"
$env:SECRET_KEY = "change-me-in-production-use-openssl-rand-hex-32"
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# === FIRST RUN ONLY ===
# Terminal 3: Seed + Import
curl -X POST http://localhost:8000/auth/seed
# Then import CSV via Swagger UI at http://localhost:8000/docs
```
