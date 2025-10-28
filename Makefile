# Makefile for managing local and production Docker environments

.PHONY: help local-up local-down local-logs prod-up prod-down prod-logs

.DEFAULT_GOAL := help

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  local-up        - Start the local environment in detached mode (uses .env.local)."
	@echo "  local-down      - Stop the local environment."
	@echo "  local-logs      - View logs for the local environment."
	@echo ""
	@echo "  prod-up         - Start the production environment in detached mode (uses .env)."
	@echo "  prod-down       - Stop the production environment."
	@echo "  prod-logs       - View logs for the production environment."

# --- Local Environment Commands ---
local-up:
	@echo "Starting local environment..."
	docker-compose -f docker-compose.local.yml up --build -d

local-down:
	@echo "Stopping local environment..."
	docker-compose -f docker-compose.local.yml down

local-logs:
	@echo "Showing logs for local environment..."
	docker-compose -f docker-compose.local.yml logs -f

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
