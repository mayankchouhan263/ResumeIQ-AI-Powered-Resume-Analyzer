# Backend image for Render (Docker runtime). Installs the Pango libraries WeasyPrint needs,
# the small spaCy model and the ONNX embedding model at BUILD time so cold starts stay fast.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    EMBEDDER_CACHE_DIR=/app/.cache/fastembed \
    PDF_ENGINE=weasyprint

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-backend.txt .
RUN pip install -r requirements-backend.txt && python -m spacy download en_core_web_sm

COPY backend ./backend
RUN python -c "from backend.services.embedder import OnnxEmbedder; OnnxEmbedder()"

# Render sets $PORT
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
