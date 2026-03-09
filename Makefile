.PHONY: dev backend frontend install install-backend install-frontend lint format

VENV = .venv/bin
PYTHON = $(VENV)/python

# Run both backend and frontend concurrently
dev:
	@echo "Starting backend (port 8001) + frontend (port 5177)..."
	@make backend & make frontend & wait

backend:
	$(PYTHON) -m backend

frontend:
	cd app && npm run dev

install: install-backend install-frontend

install-backend:
	python3 -m venv .venv
	$(VENV)/pip install -r backend/requirements.txt

install-frontend:
	cd app && npm install

lint:
	$(VENV)/ruff check backend/
	cd app && npm run lint

format:
	$(VENV)/ruff format backend/
