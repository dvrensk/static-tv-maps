# Static TV Maps — build automation
#
# Docker workflow (recommended):
#   make setup     build the Docker image
#   make data      download + process source geodata (needs network)
#   make maps      render every map into output/
#   make map M=spain-comunidades   render a single map
#   make shell     interactive shell inside the container
#
# Local workflow (venv, no Docker):
#   make local-setup
#   make local-maps
#
# Interactive label tuning ("el ajustador"):
#   make tune        Docker; open http://localhost:8321/
#   make local-tune  venv

IMAGE = static-tv-maps
DOCKER_RUN = docker run --rm -v $(PWD):/app -u $(shell id -u):$(shell id -g) $(IMAGE)
VENV = .venv
PY = $(VENV)/bin/python

.PHONY: help setup data maps maps-sobrio maps-galaxia map list shell clean unchurn local-setup local-data local-maps local-map tune local-tune test

help:
	@echo "Docker targets:  setup, data, maps, map M=<name>, list, shell, tune"
	@echo "Local targets:   local-setup, local-data, local-maps, local-map M=<name>, local-tune"
	@echo "Other:           test (tuner round-trip tests), clean (remove rendered maps)"
	@echo "                 unchurn (revert re-rendered images whose pixels didn't change; needs local-setup)"

setup:
	docker build -t $(IMAGE) .

data:
	$(DOCKER_RUN) python scripts/download_data.py

maps:
	$(DOCKER_RUN) python generate.py all

maps-sobrio:
	$(DOCKER_RUN) python generate.py all --theme sobrio

maps-galaxia:
	$(DOCKER_RUN) python generate.py all --theme galaxia

map:
	$(DOCKER_RUN) python generate.py $(M)

list:
	$(DOCKER_RUN) python generate.py --list

shell:
	docker run --rm -it -v $(PWD):/app $(IMAGE) bash

local-setup:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt

local-data:
	$(PY) scripts/download_data.py

local-maps:
	$(PY) generate.py all

local-map:
	$(PY) generate.py $(M)

# Interactive label tuning. The container needs the port published and the
# repo mounted so saves land in your working tree.
tune:
	docker run --rm -v $(PWD):/app -u $(shell id -u):$(shell id -g) \
		-p 8321:8321 $(IMAGE) python tune.py --host 0.0.0.0

local-tune:
	$(PY) tune.py

test:
	$(PY) -m pytest tests/ -q

clean:
	rm -f output/*.png output/*.jpg

# Runs on the host (needs git), so it uses the venv, not Docker.
unchurn:
	$(PY) scripts/unchurn.py
