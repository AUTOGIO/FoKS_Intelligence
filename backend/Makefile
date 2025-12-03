.PHONY: help install test lint format type-check clean run dev

help:
	@echo "FoKS Intelligence - Development Commands"
	@echo ""
	@echo "  make install     - Install dependencies"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linters (ruff)"
	@echo "  make format      - Format code (black)"
	@echo "  make type-check   - Run type checker (mypy)"
	@echo "  make clean       - Clean cache files"
	@echo "  make run         - Run development server"
	@echo "  make dev         - Run all checks (lint + format + type-check + test)"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	ruff check app/ tests/

format:
	black app/ tests/
	ruff check --fix app/ tests/

type-check:
	mypy app/ --ignore-missing-imports

clean:
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

dev: format lint type-check test

