PYTHON ?= python3

.PHONY: test test-all test-client test-collect check-client-live

test: test-all

test-all:
	$(PYTHON) scripts/run_tests.py all

test-client:
	$(PYTHON) scripts/run_tests.py client

test-collect:
	$(PYTHON) scripts/run_tests.py collect

check-client-live:
	$(PYTHON) -m src.collect check
