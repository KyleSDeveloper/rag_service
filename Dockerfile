# ---- base image ----
FROM python:3.11-slim

# System deps (optional but nice to have)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Faster, repeatable installs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ---- app files ----
WORKDIR /app
COPY . /app

# ---- Python deps ----
# If you already generated requirements.txt, this will pin versions.
# Otherwise, this fallback installs the minimal set your app needs.
RUN if [ -f requirements.txt ]; then \
      pip install -r requirements.txt ; \
    else \
      pip install "fastapi>=0.110" "uvicorn[standard]>=0.23" "rank-bm25>=0.2" "loguru>=0.7" "requests>=2.31" "tqdm>=4.66"; \
    fi

# ---- build the BM25 index at image build time (optional but convenient) ----
# Outputs rag_app/index.json so the container runs without extra steps.
RUN python -m rag_app.index --corpus ./corpus --out ./rag_app/index.json

# ---- runtime config ----
ENV PORT=8000
EXPOSE 8000

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD curl -fsS http://127.0.0.1:${PORT}/health || exit 1

# Use ${PORT} if your host (e.g., Render) sets it; default to 8000 locally
CMD ["bash","-lc","uvicorn rag_app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]


