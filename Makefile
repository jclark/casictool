SRC_FILES=casictool.py
TEST_FILES=tests/

dev-deps:
	.venv/bin/pip install -e ".[dev]"

lint:
	.venv/bin/ruff check $(SRC_FILES)

typecheck:
	.venv/bin/mypy $(SRC_FILES) $(TEST_FILES)

test:
	.venv/bin/pytest -n auto $(TEST_FILES)

check: lint typecheck test

.PHONY: dev-deps lint typecheck test check
