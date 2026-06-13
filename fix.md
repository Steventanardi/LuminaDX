# LuminaDx — Directory Audit (2026-06-10)

Full review of the repo: what to **fix** (broken/wrong), what to **add** (missing), and what to **improve** (works, but could be better). Each item says how to do it.

---

## 1. FIX — broken or wrong today

### 1.1 Junk files from botched shell commands
Zero-byte garbage sitting in the tree (gitignored, but still on disk):

- `'` (root, 0 bytes)
- `handleCancerTypeChange(ct)},` (root)
- `model` (root, 0 bytes)
- `backend/{ct` (0 bytes)

**How:** from the repo root in PowerShell:
```powershell
Remove-Item -LiteralPath "'", 'handleCancerTypeChange(ct)},', 'model', 'backend\{ct' -Force
```
(`-LiteralPath` is required — the brace/quote names break normal globbing.)

### 1.2 `start_backend.ps1` points at the old project
`start_backend.ps1:1` is `Set-Location "D:\Steven Project\Liver Cancer\backend"` — the **old repo path**. Anyone using this script starts the old backend, not LuminaDx.

**How:** replace the file contents with:
```powershell
Set-Location "$PSScriptRoot\backend"
.\.venv\Scripts\uvicorn main:app --reload --port 8000
```

### 1.3 JWT secret is the hard-coded default
`backend/config.py:33` ships `auth_secret_key: str = "change-me-in-production-use-AUTH_SECRET_KEY-env-var"` and there is **no `backend/.env`** — so the app is actually signing tokens with the public default. Anyone who reads the repo can forge an admin token.

**How (two parts):**
1. Create `backend/.env` (already gitignored):
   ```
   AUTH_SECRET_KEY=<output of: python -c "import secrets; print(secrets.token_urlsafe(48))">
   ```
2. Make the default fail loudly — in `config.py` after `settings = Settings()`:
   ```python
   if not settings.debug and settings.auth_secret_key.startswith("change-me"):
       raise RuntimeError("Set AUTH_SECRET_KEY in backend/.env before running")
   ```

### 1.4 Deprecated `datetime.utcnow()`
`backend/models/schemas.py` (`default_factory=datetime.utcnow`) and `backend/api/routes/auth.py:107` (`user.last_login = datetime.utcnow()`). Deprecated since Python 3.12 and produces naive timestamps.

**How:** use timezone-aware UTC:
```python
from datetime import datetime, timezone
# schemas.py
generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
# auth.py
user.last_login = datetime.now(timezone.utc)
```
(`auth_utils.py` already does this correctly — copy its style.)

### 1.5 Uncommitted feature work
The whole per-cancer model-picker feature (8 modified files + new `backend/core/model_catalog.py`) is sitting unstaged. Verified working (backend imports OK, `tsc --noEmit` clean) — it just needs committing before it gets tangled with other changes.

**How:**
```powershell
git add backend/core/model_catalog.py backend/api/routes/analysis.py backend/core/llm_client.py backend/models/schemas.py frontend/src
git commit -m "feat: per-cancer LLM model picker with comparison support"
```

### 1.6 Stale "Liver Cancer" branding in configs
- `frontend/package.json:2` — `"name": "liver-cancer-ai-v2"`, version `0.1.0` (backend says `0.2.0`)
- `backend/config.py:6` — `app_name: str = "Liver Cancer AI Diagnostics"`
- `Launch.bat:2` — `title Liver Cancer AI - Launcher`

**How:** rename to `luminadx-frontend` / `LuminaDx — Multi-Cancer AI Diagnostics` / `title LuminaDx - Launcher`, and bump package.json to `0.2.0` so the two halves agree.

---

## 2. ADD — missing entirely

### 2.1 Tests (the biggest gap — there are zero)
No `backend/tests/`, no pytest in requirements, no test script in package.json. The pure-logic modules are easy wins and matter for a thesis (you can cite test coverage).

**How (backend):**
1. `pip install pytest pytest-asyncio httpx` (add `pytest>=8.0` to a new `requirements-dev.txt`).
2. Create `backend/tests/` and start with the logic that has no heavy deps:
   - `test_model_catalog.py` — `resolve()` falls back on bad model, `catalog()` covers all 5 cancers, default is first option.
   - `test_auth_utils.py` — hash/verify roundtrip, expired-token returns `None`.
   - `test_deps.py` — `can_view`/`can_modify` matrix: admin sees all, radiologist only own, chief_physician same-department only.
3. Run with `cd backend; .\.venv\Scripts\python -m pytest tests -q`.

**How (frontend):** `npm i -D vitest @testing-library/react jsdom`, add `"test": "vitest run"` to package.json scripts, start with `useAnalysis` (mock `analysisApi`) and the model-picker default-selection effect.

### 2.2 `backend/.env.example`
`.gitignore` already whitelists `!.env.example` but the file doesn't exist, so nobody knows which env vars matter.

**How:** create `backend/.env.example`:
```
AUTH_SECRET_KEY=generate-with: python -c "import secrets; print(secrets.token_urlsafe(48))"
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=medgemma:4b-it-q8_0
DEBUG=false
```

### 2.3 Login rate limiting
`POST /api/auth/login` (auth.py:98) has no brute-force protection — unlimited password guessing.

