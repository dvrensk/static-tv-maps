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

IMAGE = static-tv-maps
DOCKER_RUN = docker run --rm -v $(PWD):/app -u $(shell id -u):$(shell id -g) $(IMAGE)
VENV = .venv
PY = $(VENV)/bin/python

.PHONY: help setup data maps maps-sobrio map list shell clean local-setup local-data local-maps local-map

help:
	@echo "Docker targets:  setup, data, maps, map M=<name>, list, shell"
	@echo "Local targets:   local-setup, local-data, local-maps, local-map M=<name>"
	@echo "Other:           clean (remove rendered maps)"

setup:
	docker build -t $(IMAGE) .

data:
	$(DOCKER_RUN) python scripts/download_data.py

maps:
	$(DOCKER_RUN) python generate.py all

maps-sobrio:
	$(DOCKER_RUN) python generate.py all --theme sobrio

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

clean:
	rm -f output/*.png output/*.jpg
