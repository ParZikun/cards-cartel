# Makefile for managing local and production Docker environments

.PHONY: help local-up local-down local-logs local-clean prod-up prod-down prod-logs

.DEFAULT_GOAL := help

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  local-up        - Start the local environment in detached mode (uses .env.local)."
	@echo "  local-down      - Stop the local environment."
	@echo "  local-logs      - View logs for the local environment."
	@echo "  local-clean     - Stop the local environment and remove all associated volumes (deletes DB data)."
	@echo ""
	@echo "  prod-up         - Start the production environment in detached mode (uses .env)."
	@echo "  prod-down       - Stop the production environment."
	@echo "  prod-logs       - View logs for the production environment."

# --- Local Environment Commands ---
migrate:
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
prod-up:
	@echo "Starting production environment..."
	docker-compose -f docker-compose.yml up --build -d

prod-down:
	@echo "Stopping production environment..."
	docker-compose -f docker-compose.yml down

prod-logs:
	@echo "Showing logs for production environment..."
	docker-compose -f docker-compose.yml logs -f
