.PHONY: infra-up infra-down infra-ps infra-logs infra-check infra-restart infra-reset

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
