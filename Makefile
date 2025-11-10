.DEFAULT_GOAL:=help
.ONESHELL:
.EXPORT_ALL_VARIABLES:
MAKEFLAGS += --no-print-directory

# Variables
DOCKER_COMPOSE_DEV = docker compose -f docker/docker-compose.dev.yml --project-name supporta-email-module
DOCKER_COMPOSE_PROD = docker compose -f docker/docker-compose.prod.yml --project-name supporta-email-module
DOCKER_COMPOSE_TEST = docker compose -f docker/docker-compose.tests.yml --project-name supporta-email-module
DOCKER = docker
ALEMBIC = alembic
UV = uv
PRE_COMMIT = pre-commit
PYTEST = pytest
RUFF = ruff
UVICORN = uvicorn
HYPERCORN = hypercorn
PYRIGHT = pyright

# Start the development environment
.PHONY: up-dev
up-dev:
	$(DOCKER_COMPOSE_DEV) up -d --build

# Stop the development environment
.PHONY: down-dev
down-dev:
	$(DOCKER_COMPOSE_DEV) down

# Start the production environment
.PHONY: up-prod
up-prod:
	$(DOCKER_COMPOSE_PROD) up -d --build

# Stop the production environment
.PHONY: down-prod
down-prod:
	$(DOCKER_COMPOSE_PROD) down

.PHONY: up-tests
up-tests:
	$(DOCKER_COMPOSE_TEST) up -d --build

.PHONY: down-tests
down-tests:
	$(DOCKER_COMPOSE_TEST) down

.PHONY: clear-tests
clear-tests: down-tests clear-db-tests

# Run database migrations
.PHONY: migrate
migrate:
	$(UV) run $(ALEMBIC) -x run_seeds=true upgrade head

# Create alembic migrations
.PHONY: migrations
migrations:
	$(UV) run $(ALEMBIC) revision --autogenerate

# Install dependencies using uv
.PHONY: install-deps
install-deps:
	$(UV) sync --all-extras --dev

# Perform linting on all files using ruff
.PHONY: lint
lint:
	$(UV) run $(RUFF) check --fix .

# Format all files using ruff format
.PHONY: format
format:
	$(UV) run $(RUFF) format .

# Run static type checking using pyright
.PHONY: type-check
type-check:
	$(UV) run $(PYRIGHT)

# Test the app (runs lint, format, and type-check first)
.PHONY: test
test: lint format type-check up-tests
	$(UV) run $(PYTEST) -v --durations=0 .
	$(MAKE) down-tests

.PHONY: verify
verify: format lint type-check

# Start the app using hypercorn
.PHONY: start
start:
	$(UV) run $(UVICORN) src.main:app --host 0.0.0.0 --port 8000 --no-access-log

# Create .env file from example.env on Unix systems
.PHONY: create-env-unix
create-env-unix:
	@if [ -f .env ]; then \
		echo ".env file already exists. Aborting to avoid overwriting."; \
	else \
		cp example.env .env; \
		echo ".env file created from example.env."; \
	fi

# Create .env file from example.env on Windows systems
.PHONY: create-env-windows
create-env-windows:
	@if exist .env ( \
		echo .env file already exists. Aborting to avoid overwriting. \
	) else ( \
		copy example.env .env && \
		echo .env file created from example.env. \
	)

# Initialize the project on Unix systems (install dependencies, create .env file)
.PHONY: uinit
uinit: install-deps create-env-unix
	@echo "Project initialized for Unix systems."

# Initialize the project on Windows systems (install dependencies, create .env file)
.PHONY: winit
winit: install-deps create-env-windows
	@echo "Project initialized for Windows systems."

# Start the development environment and the app
.PHONY: dev
dev: up-dev

# Clear db
.PHONY: clear-db
clear-db:
	$(DOCKER) volume rm docker_pgdata

# Clear db
.PHONY: clear-db-tests
clear-db-tests:
	$(DOCKER) volume rm docker_pgdata_tests


# Read client emails
.PHONY: read-client-emails
read-client-emails:
	$(UV) run python scripts/read_client_emails.py

# Read support emails
.PHONY: read-support-emails
read-support-emails:
	$(UV) run python scripts/read_support_emails.py

# Send complaint email
.PHONY: send-complaint
send-complaint:
	$(UV) run python scripts/send_complaint_email.py
