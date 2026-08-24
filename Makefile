.PHONY: install run worker test lint docker-up load-test

install:
	python -m pip install -e ".[dev,ml]"

run:
	uvicorn sentinel.main:app --app-dir src --reload

worker:
	python -m sentinel.worker

test:
	pytest

lint:
	ruff check .

docker-up:
	docker compose up --build

load-test:
	python scripts/load_test_async.py --requests 100 --concurrency 10

download-data:
	python scripts/download_data.py --sample-size 20000

train-baseline:
	python scripts/train_baseline.py

train-transformer:
	python scripts/train_transformer.py
