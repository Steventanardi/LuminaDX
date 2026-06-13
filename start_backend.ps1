Set-Location "$PSScriptRoot\backend"
$env:PYTHONPATH = ""
$env:VIRTUAL_ENV = ""
.\.venv\Scripts\python.exe -m uvicorn main:app --port 8000
