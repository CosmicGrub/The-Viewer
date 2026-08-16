# Backend API + extraction/indexing CLI scripts, containerized (finding
# #11/#33 — previously there was no deployment path beyond a Windows dev
# machine: no Dockerfile, no reverse-proxy config, no static hosting).
#
# Build from the repo root (needs both requirements.txt and backend/):
#   docker build -f backend/Dockerfile -t tm-search-backend .
# Or use docker-compose.yml at the repo root, which wires this up together
# with Meilisearch and the frontend.
FROM python:3.12-slim

# tesseract-ocr: the OCR fallback (extract_pdf_text.py / extract_image_text.py)
# shells out to the `tesseract` binary via pytesseract — it isn't a pip
# package. libgl1/libglib2.0-0: runtime dependencies of opencv-python
# (used for OCR preprocessing) even in a headless container.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/

ENV PYTHONUNBUFFERED=1
WORKDIR /app/backend

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
