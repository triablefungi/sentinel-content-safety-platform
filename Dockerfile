FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir ".[inference,distributed,threat-intelligence,multimodal]"

EXPOSE 8000 9101

CMD ["uvicorn", "sentinel.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
