.PHONY: build up down test smoke

.DEFAULT_GOAL := build

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

test:
	@if [ -x application/catalog-api/.venv/bin/pytest ]; then \
		cd application/catalog-api && .venv/bin/pytest -q; \
	else \
		cd application/catalog-api && python3 -m pytest -q; \
	fi

smoke:
	bash scripts/smoke-test.sh
