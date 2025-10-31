# Makefile for managing local and production Docker environments

.PHONY: help local-up local-down local-logs local-clean prod-migrate prod-up prod-down prod-logs prod-clean

.DEFAULT_GOAL := help

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Local Environment Targets:"
	@echo "  local-migrate    - Build images and run the database migration for local."
	@echo "  local-up        - Start local services (postgres, worker, jaeger)."
	@echo "  local-down      - Stop local services."
	@echo "  local-logs      - View logs for local services."
	@echo "  local-clean     - Stop local services and remove all associated volumes (deletes DB data)."
	@echo ""
	@echo "Production Environment Targets:"
	@echo "  prod-migrate    - Build images and run the database migration for production."
	@echo "  prod-up         - Start production services (worker, jaeger)."
	@echo "  prod-down       - Stop production services."
	@echo "  prod-logs       - View logs for production services."
	@echo "  prod-clean      - Stop production services and remove all associated volumes."


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
	docker-compose -f docker-compose.local.yml up --build -d worker jaeger

local-up:
	@echo "Starting local environment with postgres, worker, jaeger and api..."
	docker-compose -f docker-compose.local.yml up --build -d postgres worker jaeger

local-down:
	@echo "Stopping local environment..."
	docker-compose -f docker-compose.local.yml down

local-logs:
	@echo "Showing logs for local environment..."
	docker-compose -f docker-compose.local.yml logs -f

local-clean:
	@echo "Stopping local environment and removing volumes..."
	docker-compose -f docker-compose.local.yml down --volumes

# --- Production Environment Commands ---
prod-migrate:
	@echo "Building production images..."
	docker-compose -f docker-compose.prod.yml build worker
	@echo "Running production database migration..."
	docker-compose -f docker-compose.prod.yml run --rm worker python scripts/migrate_prod_to_postgres.py
	@echo "Migration complete."

prod-up:
	@echo "Starting production environment..."
	docker-compose -f docker-compose.prod.yml up -d

prod-down:
	@echo "Stopping production environment..."
	docker-compose -f docker-compose.prod.yml down

prod-logs:
	@echo "Showing logs for production environment..."
	docker-compose -f docker-compose.prod.yml logs -f

prod-clean:
	@echo "Stopping production environment and removing volumes..."
	docker-compose -f docker-compose.prod.yml down --volumes
