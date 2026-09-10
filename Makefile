.PHONY: up down test lint format migrate migration-check logs
up:
	docker compose up --build -d --wait
down:
	docker compose --profile test down
test:
	docker compose --profile test run --build --rm test
lint:
	docker compose --profile test run --build --rm --no-deps test ruff check --no-cache app tests scripts alembic
	docker compose --profile test run --rm --no-deps test ruff format --check app tests scripts alembic
format:
	.venv/bin/ruff check --fix .
	.venv/bin/ruff format .
migrate:
	docker compose run --rm migrate
migration-check:
	docker compose run --rm migrate alembic check
logs:
	docker compose logs -f api
