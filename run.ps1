# PowerShell helper script for Windows environments (alternative to make)
param (
    [Parameter(Position=0)]
    [string]$Target = "help"
)

# Detect virtual environment binaries
$PYTHON = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }
$PYTEST = if (Test-Path ".\.venv\Scripts\pytest.exe") { ".\.venv\Scripts\pytest.exe" } else { "pytest" }
$STREAMLIT = if (Test-Path ".\.venv\Scripts\streamlit.exe") { ".\.venv\Scripts\streamlit.exe" } else { "streamlit" }
$UVICORN = if (Test-Path ".\.venv\Scripts\uvicorn.exe") { ".\.venv\Scripts\uvicorn.exe" } else { "uvicorn" }

switch ($Target.ToLower()) {
    "load" {
        & $PYTHON src/etl/loader.py
    }
    "ratios" {
        & $PYTHON src/analytics/ratios.py
    }
    "test" {
        & $PYTEST tests/ --html=reports/pytest_report.html --self-contained-html
    }
    "report" {
        & $PYTHON src/reports/portfolio_report.py
    }
    "dashboard" {
        & $STREAMLIT run src/dashboard/app.py
    }
    "api" {
        & $UVICORN src.api.main:app --port 8000 --reload
    }
    "clean" {
        Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
        Get-ChildItem -Recurse -Filter ".pytest_cache" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Clean completed."
    }
    default {
        Write-Host "Usage: .\run.ps1 <target>"
        Write-Host "Targets: load, ratios, test, report, dashboard, api, clean"
    }
}
