.DEFAULT_GOAL := help
PYTHON := .venv/bin/python
UV_CACHE_DIR := $(CURDIR)/.cache/uv
export UV_CACHE_DIR
export TITLE ELAPSED REMAINING TRACK AUDIO SPEECH_LANGUAGE FIRST LAST THROUGH

.PHONY: help setup setup-dev download-model doctor position progress transcribe test lint format lock lock-check check check-public clean clean-transcripts clean-audio clean-cache

help:
	@printf '%s\n' \
	  'make setup                 Create .venv and install dependencies (network setup)' \
	  'make setup-dev             Create .venv and install development tools only (network setup)' \
	  'make download-model        Cache the speech model (network setup, about 1.6 GB)' \
	  'make doctor                Show local tool/runtime readiness without book text' \
	  'make position              Validate progress and list only begun tracks' \
	  'make progress TITLE="..." ELAPSED=MM:SS REMAINING=MM:SS [AUDIO=path] [TRACK=N] [SPEECH_LANGUAGE=code]' \
	  '  AUDIO is required on first setup; language detection is automatic unless specified.' \
	  'make transcribe FIRST=N LAST=M [THROUGH=MM:SS]  Fresh offline transcription' \
	  'make test                  Run boundary, journal, and cleanup tests; no model required' \
	  'make lint                  Check formatting and lint rules (needs setup-dev)' \
	  'make format                Apply formatting and safe lint fixes' \
	  'make check                 Run lint, tests, and the public file inventory check' \
	  'make lock                  Recompile the hashed lockfiles from companion/*.in (network)' \
	  'make lock-check            Fail if a lockfile does not match its .in file (network)' \
	  'make check-public          Check tracked/addable paths before staging' \
	  'make clean-transcripts     Delete all derived transcripts, keeping audio and progress' \
	  'make clean-audio           Delete only extracted sample audio' \
	  'make clean                 Delete transcripts and samples; preserve journals, cache, progress' \
	  'make clean-cache           Delete model/dependency cache; download-model needed afterward'

setup:
	@test -x "$(PYTHON)" || uv venv --python python3 .venv
	uv pip install --python "$(PYTHON)" --require-hashes -r companion/requirements.txt

setup-dev:
	@test -x "$(PYTHON)" || uv venv --python python3 .venv
	uv pip install --python "$(PYTHON)" --require-hashes -r companion/requirements-dev.txt

download-model:
	"$(PYTHON)" companion/download_model.py

doctor:
	"$(PYTHON)" companion/tasks.py doctor

position:
	"$(PYTHON)" companion/position.py show

progress:
	"$(PYTHON)" companion/tasks.py progress

transcribe:
	"$(PYTHON)" companion/tasks.py transcribe

test:
	"$(PYTHON)" -m unittest discover -s companion -p 'test_*.py'

lint:
	"$(PYTHON)" -m ruff format --check companion
	"$(PYTHON)" -m ruff check companion

format:
	"$(PYTHON)" -m ruff format companion
	"$(PYTHON)" -m ruff check --fix companion

# The runtime lock targets Apple silicon on macOS 14 or newer, the oldest release that
# current MLX wheels support. Existing pins are kept; add --upgrade to move them.
LOCK_DIR ?= companion
lock:
	MACOSX_DEPLOYMENT_TARGET=14.0 uv pip compile --quiet --python-platform aarch64-apple-darwin \
	  --python-version 3.11 --generate-hashes --custom-compile-command 'make lock' \
	  companion/requirements.in -o $(LOCK_DIR)/requirements.txt
	uv pip compile --quiet --universal --python-version 3.11 --generate-hashes \
	  --custom-compile-command 'make lock' companion/requirements-dev.in -o $(LOCK_DIR)/requirements-dev.txt

lock-check:
	@dir=$$(mktemp -d) && cp companion/requirements.txt companion/requirements-dev.txt "$$dir"/ && \
	  $(MAKE) --no-print-directory lock LOCK_DIR="$$dir" && \
	  diff -u companion/requirements.txt "$$dir"/requirements.txt && \
	  diff -u companion/requirements-dev.txt "$$dir"/requirements-dev.txt && \
	  echo 'Lockfiles match their .in files.'

check: lint test check-public

check-public:
	"$(PYTHON)" companion/check_public.py

clean:
	"$(PYTHON)" companion/tasks.py clean-transcripts
	"$(PYTHON)" companion/tasks.py clean-audio

clean-transcripts:
	"$(PYTHON)" companion/tasks.py clean-transcripts

clean-audio:
	"$(PYTHON)" companion/tasks.py clean-audio

clean-cache:
	"$(PYTHON)" companion/tasks.py clean-cache
