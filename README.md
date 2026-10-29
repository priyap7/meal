# Food AI Intelligence

Uncertainty-aware food photo analysis and meal tracking. This is a local-first starter implementation; configure a vision API before image analysis can run. It does not ship fake analysis or sample meal activity.

## Stack
- Frontend: React + TypeScript + Vite
- Backend: FastAPI + Pydantic + SQLAlchemy + SQLite
- AI: OpenAI-compatible vision endpoint (server-side only)
- Nutrition: bundled starter reference data clearly marked as such; optional USDA FoodData Central integration via API key. Import/licensing review is required before distributing IFCT data.

## Requirements
- Node.js 20+
- Python 3.11+

## Run on Windows
### 1. Backend
```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and add your API key/model if you want AI image analysis
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (new terminal)
```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```
Open the URL Vite prints, usually http://localhost:5173. API docs: http://localhost:8000/docs.

## Environment
- `OPENAI_API_KEY`: optional until image analysis/chat is used.
- `OPENAI_BASE_URL`: optional OpenAI-compatible base URL.
- `VISION_MODEL`: vision-capable model name supported by your provider.
- `USDA_API_KEY`: optional FoodData Central API key.
- Never put backend secrets in `frontend/.env`.

## Current behavior and limits
- Dashboard and all nine pages are independently navigable.
- Meals, goals and settings persist in SQLite.
- Image analysis sends the actual uploaded bytes to the configured vision model. When no API is configured, it returns a clear 503 instead of guessing.
- The bundled nutrition table is a small, transparent starter reference table, not a complete IFCT/USDA import. Unknown foods are not assigned invented nutrition values.
- Photo portion estimates are uncertain; users should review portions and preparation details before saving.
- Voice uses browser speech recognition when supported, with typed input fallback.
- Knowledge graph is generated from configured nutrition reference records and saved goals/meals, not random demo nodes.

## Tests
```powershell
cd backend
.venv\Scripts\Activate.ps1
pytest -q
```

## Production checklist
Use managed PostgreSQL, authentication/authorization if multiple users are introduced, object storage with malware scanning, rate limiting, HTTPS, secret management, migrations, audit/retention policy, and provider-specific privacy review before public deployment. Do not use this application for medical diagnosis.
