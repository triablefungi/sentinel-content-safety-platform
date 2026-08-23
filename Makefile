.PHONY: install run test lint docker-up

install:
	python -m pip install -e ".[dev,ml]"

run:
	uvicorn sentinel.main:app --app-dir src --reload

test:
	pytest

lint:
	ruff check .

docker-up:
	docker compose up --build

download-data:
	python scripts/download_data.py --sample-size 20000

train-baseline:
	python scripts/train_baseline.py
