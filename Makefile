# Shortcuts for live-interpreter. `make help` lists them.
# Variables: LANG_IN=auto|de|fr|... (spoken language)  PROMPT="names, products"
#            MODEL=auto|small|medium  TO=de PERSONAL=1 (with `make language`)
#            FILE=clip.mp3  ARGS="--speed 1.25 ..." (extra flags, see: make options)

PY      := .venv/bin/python
LANG_IN ?= auto
MODEL   ?= auto
PROMPT  ?=
FILE    ?=
ARGS    ?=
APP     := $(PY) -m live_interpreter
RUN     := $(APP) run --language $(LANG_IN) --model $(MODEL) \
           $(if $(PROMPT),--prompt "$(PROMPT)") $(ARGS)
UNAME   := $(shell uname)
CONF    := .interpreter.conf

.PHONY: help install language audio route audio-undo run run-de run-fast subtitles test options check check-venv

help:            ## Show this help
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

install:         ## One-time setup: audio tools, .venv, voice, your language
	bash install.sh
	@test -f $(CONF) || $(APP) language

language: check-venv ## Change the language you hear: make language [TO=de] [PERSONAL=1]
	$(APP) language $(TO) $(if $(PERSONAL),--personal-use)

# First run: ask which language the listener wants (default English)
$(CONF):
	@$(MAKE) -s check-venv
	$(APP) language

audio:           ## Linux: create MeetingOut sink + loopback (macOS: prints setup steps)
ifeq ($(UNAME),Darwin)
	@echo "macOS: audio is set up once in Audio MIDI Setup, see README 'macOS'."
else
	bash setup_audio.sh
endif

route:           ## Linux: move playing browser audio into MeetingOut (start the video first)
ifneq ($(UNAME),Darwin)
	@bash setup_audio.sh --route
endif

audio-undo:      ## Linux: remove MeetingOut and restore normal audio
ifneq ($(UNAME),Darwin)
	bash setup_audio.sh --undo
endif

run: check-venv $(CONF) ## Live interpreter (any language -> your language)
	$(RUN)

run-de: check-venv $(CONF) ## Live, meeting is in German (more robust detection)
	$(MAKE) run LANG_IN=de

run-fast: check-venv $(CONF) ## Live with the small model: ~2x faster, less accurate
	$(MAKE) run MODEL=small

subtitles: check-venv $(CONF) ## Live, text only (no voice)
	$(RUN) --no-tts

test: check-venv $(CONF) ## Test with an audio/video file: make test FILE=clip.mp3
	@test -n "$(FILE)" || { echo "Usage: make test FILE=clip.mp3"; exit 1; }
	$(RUN) --input-file "$(FILE)"

options: check-venv ## List all interpreter options (use them via ARGS="...")
	@$(APP) run --help

check: check-venv ## Run the unit tests (no models needed)
	@$(PY) -m pytest --version >/dev/null 2>&1 || $(PY) -m pip install -q -r requirements-dev.txt
	$(PY) -m pytest -q

check-venv:
	@test -x $(PY) || { echo "Run 'make install' first."; exit 1; }
