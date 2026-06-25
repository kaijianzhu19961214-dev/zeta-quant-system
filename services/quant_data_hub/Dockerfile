FROM python:3.12.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

COPY packages/quant_contracts/pyproject.toml packages/quant_contracts/pyproject.toml
COPY packages/quant_contracts/src packages/quant_contracts/src
COPY services/quant_data_hub/pyproject.toml services/quant_data_hub/pyproject.toml
COPY services/quant_data_hub/src services/quant_data_hub/src

RUN python -m pip install --no-cache-dir \
    packages/quant_contracts \
    services/quant_data_hub

RUN useradd --create-home --shell /usr/sbin/nologin appuser

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "quant_data_hub.main:app", "--host", "0.0.0.0", "--port", "8000"]
