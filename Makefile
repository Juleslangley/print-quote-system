BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000

.PHONY: up down reset logs ps health doctor

up:
	docker compose up --build -d

down:
	docker compose down

reset:
	docker compose down -v
	docker compose up --build -d

logs:
	docker compose logs -f

ps:
	docker compose ps

# Container status (JSON format)
health:
	docker compose ps --format json | cat

# Stack readiness: ps + curl backend health + curl frontend; clear PASS/FAIL
doctor:
	@echo "=== Docker Compose status ==="
	@docker compose ps
	@echo ""
	@echo "=== Backend health (http://localhost:$(BACKEND_PORT)/api/health) ==="
	@curl -fsS -o /dev/null http://localhost:$(BACKEND_PORT)/api/health 2>/dev/null && echo "PASS" || echo "FAIL (backend down or not ready)"
	@echo "=== Frontend (http://localhost:$(FRONTEND_PORT)) ==="
	@curl -fsS -o /dev/null http://localhost:$(FRONTEND_PORT)/ 2>/dev/null && echo "PASS" || echo "FAIL (frontend down or not ready)"
