PYTHON ?= python3
PYTHON_IMAGE ?= python:3.12.13-slim

.PHONY: infra-up infra-down infra-ps infra-logs infra-check infra-restart infra-reset test-quant-contracts test-quant-contracts-local test-quant-contracts-container test-quant-data-hub test-quant-data-hub-local test-quant-data-hub-container test

infra-up:
	docker compose up -d postgres redis

infra-down:
	docker compose down

infra-ps:
	docker compose ps

infra-logs:
	docker compose logs -f postgres redis

infra-check:
	docker compose config
	docker compose exec postgres pg_isready -U $${POSTGRES_USER:-quant_admin} -d $${POSTGRES_DB:-quant_system}
	docker compose exec redis redis-cli ping

infra-restart:
	docker compose restart postgres redis

infra-reset:
	docker compose down -v

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

test: test-quant-contracts test-quant-data-hub
