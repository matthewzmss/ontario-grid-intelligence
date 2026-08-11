.PHONY: up down logs etl spark test clean dashboard db-shell

# ── Docker ──
up:
	docker-compose -f docker/docker-compose.yml up -d
	@echo "✅ PostgreSQL: localhost:5432 | Dashboard: http://localhost:8501"

down:
	docker-compose -f docker/docker-compose.yml down

logs:
	docker-compose -f docker/docker-compose.yml logs -f

# ── Step 1: Extract ──
etl:
	python -m etl.run_pipeline

etl-historical:
	python -m etl.run_pipeline --historical

# ── Steps 2-4: Transform (PySpark) ──
spark-bronze:
	python spark_jobs/bronze_ingestion.py

spark-silver:
	python spark_jobs/bronze_to_silver.py

spark-gold:
	python spark_jobs/silver_to_gold.py

spark-all:
	python spark_jobs/bronze_ingestion.py && python spark_jobs/bronze_to_silver.py && python spark_jobs/silver_to_gold.py

# ── Step 5: Load to PostgreSQL ──
load-postgres:
	python spark_jobs/gold_to_postgres.py

# ── Step 6: Dashboard ──
dashboard:
	@open http://localhost:8501 2>/dev/null || echo "Visit http://localhost:8501"

# ── Database ──
db-shell:
	docker exec -it ontario-grid-postgres psql -U grid_admin -d ontario_grid

# ── Cleanup ──
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# ── Full Pipeline (all steps) ──
run-all: etl spark-all load-postgres
	@echo "✅ Full pipeline complete"
