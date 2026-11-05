FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy project files
COPY dataset/ /app/dataset/
COPY backend/ /app/backend/
COPY templates/ /app/templates/
COPY static/ /app/static/

ENV PYTHONPATH=/app/backend
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

# Pre-build DuckDB database from dataset/original CSVs
RUN python /app/backend/app/database/importer.py

# Expose port
EXPOSE 8000

# Run FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
