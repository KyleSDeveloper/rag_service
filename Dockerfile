# syntax=docker/dockerfile:1
FROM python:3.11-slim

# System deps (faster torch wheels, FAISS works out-of-the-box)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl ca-certificates libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Install deps
# (keeps layers slim; add --no-cache-dir for smaller images)
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install uvicorn

# Pre-download sentence-transformers model to avoid cold starts
RUN python - <<'PY'
from sentence_transformers import SentenceTransformer
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
print("Model cached.")
PY

# Build indexes at image build time (optional but nice for demo images)
# If corpus changes at runtime you can rebuild with the Make targets instead.
RUN python -m rag_app.index --corpus ./corpus --out ./rag_app/index.json || true
RUN python -m rag_app.vector_index --index_json ./rag_app/index.json --out_index ./app/faiss.index --out_meta ./app/vec_meta.json || true

# 8000 is conventional for containerized FastAPI
ENV PORT=8000
EXPOSE 8000

# Health-friendly startup
CMD ["uvicorn", "rag_app.main:app", "--host", "0.0.0.0", "--port", "8000"]

