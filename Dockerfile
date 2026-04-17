FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md /app/
COPY backend /app/backend
COPY policies /app/policies
COPY evaluation /app/evaluation
COPY docs /app/docs
COPY tools /app/tools

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.app.api.proxy:app", "--host", "0.0.0.0", "--port", "8000"]