**How:** `pip install slowapi`, then in `main.py`:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```
and decorate login with `@limiter.limit("5/minute")` (login must accept a `request: Request` param for slowapi to work).

### 2.4 Ollama / model availability check
`model_catalog.py` says "keep in sync with `ollama list`" but nothing enforces it. If a model in the catalog isn't pulled, the failure only shows up mid-analysis.

**How:**
- At startup (in `lifespan` in `main.py`), call `GET {ollama_base_url}/api/tags` with httpx, compare against `VISION_MODELS`, and `logger.warning` any catalog entry that isn't installed.
- Extend `/health` to report `"ollama": "ok" | "unreachable"` so the frontend can surface it.

### 2.5 CI workflow
Nothing runs typecheck/tests automatically.

**How:** `.github/workflows/ci.yml` with two jobs: frontend (`npm ci && npx tsc --noEmit && npm test`) and backend (`pip install -r requirements-dev.txt && pytest backend/tests` — keep heavy deps like TotalSegmentator/pyradiomics out of the CI install; the suggested tests in 2.1 don't need them).

### 2.6 Frontend lint script
package.json has no `lint`. **How:** `npm i -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint-plugin-react-hooks`, add `"lint": "eslint src --ext .ts,.tsx"`. The react-hooks plugin catches real dependency-array bugs, which this codebase (lots of `useEffect`/`useCallback` in App.tsx) is prone to.

---

## 3. IMPROVE — works, but could be better

### 3.1 Split the two oversized components (CLAUDE.md's own 500-line rule)
- `frontend/src/App.tsx` — **774 lines**
- `frontend/src/components/AIReportPanel.tsx` — **759 lines**

**How (App.tsx):** extract self-contained blocks into components — the run-step sidebar (including the new model picker → `components/ModelPicker.tsx`), the patient-context form, and the RAG status block. Each takes its state via props; no logic change. Same approach for AIReportPanel: the edit-mode textareas and section renderers can move into small subcomponents.

### 3.2 New UI strings bypass i18n
The model picker hard-codes `"AI Model"` and `"recommended"` (App.tsx ~line 593) while the rest of the app goes through `t()` from `i18n.tsx`.

**How:** add keys (`step.model`, `step.modelRecommended`) to both locales in `frontend/src/i18n.tsx` and replace the literals with `t('step.model')`.

### 3.3 `model` as a query param on a POST
`POST /analysis/start/{study_id}?model=...` mixes the body (PatientContext) with a query param. Works, but awkward to extend (next option = another query param).

**How:** wrap the body in a request model:
```python
class StartAnalysisRequest(BaseModel):
    patient_context: Optional[PatientContext] = None
    model: Optional[str] = None
```
and send `{ patient_context: ctx, model }` from `api.ts`. Do this before other clients depend on the query-param shape.

### 3.4 Reject unknown model instead of silently substituting
`model_catalog.resolve()` silently falls back to the default when the requested model is invalid — for a *comparison* feature, silently running a different model than the doctor picked is misleading.

**How:** in `start_analysis`, replace the silent resolve with:
```python
if model and not model_catalog.is_allowed(model):
    raise HTTPException(status_code=400, detail=f"Unknown model: {model}")
```

### 3.5 Pin dependency versions
`requirements.txt` is all `>=` — a fresh install next year resolves to different versions (chromadb/langchain in particular break often).

**How:** keep `requirements.txt` as the intent file, and snapshot the working venv: `.\.venv\Scripts\python -m pip freeze > requirements.lock`. Document in README: install from the lock for reproduction (thesis-relevant).

### 3.6 Cookie `secure=False` is hard-coded
`auth.py:72` — right for localhost, wrong the moment this is demoed over HTTPS.

**How:** drive it from config: add `cookie_secure: bool = False` to Settings and use `secure=settings.cookie_secure` in `_set_auth_cookie`.

### 3.7 Repo hygiene: non-code content in the repo root
- `Personal/` (thesis notes, research, diagrams) — only `Personal/Reference/` is gitignored; the rest is mixed into the project.
- `Pictures/` (UI screenshots, likely used by README), `Merlin.md`, `Radiology-Infer-Mini.md` (gitignored but on disk).
- `scripts/validation_results.csv` — generated data output living next to source scripts; `scripts/__pycache__/` too.

**How:** move screenshots to `docs/images/` and update README links; move `validation_results.csv` to `docs/thesis/` (or wherever results live); either gitignore all of `Personal/` or relocate it outside the repo. Delete `scripts/__pycache__`.

### 3.8 Use the existing WebSocket instead of polling
`useAnalysis.ts` polls `GET /analysis/status/{job_id}` on an interval, while `analysis.py` already imports `WebSocket`/`WebSocketDisconnect` and exposes a WS route. Polling works fine for a single user — only worth doing if you want snappier progress updates; otherwise skip.

**How:** in `useAnalysis.start`, open `new WebSocket(`ws://…/api/analysis/ws/${jobId}`)` and update job state from messages, falling back to polling on error.

---

## Suggested order

1. **1.1–1.2** (2 minutes, removes footguns)
2. **1.5** commit the model picker
3. **1.3 + 2.2** secret key + .env.example (security)
4. **1.4, 1.6** small correctness/branding fixes
5. **2.1** tests, then **2.5** CI to keep them running
6. **3.x** as time allows — 3.1 (file splits) and 3.2 (i18n) first since they touch the freshly-changed files
