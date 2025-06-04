# Copyright 2025 highstreet technologies USA Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

.PHONY: run clean venv deps debug-validation regen-models check-config viz-start viz-stop

PYTHON := $(shell pyenv which python3.12 2>/dev/null || which python3)
VENV_DIR := .venv
VENV_BIN := $(VENV_DIR)/bin
VENV_PY := $(VENV_DIR)/bin/python
REQUIREMENTS := requirements.txt
PYTHONPATH := src

# Environment variables for OpenDaylight controller
ODL_CONTROLLER_BASE_URL ?= https://odlux.oam.smo.o-ran-sc.org
ODL_CONTROLLER_USERNAME ?= admin
ODL_CONTROLLER_PASSWORD ?= Kp8bJ4SXszM0WXlhak3eHlcse2gAw84vaoGGmJvUy2U

# Environment variables for simulator
SIMULATOR_COMPOSE_FILE ?= src/hybrid_mplane_test_runner/tools/simulator/docker-compose.yaml
SIMULATOR_SERVICE_NAME ?= pynts-o-ru-hybrid
SIMULATOR_WAIT_TIME ?= 60

# Environment variables for visualization
VISUALIZATION_COMPOSE_FILE ?= visualization/docker-compose.yml

export ODL_CONTROLLER_BASE_URL
export ODL_CONTROLLER_USERNAME
export ODL_CONTROLLER_PASSWORD
export SIMULATOR_COMPOSE_FILE
export SIMULATOR_SERVICE_NAME
export SIMULATOR_WAIT_TIME
export VISUALIZATION_COMPOSE_FILE

check-python-version:
	@PY_VERSION=$$($(PYTHON) -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'); \
	REQUIRED="3.11"; \
	echo "Detected Python version: $$PY_VERSION"; \
	if [ "$$(printf '%s\n' $$REQUIRED $$PY_VERSION | sort -V | head -n1)" != "$$REQUIRED" ]; then \
		echo "❌ Python >= $$REQUIRED is required. Found $$PY_VERSION."; \
		exit 1; \
	fi

run: $(VENV_PY)
	@echo "Running test case with controller at $(ODL_CONTROLLER)..."
	@echo "Simulator: $(SIMULATOR_SERVICE_NAME) using $(SIMULATOR_COMPOSE_FILE)"
	USE_SIMULATOR=false PYTHONPATH=src $(VENV_PY) -m hybrid_mplane_test_runner.runner.main

venv: check-python-version
	@echo "🐍 Creating virtual environment..."
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "⬆️  Upgrading pip and setuptools..."
	$(VENV_PY) -m pip install --upgrade pip setuptools
ifneq ("$(wildcard $(REQUIREMENTS))","")
	@echo "Installing dependencies from $(REQUIREMENTS)..."
	$(VENV_PY) -m pip install -r $(REQUIREMENTS)
endif
	@echo "Virtual environment ready in $(VENV_DIR)"

clean:
	@echo "Cleaning output directory..."
	rm -rf output/*.json
	rm -rf output/*.log
	rm -rf output/*.zip

debug-validation:
	PYTHONPATH=src $(VENV_PY) output/validate_result_verbose.py output/results*.json schema/o-ran-test-results-schema.json

#regen-models:
#	@echo "📦 Generating Pydantic models..."
#	@.venv/bin/datamodel-codegen \
#	  --input schema/o-ran-test-results-schema.json \
#	  --input-file-type jsonschema \
#	  --output src/hybrid_mplane_test_runner/models/testresult_models.py
#	@echo "Patching __root__ to RootModel..."
#	@PYTHONPATH=src $(VENV_PY) src/hybrid_mplane_test_runner/tools/scripts/patch_rootmodels.py

check-config: $(VENV_PY)
	@echo "Checking configuration loading..."
	@PYTHONPATH=src $(VENV_PY) src/hybrid_mplane_test_runner/tools/scripts/check_config.py

viz-start:
	@echo "Starting visualization services (Grafana and TimescaleDB)..."
	@docker compose -f $(VISUALIZATION_COMPOSE_FILE) up -d
	@echo "Visualization services started. Grafana is available at http://localhost:3000"

viz-stop:
	@echo "Stopping visualization services..."
	@docker compose -f $(VISUALIZATION_COMPOSE_FILE) down --volumes
	@docker compose -f $(VISUALIZATION_COMPOSE_FILE) down
	@echo "Visualization services stopped"
