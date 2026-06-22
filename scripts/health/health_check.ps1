#requires -Version 5.1
<#
.SYNOPSIS
    LuminaDx health check + auto-fix for the backend (FastAPI) and frontend (Vite/React).

.DESCRIPTION
    Verifies the dev environment is wired correctly and that both apps run:
      - tooling present (py launcher / python, node, npm)
      - backend Python venv + dependencies
      - backend/.env present with a non-default AUTH_SECRET_KEY
      - frontend node_modules installed
      - stray 0-byte junk files (from botched shell redirects) cleaned up
      - backend imports + pytest suite
      - frontend TypeScript typecheck (and optional production build)
      - Ollama reachability + required models

    Run check-only (default) or pass -Fix to auto-repair what it can.

.PARAMETER Fix
    Apply auto-fixes: create venv, install deps, npm install, generate .env /
    AUTH_SECRET_KEY, delete known junk files, pull missing Ollama models.

.PARAMETER SkipTests
    Skip the backend pytest suite and frontend typecheck (faster smoke check).

.PARAMETER Build
    Also run the frontend production build (npm run build).

.PARAMETER SkipOllama
    Skip the Ollama reachability / model checks.

.EXAMPLE
    .\scripts\shared\health_check.ps1
    .\scripts\shared\health_check.ps1 -Fix
    .\scripts\shared\health_check.ps1 -Fix -Build
#>
[CmdletBinding()]
param(
    [switch]$Fix,
    [switch]$SkipTests,
    [switch]$Build,
    [switch]$SkipOllama
)

$ErrorActionPreference = "Continue"

# Resolve repo root (script lives in scripts/shared/)
$RepoRoot   = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Backend    = Join-Path $RepoRoot "backend"
$Frontend   = Join-Path $RepoRoot "frontend"
$VenvPython = Join-Path $Backend  ".venv\Scripts\python.exe"
$VenvPip    = Join-Path $Backend  ".venv\Scripts\pip.exe"

# Result tallies
$script:Pass     = 0
$script:Fail     = 0
$script:Fixed    = 0
$script:Warn     = 0
$script:Failures = @()

function Ok   ($m) { Write-Host "  [ OK   ] $m" -ForegroundColor Green;  $script:Pass++ }
function Bad  ($m) { Write-Host "  [ FAIL ] $m" -ForegroundColor Red;    $script:Fail++; $script:Failures += $m }
function Done ($m) { Write-Host "  [ FIXED] $m" -ForegroundColor Cyan;   $script:Fixed++ }
function Warn ($m) { Write-Host "  [ WARN ] $m" -ForegroundColor Yellow; $script:Warn++ }
function Step ($m) { Write-Host "`n=== $m ===" -ForegroundColor Magenta }

# Run a venv python command with the same env hygiene as start_backend.ps1
function Invoke-VenvPython {
    param([string[]]$ArgList, [string]$WorkDir = $Backend)
    $oldPP = $env:PYTHONPATH; $oldVE = $env:VIRTUAL_ENV
    $env:PYTHONPATH = ""; $env:VIRTUAL_ENV = ""
    Push-Location $WorkDir
    try { & $VenvPython @ArgList 2>&1 | Out-String }
    finally {
        Pop-Location
        $env:PYTHONPATH = $oldPP; $env:VIRTUAL_ENV = $oldVE
    }
}

# Run a multi-line Python script (passed on stdin) in the venv; return output + exit code.
function Invoke-VenvPythonScript {
    param([string]$Code, [string]$WorkDir = $Backend)
    $oldPP = $env:PYTHONPATH; $oldVE = $env:VIRTUAL_ENV
    $env:PYTHONPATH = ""; $env:VIRTUAL_ENV = ""
    Push-Location $WorkDir
    try {
        $out = ($Code | & $VenvPython - 2>&1 | Out-String)
        return [pscustomobject]@{ Output = $out; Code = $LASTEXITCODE }
    }
    finally {
        Pop-Location
        $env:PYTHONPATH = $oldPP; $env:VIRTUAL_ENV = $oldVE
    }
}

function New-Secret {
    if (Test-Path $VenvPython) {
        $s = (Invoke-VenvPython @("-c", "import secrets; print(secrets.token_urlsafe(48))")).Trim()
        if ($s) { return $s }
    }
    $bytes = New-Object byte[] 48
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
}

