.PHONY: help install demo test lint serve doctor init clean

help:
	@echo "SkyCache targets:"
	@echo "  make install  - install package + dev deps"
	@echo "  make init     - create data dirs and load sample packages"
	@echo "  make demo     - init + serve simulation mode"
	@echo "  make serve    - run portal (use SKYCACHE_SIM=1 for sim)"
	@echo "  make test     - run pytest"
	@echo "  make doctor   - environment health check"
	@echo "  make lint     - ruff check"
	@echo "  make clean    - remove caches and local data"

install:
	python -m pip install -e ".[dev]"

init:
	python -m skycache init --load-samples

demo: init
	python -m skycache serve --sim --host 127.0.0.1 --port 8080

serve:
	python -m skycache serve --host 0.0.0.0 --port 8080

test:
	python -m pytest -q

doctor:
	python -m skycache doctor

lint:
	python -m ruff check skycache tests

clean:
	rm -rf data .pytest_cache .ruff_cache **/__pycache__ *.egg-info dist build
