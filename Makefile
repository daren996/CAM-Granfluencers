PYTHON ?= python3
DOCS_INPUT ?= data/collect

.PHONY: test test-all test-client test-collect check-client-live sync-docs-data docs-data

test: test-all

test-all:
	$(PYTHON) scripts/run_tests.py all

test-client:
	$(PYTHON) scripts/run_tests.py client

test-collect:
	$(PYTHON) scripts/run_tests.py collect

check-client-live:
	$(PYTHON) -m src.collect check

sync-docs-data:
	$(PYTHON) -m src.collect sync-docs-data

docs-data:
	$(PYTHON) -m src.collect export-dashboard --input $(DOCS_INPUT)
	$(PYTHON) -m src.collect sync-docs-data
