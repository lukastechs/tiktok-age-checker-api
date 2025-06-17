FROM python:3.9-slim

  WORKDIR /app

  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  RUN playwright install chromium
  RUN playwright install-deps

  COPY . .

  ENV PORT=8000

  CMD exec uvicorn --host 0.0.0.0 --port $PORT main:app
