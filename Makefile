PYTHON ?= python3
PYTHON_IMAGE ?= python:3.12.13-slim

.PHONY: infra-up infra-down infra-ps infra-logs infra-check infra-restart infra-reset remote-101-clickhouse-tunnel remote-101-clickhouse-tunnel-status quant-data-hub-build quant-data-hub-up quant-data-hub-down quant-data-hub-logs quant-data-hub-check quant-factor-lab-build quant-factor-lab-up quant-factor-lab-down quant-factor-lab-logs quant-factor-lab-check quant-factor-validation-build quant-factor-validation-up quant-factor-validation-down quant-factor-validation-logs quant-factor-validation-check quant-ops-api-build quant-ops-api-up quant-ops-api-down quant-ops-api-logs quant-ops-api-check quant-ops-web-build quant-ops-web-up quant-ops-web-down quant-ops-web-logs quant-ops-web-check smoke-quant-data-hub-101 smoke-quant-factor-validation-persistence test-quant-contracts test-quant-contracts-local test-quant-contracts-container test-quant-data-hub test-quant-data-hub-local test-quant-data-hub-container test-quant-data-sdk test-quant-data-sdk-local test-quant-data-sdk-container test-quant-factor-lab test-quant-factor-lab-local test-quant-factor-lab-container test-quant-factor-validation test-quant-factor-validation-local test-quant-factor-validation-container test-quant-ops-api test-quant-ops-api-local test-quant-ops-api-container test-quant-ops-web test-quant-ops-web-container test

infra-up:
	docker compose up -d postgres redis

infra-down:
	docker compose down

infra-ps:
	docker compose ps

infra-logs:
	docker compose logs -f postgres redis

infra-check:
	docker compose config --quiet
	docker compose exec postgres pg_isready -U $${POSTGRES_USER:-quant_admin} -d $${POSTGRES_DB:-quant_system}
	docker compose exec redis redis-cli ping

infra-restart:
	docker compose restart postgres redis

infra-reset:
	docker compose down -v

remote-101-clickhouse-tunnel:
	lsof -nP -iTCP:18123 -sTCP:LISTEN >/dev/null || ssh -fN -L 127.0.0.1:18123:127.0.0.1:18123 192.168.2.101

remote-101-clickhouse-tunnel-status:
	lsof -nP -iTCP:18123 -sTCP:LISTEN

quant-data-hub-build:
	docker compose build quant_data_hub

quant-data-hub-up:
	docker compose up -d quant_data_hub

quant-data-hub-down:
	docker compose stop quant_data_hub

quant-data-hub-logs:
	docker compose logs -f quant_data_hub

quant-data-hub-check:
	curl -sS -m 10 http://127.0.0.1:$${QUANT_DATA_HUB_PORT:-18000}/health

quant-factor-lab-build:
	docker compose build quant_factor_lab

quant-factor-lab-up:
	docker compose up -d quant_factor_lab

quant-factor-lab-down:
	docker compose stop quant_factor_lab

quant-factor-lab-logs:
	docker compose logs -f quant_factor_lab

quant-factor-lab-check:
	curl -sS -m 10 http://127.0.0.1:$${QUANT_FACTOR_LAB_PORT:-18010}/health

quant-factor-validation-build:
	docker compose build quant_factor_validation

quant-factor-validation-up:
	docker compose up -d quant_factor_validation

quant-factor-validation-down:
	docker compose stop quant_factor_validation

quant-factor-validation-logs:
	docker compose logs -f quant_factor_validation

quant-factor-validation-check:
	curl -sS -m 10 http://127.0.0.1:$${QUANT_FACTOR_VALIDATION_PORT:-18020}/health

quant-ops-api-build:
	docker compose build quant_ops_api

quant-ops-api-up:
	docker compose up -d quant_ops_api

quant-ops-api-down:
	docker compose stop quant_ops_api

quant-ops-api-logs:
	docker compose logs -f quant_ops_api

quant-ops-api-check:
	curl -sS -m 10 http://127.0.0.1:$${QUANT_OPS_API_PORT:-18030}/health

quant-ops-web-build:
	docker compose build quant_ops_web

quant-ops-web-up:
	docker compose up -d quant_ops_web

quant-ops-web-down:
	docker compose stop quant_ops_web

quant-ops-web-logs:
	docker compose logs -f quant_ops_web

quant-ops-web-check:
	curl -sS -m 10 http://127.0.0.1:$${QUANT_OPS_WEB_PORT:-18040}/

smoke-quant-data-hub-101:
	$(PYTHON) scripts/smoke_quant_data_hub_101.py

