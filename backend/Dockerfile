# backend/Dockerfile
FROM python:3.10-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Install system dependencies (for psycopg2 etc.)
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary source code
COPY src ./src

# bundle trained models used by api_v1_5.py
COPY reports/models ./reports/models

EXPOSE 8000
# Start FastAPI server using module path
CMD ["uvicorn", "src.api_v1_5:app", "--host", "0.0.0.0", "--port", "8000"]
