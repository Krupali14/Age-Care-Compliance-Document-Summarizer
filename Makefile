.PHONY: up down build logs migrate seed clean restart

up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

migrate:
	docker compose exec backend alembic upgrade head

seed:
	@echo "Seed script not implemented yet."

clean:
	docker compose down -v --rmi local --remove-orphans

restart: down up
