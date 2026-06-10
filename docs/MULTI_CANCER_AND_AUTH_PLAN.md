# LuminaDx — Multi-Cancer + Doctor Authentication Plan

> Plan only. No code changed yet. Two parallel goals:
> 1. Expand from **liver-only** to **5 cancer types**: Lung, Liver, Skin, Breast, Colorectal.
> 2. Add **real doctor login** (accounts + sessions) so only authenticated clinicians can use the app, with per-user data isolation to prevent data leaks.

---

## 1. Where the code is liver-locked today

Current pipeline is hardwired to liver/LI-RADS in these files:

| Layer | File | Liver-specific coupling |
|-------|------|--------------------------|
| Schemas | `backend/models/schemas.py` | `LiRadsCategory`, `LesionFinding` (APHE/washout/capsule), `DiagnosticReport` (`bclc_stage`), `PatientContext` (cirrhosis/hepatitis/AFP) |
| LLM | `backend/core/llm_client.py` | Hardcoded "hepatic radiologist" system prompt, LI-RADS v2024, BCLC, fixed JSON schema |
| Segmentation | `backend/core/segmentation.py` | TotalSegmentator `liver` + `liver_lesions` tasks (CT only) |
| Pipeline | `backend/api/routes/analysis.py` | Liver RAG query strings, liver tumor mask filenames |
| RAG | `backend/core/rag_engine.py` | Single guideline knowledge base (liver guidelines) |
| Auth | `backend/api/deps.py` | One optional shared `X-API-Key` — **no users, no sessions, no isolation** |
| Frontend | `frontend/src/App.tsx` | "Liver Cancer AI" title, cirrhosis/hepatitis chips, LI-RADS + BCLC badge |

**Good news:** the upload layer already splits into 3 pipelines — **volumetric** (DICOM/NIfTI → segmentation) vs **image** (JPG/PNG → LLM-only). That split maps cleanly onto the new cancer types.

---

## 2. Cancer types — modality, scoring, pipeline

| Cancer | Primary modality | Pipeline reuse | Scoring system | Auto-segmentation |
|--------|------------------|----------------|----------------|-------------------|
| **Liver** (existing) | CT / MRI | volumetric | LI-RADS v2024 + BCLC | TotalSegmentator liver + liver_lesions |
| **Lung** | CT | volumetric | Lung-RADS v2022 + Fleischner | TotalSegmentator lung lobes + lung_nodules |
| **Colorectal** | CT (CT colonography) | volumetric | C-RADS / TNM | TotalSegmentator colon (polyp seg limited → LLM-assisted) |
| **Breast** | Mammography / US / MRI | image (mammo/US) + volumetric (MRI later) | BI-RADS | none initially → LLM vision |
| **Skin** | Dermoscopy / clinical photo | image | ABCDE + 7-point + Breslow estimate | none → LLM vision |

Order of rollout (low → high effort): **Skin → Breast → Lung → Colorectal** (Liver already done). Skin/Breast are image-only and need no new seg models, so they validate the abstraction fastest.

---

## 3. Architecture approach — "Diagnosis Module" registry

Introduce a **cancer-type plugin abstraction** so each cancer is a self-contained module and the pipeline becomes generic.

```
backend/core/modules/
  base.py            # DiagnosisModule protocol/ABC
  liver.py           # refactor existing logic here (no behavior change)
  lung.py
  skin.py
  breast.py
  colorectal.py
  registry.py        # name -> module instance
```

Each `DiagnosisModule` declares:

```python
class DiagnosisModule(Protocol):
    cancer_type: str                 # "liver" | "lung" | ...
    display_name: str
    accepted_modalities: list[str]   # ["CT","MRI"] / ["photo"] / ...
    pipeline: Literal["volumetric", "image"]

    def segmentation_spec(self) -> SegSpec | None      # which TotalSeg tasks, or None
    def system_prompt(self) -> str                     # specialist persona + criteria
    def report_schema(self) -> dict                    # JSON shape the LLM must return
    def rag_query(self, seg, modality) -> str          # retrieval query
    def rag_namespace(self) -> str                     # which guideline KB
    def parse_report(self, raw) -> DiagnosticReport    # module-aware parsing
    def patient_context_fields(self) -> list[Field]    # drives frontend context form
```

**Generic report model:** make `DiagnosticReport` cancer-agnostic:
- Keep core fields (`overall_impression`, `lesions[]`, `differential_diagnosis`, `recommendations`, `guideline_citations`).
- Replace `lirads_category` with generic `score_system` + `score` (e.g. `"LI-RADS"`/`"LR-5"`, `"BI-RADS"`/`"4A"`, `"Lung-RADS"`/`"4B"`).
- Move liver-only fields (`bclc_stage`, APHE/washout/capsule) into a flexible `findings: dict` / typed per-module extension so we don't break liver output.

**Pipeline change** (`analysis.py`): replace hardcoded liver steps with `module = registry.get(cancer_type)` and call module hooks for seg spec, RAG query, prompt, parsing. The per-job `cancer_type` is selected at upload time (frontend dropdown) and stored on the study/job.

**RAG** (`rag_engine.py`): namespace the vector store per cancer (separate collections or a `cancer_type` metadata filter) and ingest each cancer's guideline PDFs into its own namespace.

This keeps liver behavior byte-for-byte identical (it just moves into `liver.py`) while every new cancer is an additive module.

