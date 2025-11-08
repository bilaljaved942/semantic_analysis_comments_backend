# backend/Dockerfile
FROM python:3.11-slim

# set environment
ENV PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    HF_HOME=/hf_cache \
    TRANSFORMERS_CACHE=/hf_cache/transformers \
    TORCH_HOME=/hf_cache/torch

# create app user
RUN useradd --create-home appuser
WORKDIR /app

# install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git curl libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# copy all app code
COPY . /app

# ensure permissions
RUN chown -R appuser:appuser /app
USER appuser

# expose port
EXPOSE 8000

# default command - run FastAPI app
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
