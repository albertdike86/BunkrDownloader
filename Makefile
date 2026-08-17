# Makefile using uv with pyproject.toml
# Examples:
#   make sync
#   make run-batch
#   make run-single URL="https://bunkr.si/a/PUK068QE" EXTRA="--ignore .zip"

UV := uv
PY := uv run python

# Keep native environments separate when one checkout is shared by Windows and
# WSL/Linux. uv creates the selected environment from pyproject.toml and uv.lock.
ifeq ($(OS),Windows_NT)
UV_ENV := .venv-windows
else
UV_ENV := .venv-unix
endif
export UV_PROJECT_ENVIRONMENT := $(UV_ENV)

.DEFAULT_GOAL := run-batch

.PHONY: sync
sync:
	@echo "Syncing environment with uv..."
	$(UV) sync

.PHONY: run-batch
run-batch: sync
	$(PY) main.py

.PHONY: run-single
run-single: sync
ifndef URL
	$(error You must provide URL, for example: make run-single URL="https://bunkr.si/a/PUK068QE")
endif
	$(PY) downloader.py $(URL) $(EXTRA)

.PHONY: help
help:
	@echo ""
	@echo "Usage:"
	@echo "  make sync          Create or update the uv environment from pyproject.toml"
	@echo "  make               Build for this OS and run main.py"
	@echo "  make run-batch     Build for this OS and run main.py"
	@echo "  make run-single    Run downloader.py for one URL (provide URL=...)"
	@echo ""
