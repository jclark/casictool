SRC_FILES = casictool.py casic.py

dev-deps:
	.venv/bin/pip install -e ".[dev]"

lint:
	.venv/bin/ruff check $(SRC_FILES) tests/

typecheck:
	.venv/bin/mypy $(SRC_FILES)

test:
	.venv/bin/pytest -n auto tests/

check: lint typecheck test

.PHONY: dev-deps lint typecheck test check