function Rel ($path) {
    if ($path.StartsWith($RepoRoot)) { return $path.Substring($RepoRoot.Length).TrimStart('\','/') }
    return $path
}

Write-Host "LuminaDx health check  (root: $RepoRoot)" -ForegroundColor White
$mode = if ($Fix) { "AUTO-FIX" } else { "check-only" }
if ($SkipTests) { $mode += " | tests skipped" }
if ($Build)     { $mode += " | +build" }
Write-Host "Mode: $mode" -ForegroundColor DarkGray

# ---------------------------------------------------------------------------
Step "1. Tooling"
# ---------------------------------------------------------------------------
$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) { Ok "node $(node --version)" } else { Bad "node not found on PATH" }

$npm = Get-Command npm -ErrorAction SilentlyContinue
if ($npm) { Ok "npm $(npm --version)" } else { Bad "npm not found on PATH" }

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
$python     = Get-Command python -ErrorAction SilentlyContinue
if ($pyLauncher -or $python) { Ok "Python launcher available" } else { Bad "Python not found on PATH" }

# ---------------------------------------------------------------------------
Step "2. Junk file cleanup"
# ---------------------------------------------------------------------------
# Known stray artifacts from botched shell redirects. Only removed if 0 bytes.
$junk = @(
    (Join-Path $Backend  "{,+"),
    (Join-Path $Backend  "50%"),
    (Join-Path $Backend  "8mm"),
    (Join-Path $Backend  "None')"),
    (Join-Path $Frontend "50%"),
    (Join-Path $Frontend "None')"),
    (Join-Path $RepoRoot "DiagnosticReport")
)
$foundJunk = $false
foreach ($f in $junk) {
    if (Test-Path -LiteralPath $f) {
        $foundJunk = $true
        $item = Get-Item -LiteralPath $f -Force
        if ($item.Length -eq 0) {
            if ($Fix) {
                Remove-Item -LiteralPath $f -Force -Confirm:$false
                Done "removed junk: $(Rel $f)"
            } else {
                Warn "junk file (0 bytes): $(Rel $f)  (use -Fix to delete)"
            }
        } else {
            Warn "stray file is NOT empty, leaving it: $(Rel $f)"
        }
    }
}
if (-not $foundJunk) { Ok "no known junk files present" }

# ---------------------------------------------------------------------------
Step "3. Backend virtualenv + dependencies"
# ---------------------------------------------------------------------------
if (Test-Path $VenvPython) {
    Ok "venv present (backend\.venv)"
} else {
    if ($Fix) {
        Write-Host "  creating venv..." -ForegroundColor DarkGray
        if ($pyLauncher) { py -3.11 -m venv (Join-Path $Backend ".venv") }
        else             { python -m venv (Join-Path $Backend ".venv") }
        if (Test-Path $VenvPython) { Done "created backend\.venv" } else { Bad "venv creation failed" }
    } else {
        Bad "venv missing (backend\.venv) - run with -Fix or scripts\shared\setup.ps1"
    }
}

if (Test-Path $VenvPython) {
    $depCheck = Invoke-VenvPython @("-c", "import fastapi, uvicorn, pydantic, sqlalchemy, httpx, loguru, slowapi; print('DEPS_OK')")
    if ($depCheck -match "DEPS_OK") {
        Ok "core backend dependencies import"
    } else {
        if ($Fix) {
            Write-Host "  installing requirements.txt..." -ForegroundColor DarkGray
            & $VenvPip install -r (Join-Path $Backend "requirements.txt") --quiet
            $depCheck2 = Invoke-VenvPython @("-c", "import fastapi, uvicorn, pydantic, sqlalchemy, httpx, loguru, slowapi; print('DEPS_OK')")
            if ($depCheck2 -match "DEPS_OK") { Done "installed backend dependencies" }
            else { Bad "backend dependencies still missing after install" }
        } else {
            Bad "backend dependencies missing - run with -Fix"
        }
    }
    $pt = Invoke-VenvPython @("-c", "import pytest; print('PYTEST_OK')")
    if ($pt -notmatch "PYTEST_OK" -and $Fix) {
        & $VenvPip install -r (Join-Path $Backend "requirements-dev.txt") --quiet
    }
}

# ---------------------------------------------------------------------------
Step "4. Backend .env / AUTH_SECRET_KEY"
# ---------------------------------------------------------------------------
$envFile    = Join-Path $Backend ".env"
$envExample = Join-Path $Backend ".env.example"

if (Test-Path -LiteralPath $envFile) {
    $envText = Get-Content -LiteralPath $envFile -Raw
    if ($envText -match 'AUTH_SECRET_KEY\s*=\s*(.+)') {
        $val = $Matches[1].Trim()
        if ($val -and $val -notmatch '^change-me') {
            Ok ".env present with a non-default AUTH_SECRET_KEY"
        } else {
            if ($Fix) {
                $secret = New-Secret
                $new = $envText -replace 'AUTH_SECRET_KEY\s*=.*', "AUTH_SECRET_KEY=$secret"
                Set-Content -LiteralPath $envFile -Value $new -Encoding utf8 -NoNewline
                Done "generated a secure AUTH_SECRET_KEY in backend\.env"
            } else {
                Bad "AUTH_SECRET_KEY is still the insecure default - run with -Fix"
            }
        }
    } else {
        if ($Fix) {
            $secret = New-Secret
            Add-Content -LiteralPath $envFile -Value "`nAUTH_SECRET_KEY=$secret" -Encoding utf8
            Done "added AUTH_SECRET_KEY to backend\.env"
        } else {
            Warn ".env present but no AUTH_SECRET_KEY line found - run with -Fix"
        }
    }
} else {
    if ($Fix) {
        if (Test-Path -LiteralPath $envExample) { Copy-Item -LiteralPath $envExample -Destination $envFile }
        else { New-Item -ItemType File -Path $envFile | Out-Null }
        $secret = New-Secret
        $cur = if (Test-Path -LiteralPath $envFile) { Get-Content -LiteralPath $envFile -Raw } else { "" }
        if ($cur -match 'AUTH_SECRET_KEY\s*=') {
            $cur = $cur -replace 'AUTH_SECRET_KEY\s*=.*', "AUTH_SECRET_KEY=$secret"
            Set-Content -LiteralPath $envFile -Value $cur -Encoding utf8 -NoNewline
        } else {
            Add-Content -LiteralPath $envFile -Value "AUTH_SECRET_KEY=$secret" -Encoding utf8
        }
        Done "created backend\.env with a secure AUTH_SECRET_KEY"
    } else {
        Bad "backend\.env missing - run with -Fix (or copy .env.example)"
    }
}

# ---------------------------------------------------------------------------
Step "5. Frontend dependencies"
# ---------------------------------------------------------------------------
if (Test-Path (Join-Path $Frontend "node_modules")) {
    Ok "node_modules present"
} else {
    if ($Fix -and $npm) {
        Write-Host "  npm install..." -ForegroundColor DarkGray
        Push-Location $Frontend; npm install; Pop-Location
        if (Test-Path (Join-Path $Frontend "node_modules")) { Done "installed frontend dependencies" }
        else { Bad "npm install did not produce node_modules" }
    } else {
        Bad "frontend node_modules missing - run with -Fix"
    }
}

# ---------------------------------------------------------------------------
Step "6. Backend import + tests"
# ---------------------------------------------------------------------------
if (Test-Path $VenvPython) {
    $imp = Invoke-VenvPython @("-c", "import main; print('IMPORT_OK')")
    if ($imp -match "IMPORT_OK") { Ok "backend imports (main:app)" }
    else { Bad "backend failed to import:`n$imp" }

    if (-not $SkipTests) {
        Write-Host "  running pytest..." -ForegroundColor DarkGray
        $testOut = Invoke-VenvPython @("-m", "pytest", "-q")
        $summary = ($testOut -split "`n" | Where-Object { $_ -match "passed|failed|error" } | Select-Object -Last 1)
        if ($testOut -match "failed|error" -and $testOut -notmatch "0 failed") {
            Bad "pytest: $($summary.Trim())"
        } else {
            Ok "pytest: $($summary.Trim())"
        }
    } else {
        Warn "pytest skipped (-SkipTests)"
    }
} else {
    Bad "skipping backend tests - no venv"
}

# ---------------------------------------------------------------------------
Step "7. AI model picker + feature/extraction selection"
# ---------------------------------------------------------------------------
# Validates the two catalogs that drive the per-diagnosis pickers
# (core/model_catalog.py + core/feature_catalog.py) and that they agree with the
# module registry and the CNN backbone registry. Then confirms the frontend is
# still wired to consume them. This is the piece that "keeps getting forgotten".
$pickerValidator = @'
import sys
from core import model_catalog as mc, feature_catalog as fc, cnn_features
from core.modules import registry
errs = []
cancers = set(registry.CANCER_TYPES)

# --- LLM model catalog (the "AI Model Pick" dropdown) ---
mcat = mc.catalog()
if set(mcat) != cancers:
    errs.append(f"model catalog cancers {set(mcat)} != registry {cancers}")
for ct in cancers:
    d = mc.default_for(ct)
    if d not in mc.VISION_MODELS:
        errs.append(f"{ct}: default model '{d}' not in VISION_MODELS")
    opts = mc.options_for(ct)
    if not opts or opts[0]["tag"] != d:
        errs.append(f"{ct}: options_for() does not list the default first")
    for o in opts:
        if o["tag"] not in mc.VISION_MODELS:
            errs.append(f"{ct}: option '{o['tag']}' not in VISION_MODELS")

# --- Feature / extraction catalog (the "Features & Extraction" checkboxes) ---
fcat = fc.catalog()
if set(fcat) != cancers:
    errs.append(f"feature catalog cancers {set(fcat)} != registry {cancers}")
for ct in cancers:
    applicable = set(fc.applicable_for(ct))
    for k in applicable:
        if k not in fc._FEATURES:
            errs.append(f"{ct}: applicable feature '{k}' missing from _FEATURES")
    for dd in fc.defaults_for(ct):
        if dd not in applicable:
            errs.append(f"{ct}: default feature '{dd}' not in applicable set")
    if fc.resolve(ct, None) != set(fc.defaults_for(ct)):
        errs.append(f"{ct}: resolve(None) != defaults")
    if fc.resolve(ct, ["__bogus__"]) != set():
        errs.append(f"{ct}: resolve() did not drop an unknown feature key")

# --- CNN backbones referenced by the feature catalog must be real extractors ---
for k, (_, g) in fc._FEATURES.items():
    if g == "cnn" and not cnn_features.is_backbone(k):
        errs.append(f"CNN feature '{k}' is not a recognised cnn_features backbone")

if errs:
    print("PICKERS_FAIL")
    for e in errs:
        print("  - " + e)
    sys.exit(1)
print(f"PICKERS_OK models={len(mc.VISION_MODELS)} features={len(fc._FEATURES)} cancers={len(cancers)}")
'@

if (Test-Path $VenvPython) {
    $pick = Invoke-VenvPythonScript $pickerValidator
    if ($pick.Output -match "PICKERS_OK") {
        $stats = ($pick.Output -split "`n" | Where-Object { $_ -match "PICKERS_OK" } | Select-Object -First 1) -replace ".*PICKERS_OK\s*", ""
        Ok "model + feature/extraction catalogs consistent ($($stats.Trim()))"
    } else {
        Bad "model/feature picker validation failed:`n$($pick.Output)"
    }
} else {
    Bad "skipping picker validation - no venv"
}

# Frontend wiring: the pickers must still be consumed by the UI.
$apiFile   = Join-Path $Frontend "src\services\api.ts"
$typesFile = Join-Path $Frontend "src\types\index.ts"
$wpFile    = Join-Path $Frontend "src\components\WorkflowPanel.tsx"
if ((Test-Path $apiFile) -and (Test-Path $typesFile) -and (Test-Path $wpFile)) {
    $apiTxt   = Get-Content $apiFile -Raw
    $typesTxt = Get-Content $typesFile -Raw
    $wpTxt    = Get-Content $wpFile -Raw
    $wired = ($apiTxt -match "/analysis/models") -and ($apiTxt -match "/analysis/features") `
        -and ($typesTxt -match "ModelCatalog") -and ($typesTxt -match "FeatureCatalog") `
        -and ($wpTxt -match "modelCatalog") -and ($wpTxt -match "featureCatalog") -and ($wpTxt -match "selectedFeatures")
    if ($wired) { Ok "frontend pickers wired (model dropdown + feature checkboxes)" }
    else { Bad "frontend picker wiring missing - check api.ts / types / WorkflowPanel.tsx" }
} else {
    Warn "frontend picker source files not found - skipping wiring check"
}

# Skin classifier calibration metadata (temperature + operating thresholds).
# Advisory only: older checkpoints fall back to safe defaults, so a missing
# calibration is a WARN (run scripts/skin/calibrate_skin.py), not a failure.
$skinCalibProbe = @'
import sys
from config import settings
ckpt = settings.weights_dir / "skin_ham10000_resnet50.pt"
if not ckpt.exists():
    print("SKIN_CKPT_ABSENT"); sys.exit(0)
try:
    import torch
    try:
        meta = torch.load(ckpt, map_location="cpu", weights_only=False, mmap=True)
    except TypeError:
        meta = torch.load(ckpt, map_location="cpu", weights_only=False)
except Exception as e:
    print("SKIN_CKPT_UNREADABLE " + str(e)[:80]); sys.exit(0)
keys = [k for k in ("temperature", "malignancy_threshold", "melanoma_threshold") if k in meta]
if len(keys) == 3:
    print(f"SKIN_CALIB_OK T={meta['temperature']:.2f} mal_thr={meta['malignancy_threshold']:.2f} mel_thr={meta['melanoma_threshold']:.2f}")
else:
    print("SKIN_CALIB_MISSING have=" + (",".join(keys) or "none"))
'@
if (Test-Path $VenvPython) {
    $calib = Invoke-VenvPythonScript $skinCalibProbe
    $line = ($calib.Output -split "`n" | Where-Object { $_ -match "SKIN_" } | Select-Object -First 1)
    if ($line -match "SKIN_CALIB_OK")        { Ok "skin classifier calibrated ($((($line -replace '.*SKIN_CALIB_OK\s*','')).Trim()))" }
    elseif ($line -match "SKIN_CALIB_MISSING") { Warn "skin classifier not calibrated - run scripts\skin\calibrate_skin.py ($((($line -replace '.*SKIN_CALIB_MISSING\s*','')).Trim()))" }
    elseif ($line -match "SKIN_CKPT_ABSENT")   { Warn "no trained skin checkpoint (HAM10000 classifier disabled until trained)" }
    else { Warn "skin checkpoint calibration could not be read" }
}

# ---------------------------------------------------------------------------
Step "8. Frontend typecheck / build"
# ---------------------------------------------------------------------------
if ((Test-Path (Join-Path $Frontend "node_modules")) -and $npm) {
    if (-not $SkipTests) {
        Write-Host "  tsc --noEmit..." -ForegroundColor DarkGray
        Push-Location $Frontend
        $tscOut = (& npx tsc --noEmit 2>&1 | Out-String)
        $tscCode = $LASTEXITCODE
        Pop-Location
        if ($tscCode -eq 0) { Ok "TypeScript typecheck clean" }
        else { Bad "tsc reported errors:`n$tscOut" }
    } else {
        Warn "typecheck skipped (-SkipTests)"
    }

    if ($Build) {
        Write-Host "  npm run build..." -ForegroundColor DarkGray
        Push-Location $Frontend
        $buildOut = (& npm run build 2>&1 | Out-String)
        $buildCode = $LASTEXITCODE
        Pop-Location
        if ($buildCode -eq 0) { Ok "frontend production build succeeded" }
        else { Bad "frontend build failed:`n$buildOut" }
    }
} else {
    Bad "skipping frontend checks - node_modules missing"
}

# ---------------------------------------------------------------------------
Step "9. Ollama (LLM backend)"
# ---------------------------------------------------------------------------
if ($SkipOllama) {
    Warn "Ollama checks skipped (-SkipOllama)"
} else {
    $ollamaUrl = "http://localhost:11434"
    try {
        $tags = Invoke-RestMethod -Uri "$ollamaUrl/api/tags" -TimeoutSec 4 -ErrorAction Stop
        Ok "Ollama reachable at $ollamaUrl"
        $installed = @($tags.models | ForEach-Object { $_.name })
        $required = @("medgemma:4b-it-q8_0", "nomic-embed-text")
        foreach ($m in $required) {
            if ($installed -contains $m) {
                Ok "model present: $m"
            } else {
                if ($Fix -and (Get-Command ollama -ErrorAction SilentlyContinue)) {
                    Write-Host "  ollama pull $m ..." -ForegroundColor DarkGray
                    ollama pull $m
                    Done "pulled $m"
                } else {
                    Warn "model not installed: $m  (ollama pull $m)"
                }
            }
        }
    } catch {
        Warn "Ollama unreachable at $ollamaUrl - start it with 'ollama serve' (LLM features degraded)"
    }
}

# ---------------------------------------------------------------------------
Step "Summary"
# ---------------------------------------------------------------------------
Write-Host ("  Passed: {0}   Fixed: {1}   Warnings: {2}   Failed: {3}" -f `
    $script:Pass, $script:Fixed, $script:Warn, $script:Fail) -ForegroundColor White

if ($script:Fail -gt 0) {
    Write-Host "`nFailures:" -ForegroundColor Red
    $script:Failures | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    if (-not $Fix) { Write-Host "`nTip: re-run with -Fix to auto-repair." -ForegroundColor Yellow }
    exit 1
} else {
    Write-Host "`nAll critical checks passed." -ForegroundColor Green
    exit 0
}