---

## 4. Authentication & data isolation approach

Goal: a doctor must log in before any clinical action, and **can only see their own studies/reports** (data-leak prevention). The current shared-key check is replaced entirely.

### Stack
- **SQLite + SQLAlchemy** (new lightweight DB; no server needed, fits the prototype). Users + a thin index of study/job ownership live here.
- **`passlib[bcrypt]`** for password hashing (never store plaintext).
- **JWT** (`pyjwt`) access tokens, short-lived (e.g. 30–60 min) + optional refresh token.
- Secret key from `.env` (`AUTH_SECRET_KEY`), never committed.

### User model
```
User: id, email, full_name, hashed_password, role (admin|radiologist),
      is_active, created_at, last_login
```
- **Admin-provisioned accounts** (recommended for a medical app — no open self-registration). Admin seeds the first account via a script; admin endpoint creates further doctor accounts.

### Endpoints (`backend/api/routes/auth.py`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/login` | email+password → JWT |
| POST | `/api/auth/logout` | invalidate session/refresh (if used) |
| GET  | `/api/auth/me` | current user profile |
| POST | `/api/auth/users` | admin creates doctor account |
| POST | `/api/auth/change-password` | rotate own password |

### Enforcement
- New dependency `get_current_user` (replaces `verify_api_key`) applied to **every** clinical route in `dicom.py`, `analysis.py`, `rag.py`, `audit.py`.
- **Data isolation:** add `owner_user_id` to `DicomStudy` and `AnalysisJob`. All list/get/delete/report/slices endpoints filter by `owner_user_id == current_user.id` (admin may see all, optional). A doctor requesting another user's `job_id`/`study_id` gets `404` (not `403`, to avoid leaking existence).
- **Audit + sign-off** (`audit_log.py`, `SignOff`): record the authenticated user identity instead of a free-text `radiologist_name`, giving a real accountability trail.

### Frontend
- **Login screen** gates the whole app; unauthenticated users see only login.
- `AuthContext` + axios interceptor attaches `Authorization: Bearer <token>`; on `401` → force logout/redirect to login.
- Token storage: **httpOnly cookie preferred** (immune to XSS token theft); fallback in-memory + refresh. (Decision flagged below.)
- Header shows logged-in doctor name + logout button. Sign-off auto-fills the authenticated doctor's name.

### Security hardening
- Login rate-limiting / lockout after N failed attempts.
- Password policy (min length, complexity).
- CORS already restricted to localhost dev origins — tighten for prod.
- HTTPS required in any real deployment (PHI). De-identification on upload already exists — keep it.

---

## 5. Phased delivery

**Phase 0 — Auth foundation** (do first; it's the data-leak guard)
1. Add SQLite/SQLAlchemy, User model, password hashing, JWT.
2. `auth.py` routes + `get_current_user` dependency + admin seed script.
3. Add `owner_user_id` to studies/jobs; enforce isolation on all routes.
4. Frontend login screen + auth context + interceptor + logout.
5. Tie audit log + sign-off to authenticated user.

**Phase 1 — Diagnosis-module abstraction**
6. Create `modules/base.py` + `registry.py`; refactor liver into `modules/liver.py` (no behavior change — regression-test against current output).
7. Generalize `DiagnosticReport` (`score_system`/`score` + `findings`); make pipeline module-driven.
8. Add `cancer_type` to upload + frontend cancer selector; namespace RAG per cancer.

**Phase 2 — New cancer modules (incremental)**
9. Skin (image, ABCDE/Breslow) → 10. Breast (image, BI-RADS) → 11. Lung (volumetric, Lung-RADS) → 12. Colorectal (volumetric, C-RADS/TNM).
Each: system prompt + report schema + RAG guidelines + frontend context fields + tests.

**Phase 3 — Polish**
13. Rebrand UI "Liver Cancer AI" → "LuminaDx" multi-cancer; per-cancer badges (LI-RADS/Lung-RADS/BI-RADS).
14. Docs + model cards per cancer; update thesis chapters.

---

## 6. Decisions — CONFIRMED

1. **Token storage:** ✅ **httpOnly cookie** — backend sets a secure httpOnly cookie; immune to XSS token theft. Add CSRF protection (SameSite=strict + CSRF token on state-changing requests).
2. **Account creation:** ✅ **Admin-provisioned only** — no open self-registration. Admin seeds the first account via a script; admin endpoint creates further doctor accounts.
3. **Cross-user visibility:** ✅ **Strict per-doctor isolation** — every user, including admin, sees only their own studies/reports. Cross-user `job_id`/`study_id` access → `404`.
4. **Scope / first deliverable:** ✅ **Auth + Skin vertical slice** — ship login + Skin (image-only) end-to-end first to validate the module abstraction, then add Breast → Lung → Colorectal.

---

## 7. Risks / notes
- Lung/colorectal nodule & polyp auto-segmentation is weaker than liver lesion seg; expect heavier reliance on the vision-LLM for those, with seg as an assist.
- Generalizing `DiagnosticReport` must not break the existing liver report/PDF/FHIR export — covered by a liver regression test in Phase 1.
- Adding a DB is a real dependency shift from the current "dependency-free JSON store"; SQLite keeps it file-based and simple.
- PHI: per-user isolation + existing DICOM de-identification + HTTPS-in-prod together form the data-leak defense.
