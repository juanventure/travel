FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

# Bind to the platform-provided $PORT (e.g. Render) when set; default 8000 for
# local docker-compose. Shell form so ${PORT} is expanded at runtime.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
