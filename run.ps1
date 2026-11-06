# PowerShell helper script for Windows environments (alternative to make)
param (
    [Parameter(Position=0)]
    [string]$Target = "help"
)

switch ($Target.ToLower()) {
    "load" {
        python src/etl/loader.py
    }
    "ratios" {
        python src/analytics/ratios.py
    }
    "test" {
        pytest tests/ --html=reports/pytest_report.html --self-contained-html
    }
    "report" {
        python src/reports/portfolio_report.py
    }
    "dashboard" {
        streamlit run src/dashboard/app.py
    }
    "api" {
        uvicorn src.api.main:app --port 8000 --reload
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
