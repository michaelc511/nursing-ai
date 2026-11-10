# [CONFIRM] Finalized in Phase 11 (multi-stage: Node builds the UI, Python serves FastAPI).
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
WORKDIR /app/backend
# [CONFIRM] start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
