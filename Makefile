.PHONY: help load ratios test report dashboard api clean

PYTHON = python
PYTEST = pytest
STREAMLIT = streamlit
UVICORN = uvicorn

help:
	@echo "Available commands:"
	@echo "  make load        - Runs ETL pipeline to load all 12 files into nifty100.db"
	@echo "  make ratios      - Runs Ratio Engine to compute 30+ financial KPIs"
	@echo "  make test        - Runs full pytest test suite and generates HTML report"
	@echo "  make report      - Generates automated PDF tearsheets and sector reports"
	@echo "  make dashboard   - Launches Streamlit interactive dashboard"
	@echo "  make api         - Starts FastAPI REST server on port 8000"
	@echo "  make clean       - Cleans cached Python files and test artifacts"

load:
	$(PYTHON) src/etl/loader.py

ratios:
	$(PYTHON) src/analytics/ratios.py

test:
	$(PYTEST) tests/ --html=reports/pytest_report.html --self-contained-html

report:
	$(PYTHON) src/reports/portfolio_report.py

dashboard:
	$(STREAMLIT) run src/dashboard/app.py

api:
	$(UVICORN) src.api.main:app --port 8000 --reload

clean:
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
