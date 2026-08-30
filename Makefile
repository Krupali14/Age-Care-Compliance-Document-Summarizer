.PHONY: up down build logs migrate seed clean restart setup

ifeq ($(OS),Windows_NT)
# Windows: GNU make would default to cmd.exe; force PowerShell so no sed/chmod needed.
SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command

setup:
	@if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "created .env from .env.example" }
	@$$c = Get-Content .env -Raw; if ($$c -match 'JWT_SECRET=changeme') { $$s = -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) }); Set-Content .env (($$c -replace 'JWT_SECRET=.*', "JWT_SECRET=$$s")) -NoNewline; Write-Host "generated JWT_SECRET" }
	@New-Item -ItemType Directory -Force -Path backend/uploads | Out-Null
	@# ponytail: chmod is a no-op on Windows; Docker Desktop mounts are already writable.

else

setup:
	@[ -f .env ] || { cp .env.example .env; echo "created .env from .env.example"; }
	@if grep -q '^JWT_SECRET=changeme' .env; then \
		s=$$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'); \
		sed -i.bak "s|^JWT_SECRET=.*|JWT_SECRET=$$s|" .env && rm -f .env.bak; \
		echo "generated JWT_SECRET"; \
	fi
	@mkdir -p backend/uploads && chmod -R u+rwX backend/uploads
	@find . -name '*.sh' -not -path './node_modules/*' -not -path './*/node_modules/*' -exec chmod +x {} + 2>/dev/null || true

endif

up: setup
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