smoke-quant-factor-validation-persistence:
	docker compose exec -T quant_factor_validation python -m quant_factor_validation.tools.persistence_smoke

test-quant-contracts: test-quant-contracts-container

test-quant-contracts-local:
	PYTHONPATH=packages/quant_contracts/src $(PYTHON) -m unittest discover packages/quant_contracts/tests

test-quant-contracts-container:
	docker run --rm -e PIP_DISABLE_PIP_VERSION_CHECK=1 -e PIP_ROOT_USER_ACTION=ignore -v "$(CURDIR):/workspace" -w /workspace $(PYTHON_IMAGE) sh -c "python -m pip install -e packages/quant_contracts && python -m unittest discover packages/quant_contracts/tests"

test-quant-data-hub: test-quant-data-hub-container

test-quant-data-hub-local:
	PYTHONPATH=packages/quant_contracts/src:services/quant_data_hub/src $(PYTHON) -m unittest discover services/quant_data_hub/tests

test-quant-data-hub-container:
	docker run --rm -e PIP_DISABLE_PIP_VERSION_CHECK=1 -e PIP_ROOT_USER_ACTION=ignore -v "$(CURDIR):/workspace" -w /workspace $(PYTHON_IMAGE) sh -c "python -m pip install -e packages/quant_contracts -e 'services/quant_data_hub[test]' && python -m unittest discover services/quant_data_hub/tests"

test-quant-data-sdk: test-quant-data-sdk-container

test-quant-data-sdk-local:
	PYTHONPATH=packages/quant_contracts/src:clients/quant_data_sdk/src $(PYTHON) -m unittest discover clients/quant_data_sdk/tests

test-quant-data-sdk-container:
	docker run --rm -e PIP_DISABLE_PIP_VERSION_CHECK=1 -e PIP_ROOT_USER_ACTION=ignore -v "$(CURDIR):/workspace" -w /workspace $(PYTHON_IMAGE) sh -c "python -m pip install -e packages/quant_contracts -e 'clients/quant_data_sdk[test]' && python -m unittest discover clients/quant_data_sdk/tests"

test-quant-factor-lab: test-quant-factor-lab-container

test-quant-factor-lab-local:
	PYTHONPATH=packages/quant_contracts/src:clients/quant_data_sdk/src:services/quant_factor_lab/src $(PYTHON) -m unittest discover services/quant_factor_lab/tests

test-quant-factor-lab-container:
	docker run --rm -e PIP_DISABLE_PIP_VERSION_CHECK=1 -e PIP_ROOT_USER_ACTION=ignore -v "$(CURDIR):/workspace" -w /workspace $(PYTHON_IMAGE) sh -c "python -m pip install -e packages/quant_contracts -e clients/quant_data_sdk -e 'services/quant_factor_lab[test]' && python -m unittest discover services/quant_factor_lab/tests"

test-quant-factor-validation: test-quant-factor-validation-container

test-quant-factor-validation-local:
	PYTHONPATH=packages/quant_contracts/src:clients/quant_data_sdk/src:services/quant_factor_validation/src $(PYTHON) -m unittest discover services/quant_factor_validation/tests

test-quant-factor-validation-container:
	docker run --rm -e PIP_DISABLE_PIP_VERSION_CHECK=1 -e PIP_ROOT_USER_ACTION=ignore -v "$(CURDIR):/workspace" -w /workspace $(PYTHON_IMAGE) sh -c "python -m pip install -e packages/quant_contracts -e clients/quant_data_sdk -e 'services/quant_factor_validation[test]' && python -m unittest discover services/quant_factor_validation/tests"

test-quant-ops-api: test-quant-ops-api-container

test-quant-ops-api-local:
	PYTHONPATH=services/quant_ops_api/src $(PYTHON) -m unittest discover services/quant_ops_api/tests

test-quant-ops-api-container:
	docker run --rm -e PIP_DISABLE_PIP_VERSION_CHECK=1 -e PIP_ROOT_USER_ACTION=ignore -v "$(CURDIR):/workspace" -w /workspace $(PYTHON_IMAGE) sh -c "python -m pip install -e 'services/quant_ops_api[test]' && python -m unittest discover services/quant_ops_api/tests"

test-quant-ops-web: test-quant-ops-web-container

test-quant-ops-web-container:
	docker run --rm -v "$(CURDIR)/apps/quant_ops_web:/workspace" -v /workspace/node_modules -w /workspace node:22-alpine sh -c "npm ci && npm run typecheck"

test: test-quant-contracts test-quant-data-hub test-quant-data-sdk test-quant-factor-lab test-quant-factor-validation test-quant-ops-api test-quant-ops-web
