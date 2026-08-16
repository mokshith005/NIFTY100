.PHONY: load ratios test report dashboard api clean

load:
	python src/etl/loader.py

ratios:
	python src/ratios.py

test:
	pytest tests/ -v

report:
	python src/report.py

dashboard:
	streamlit run src/dashboard.py

api:
	uvicorn src.api:app --reload

clean:
	python -c "import shutil; from pathlib import Path; [shutil.rmtree(p, ignore_errors=True) for p in Path('.').rglob('__pycache__')]; shutil.rmtree('.pytest_cache', ignore_errors=True)"