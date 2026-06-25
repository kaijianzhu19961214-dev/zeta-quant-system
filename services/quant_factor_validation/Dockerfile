FROM python:3.12.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

COPY packages/quant_contracts/pyproject.toml packages/quant_contracts/pyproject.toml
COPY packages/quant_contracts/src packages/quant_contracts/src
COPY clients/quant_data_sdk/pyproject.toml clients/quant_data_sdk/pyproject.toml
COPY clients/quant_data_sdk/src clients/quant_data_sdk/src
COPY services/quant_factor_validation/pyproject.toml services/quant_factor_validation/pyproject.toml
COPY services/quant_factor_validation/src services/quant_factor_validation/src

RUN python -m pip install --no-cache-dir \
    packages/quant_contracts \
    clients/quant_data_sdk \
    services/quant_factor_validation

RUN useradd --create-home --shell /usr/sbin/nologin appuser

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "quant_factor_validation.main:app", "--host", "0.0.0.0", "--port", "8000"]
