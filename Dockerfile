FROM python:3.14-slim

LABEL org.opencontainers.image.title="Sentinel Content Safety Platform" \
    org.opencontainers.image.description="Production-oriented multimodal moderation API" \
    org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

ARG PYTORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --index-url "${PYTORCH_CPU_INDEX_URL}" \
    "torch>=2.7,<3.0" "torchvision>=0.22,<1.0"
RUN pip install --no-cache-dir ".[inference,distributed,threat-intelligence,multimodal]"

RUN addgroup --system sentinel \
    && adduser --system --ingroup sentinel --home /home/sentinel sentinel \
    && mkdir -p /app/artifacts/review /home/sentinel/.cache \
    && chown -R sentinel:sentinel /app/artifacts/review /home/sentinel

EXPOSE 8000 9101

USER sentinel

CMD ["uvicorn", "sentinel.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
