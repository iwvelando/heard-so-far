.DEFAULT_GOAL := help
PYTHON := .venv/bin/python
UV_CACHE_DIR := $(CURDIR)/.cache/uv
export UV_CACHE_DIR
export TITLE ELAPSED REMAINING TRACK AUDIO SPEECH_LANGUAGE FIRST LAST THROUGH

.PHONY: help setup download-model doctor position progress transcribe test check check-public clean clean-transcripts clean-audio clean-cache

help:
	@printf '%s\n' \
	  'make setup                 Create .venv and install dependencies (network setup)' \
	  'make download-model        Cache the speech model (network setup, about 1.6 GB)' \
	  'make doctor                Show local tool/runtime readiness without book text' \
	  'make position              Validate progress and list only begun tracks' \
	  'make progress TITLE="..." ELAPSED=MM:SS REMAINING=MM:SS [AUDIO=path] [TRACK=N] [SPEECH_LANGUAGE=code]' \
	  '  AUDIO is required on first setup; language detection is automatic unless specified.' \
	  'make transcribe FIRST=N LAST=M [THROUGH=MM:SS]  Fresh offline transcription' \
	  'make test                  Run boundary, journal, and cleanup tests; no model required' \
	  'make check                 Run tests and check the public file inventory' \
	  'make check-public          Check tracked/addable paths before staging' \
	  'make clean-transcripts     Delete all derived transcripts, keeping audio and progress' \
	  'make clean-audio           Delete only extracted sample audio' \
	  'make clean                 Delete transcripts and samples; preserve journals, cache, progress' \
	  'make clean-cache           Delete model/dependency cache; download-model needed afterward'

setup:
	@test -x "$(PYTHON)" || uv venv --python python3 .venv
	uv pip install --python "$(PYTHON)" -r companion/requirements.txt

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

check: test check-public

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
