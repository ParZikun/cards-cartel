# Makefile for managing local and production Docker environments

.PHONY: help local-up local-down local-logs local-clean prod-migrate prod-up prod-down prod-logs prod-clean

.DEFAULT_GOAL := help

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Local Environment Targets:"
	@echo "  local-migrate    - Build images and run the database migration for local."
	@echo "  local-up        - Start local services (postgres, worker)."
	@echo "  local-down      - Stop local services."
	@echo "  local-logs      - View logs for local services."
	@echo "  local-clean     - Stop local services and remove all associated volumes (deletes DB data)."
	@echo "  local-restart   - Restart local services."
	@echo ""
	@echo "Production Environment Targets:"
	@echo "  prod-migrate    - Build images and run the database migration for production."
	@echo "  prod-up         - Start production services (worker)."
	@echo "  prod-down       - Stop production services."
	@echo "  prod-logs       - View logs for production services."
	@echo "  prod-clean      - Stop production services and remove all associated volumes."
	@echo "  prod-analyze    - Analyze ALL ME and DB listings and update database."


# --- Local Environment Commands ---
local-migrate:
	@echo "Starting postgres and running database migration..."
	docker-compose -f docker-compose.local.yml up --build -d postgres
	@echo "Waiting for postgres to be healthy..."
	@until [ "$$(docker inspect -f '{{.State.Health.Status}}' postgres-local)" = "healthy" ]; do \
		sleep 1; \
	done;
	python -m scripts.migrate_prod_to_postgres
	@echo "Starting remaining services..."
	docker-compose -f docker-compose.local.yml up --build -d worker api

local-up:
	@echo "Starting local environment with postgres and worker..."
	docker-compose -f docker-compose.local.yml up --build -d postgres worker api

local-down:
	@echo "Stopping local environment..."
	docker-compose -f docker-compose.local.yml down

local-logs:
	@echo "Showing logs for local environment..."
	docker-compose -f docker-compose.local.yml logs -f

local-clean:
	@echo "Stopping local environment and removing volumes..."
	docker-compose -f docker-compose.local.yml down --volumes

local-analyze:
	@echo "Running analysis of all ME and DB listings to update database..."
	docker-compose -f docker-compose.local.yml run --rm worker python -m scripts.update_database_listings
	@echo "Analysis complete."

migrate-local:
	@echo "Applying migrations..."
	@cat migrations/*.sql | docker exec -i postgres-local psql -U postgres -d cards_cartel_db
	@echo "Migrations applied successfully."

local-restart:
	@echo "Restarting local environment..."
	docker-compose -f docker-compose.local.yml restart

# Helper to add a user to the whitelist
# Usage: make add-user WALLET=... TIER=...
add-user:
	@if [ -z "$(WALLET)" ]; then \
		echo "Error: WALLET argument is required. Usage: make add-user WALLET=<address> [TIER=NORMAL|GOLD]"; \
		exit 1; \
	fi
	docker exec -it sniper-worker-local python scripts/manage_users.py add $(WALLET) --tier $(or $(TIER),NORMAL)

# Helper to list all users
list-users:
	docker exec -it sniper-worker-local python scripts/manage_users.py list

# --- Production Environment Commands ---
prod-migrate:
	@echo "Building production images..."
	docker-compose -f docker-compose.prod.yml build worker
	@echo "Running production database migration..."
	docker-compose -f docker-compose.prod.yml run --rm worker python scripts/migrate_prod_to_postgres.py
	@echo "Migration complete."

prod-up:
	@echo "Starting production environment..."
	docker-compose -f docker-compose.prod.yml up --build -d

prod-down:
	@echo "Stopping production environment..."
	docker-compose -f docker-compose.prod.yml down

prod-logs:
	@echo "Showing logs for production environment..."
	docker-compose -f docker-compose.prod.yml logs -f

prod-clean:
	@echo "Stopping production environment and removing volumes..."
	docker-compose -f docker-compose.prod.yml down --volumes

prod-analyze:
	@echo "Running analysis of all ME and DB listings to update database..."
	docker-compose -f docker-compose.prod.yml run --rm worker python -m scripts.update_database_listings
	@echo "Analysis complete."

migrate-prod:
	@echo "Applying migrations to Production (Azure)..."
	@cat migrations/*.sql | docker run --rm -i --env-file .env postgres:13 sh -c 'export PGPASSWORD=$$POSTGRES_PASSWORD; psql -h $$POSTGRES_HOST -U $$POSTGRES_USER -d $$POSTGRES_DB'
	@echo "Migrations applied successfully."

prod-restart:
	@echo "Restarting production environment..."
	docker-compose -f docker-compose.prod.yml restart