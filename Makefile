# Convenience wrapper around src/run_pipeline.py.
# Every target is a thin alias so the pipeline stays the single entry point.

# The vendored numpy/matplotlib under pylibs/ are built for CPython 3.12, so a
# newer `python3` cannot import them. Fall back to a 3.12 interpreter when one
# exists. Override explicitly with:  make PY=/path/to/python3.12
PY ?= $(shell command -v python3.12 || command -v /snap/core24/current/usr/bin/python3.12 || echo python3)

.PHONY: all data analysis figures reports validate clean

all:            ## regenerate everything (data -> docs -> figures -> validation)
	$(PY) src/run_pipeline.py

fast:           ## re-run analysis/reporting without regenerating the dataset
	$(PY) src/run_pipeline.py --fast

data:           ## simulate the dataset and clean it
	$(PY) src/generate_data.py
	$(PY) src/clean_data.py

analysis:       ## build the warehouse and run the decomposition
	$(PY) src/run_sql.py
	$(PY) src/decompose.py
	$(PY) src/five_whys.py
	$(PY) src/write_report.py

figures:        ## regenerate the ten charts
	$(PY) src/make_figures.py

reports:        ## rebuild the brief, the deck, the Word report and the PDF
	$(PY) src/write_reports.py

validate:       ## grade the diagnostic against the ground truth (exit 0 = pass)
	$(PY) src/validate_against_truth.py

clean:          ## remove generated artefacts (safe: all are reproducible)
	rm -rf data/raw data/processed outputs/tables outputs/figures outputs/reports \
	       data/revenue_decline.sqlite
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
