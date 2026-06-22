# ============================================================
# Liver Cancer AI - One-time setup script (PowerShell)
# Run from the project root:  .\scripts\setup.ps1
# ============================================================

Write-Host "`n=== Liver Cancer AI Setup ===" -ForegroundColor Cyan

# 1. Python virtual environment
if (-not (Test-Path "backend\.venv")) {
    Write-Host "`n[1/6] Creating Python virtual environment (Python 3.11)..." -ForegroundColor Yellow
    py -3.11 -m venv backend\.venv
} else {
    Write-Host "`n[1/6] Virtual environment already exists" -ForegroundColor Green
}

$pip = "backend\.venv\Scripts\pip.exe"
$python = "backend\.venv\Scripts\python.exe"

# 2. PyTorch with CUDA 12.1 (for RTX 4070)
Write-Host "`n[2/6] Installing PyTorch with CUDA 12.1..." -ForegroundColor Yellow
& $pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 --quiet

# 3. Backend dependencies
Write-Host "`n[3/6] Installing backend dependencies..." -ForegroundColor Yellow
& $pip install -r backend\requirements.txt --quiet

# 4. Verify GPU
Write-Host "`n[4/6] Verifying CUDA availability..." -ForegroundColor Yellow
& $python -c "import torch; print('CUDA:', torch.cuda.is_available(), '| Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"

# 5. Ollama models
Write-Host "`n[5/6] Pulling Ollama models (this may take a while on first run)..." -ForegroundColor Yellow
Write-Host "  Pulling llama3.2-vision 11B Q4..." -ForegroundColor Gray
ollama pull llama3.2-vision:11b-instruct-q4_K_M
Write-Host "  Pulling nomic-embed-text..." -ForegroundColor Gray
ollama pull nomic-embed-text

# 6. Frontend
Write-Host "`n[6/6] Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location frontend
npm install
Set-Location ..

# Copy .env
if (-not (Test-Path "backend\.env")) {
    Copy-Item "backend\.env.example" "backend\.env"
    Write-Host "`nCreated backend\.env from example" -ForegroundColor Green
}

Write-Host "`n=== Setup complete! ===" -ForegroundColor Cyan
Write-Host @"

Next steps:
  1. Start backend:   cd backend ; .\.venv\Scripts\uvicorn main:app --reload
  2. Start frontend:  cd frontend ; npm run dev
  3. Open browser:    http://localhost:5173

Optional - load medical guidelines into RAG:
  Place PDF files in:  backend\data\knowledge_base\
  Then run:            cd scripts ; python ingest_guidelines.py

"@ -ForegroundColor White
