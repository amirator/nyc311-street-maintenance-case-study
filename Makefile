# NYC 311 street-maintenance case study. `make help` lists targets.
VENV   ?= .venv
PYTHON := $(VENV)/bin/python
export PYTHONPATH := src

.PHONY: help venv data all test maps slides-png clean

help:
	@echo "make all         download data if missing, build DuckDB, validate, figures, maps, slides"
	@echo "make data        (re)download the 2025 DOT extract from NYC Open Data"
	@echo "make test        run pytest (fixture tests always; full-data tests if data present)"
	@echo "make maps        install mermaid-cli (npm ci) so process maps re-render"
	@echo "make slides-png  render slide previews into docs/img/slides (needs poppler)"

$(PYTHON):
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q --upgrade pip
	$(VENV)/bin/pip install -q -r requirements-dev.txt -c constraints.txt

venv: $(PYTHON)

data: $(PYTHON)
	$(PYTHON) scripts/download_data.py

all: $(PYTHON)
	$(PYTHON) -m case_study all

test: $(PYTHON)
	$(PYTHON) -m pytest -q

maps:
	PUPPETEER_SKIP_DOWNLOAD=1 npm ci

slides-png:
	rm -f docs/img/slides/*.png && pdftoppm -png -r 110 reports/case_study_slides.pdf docs/img/slides/slide

clean:
	rm -rf data/*.duckdb .pytest_cache **/__pycache__
