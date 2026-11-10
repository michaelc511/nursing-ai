# One container: Node builds the React UI, Python serves it with FastAPI. Local models and the
# policy index are baked into the image, so a deploy needs no downloads at start.
FROM node:20-slim AS ui
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
ENV PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu \
    HF_HOME=/opt/hf \
    PYTHONUNBUFFERED=1 \
    CHROMA_DIR=/opt/chroma
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY data/samples data/samples
COPY --from=ui /app/frontend/dist frontend/dist
WORKDIR /app/backend
RUN python -m app.cli index-policies \
 && python -c "from sentence_transformers import CrossEncoder; from app.config import settings; CrossEncoder(settings.rerank_model)"
ENV HF_HUB_OFFLINE=1
EXPOSE 8080
# Refuses to start without its secrets, so the app can never run on the dev-only defaults.
CMD ["sh", "-c", ": \"${SECRET_KEY:?SECRET_KEY is required}\" \"${DEMO_PASSWORD:?DEMO_PASSWORD is required}\" && mkdir -p /data/storage /data/inbox && python -m app.cli init-db && exec uvicorn app.main:app --host 0.0.0.0 --port 8080"]
