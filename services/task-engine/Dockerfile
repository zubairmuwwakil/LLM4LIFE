FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY task_engine ./task_engine
COPY alembic.ini ./
COPY migrations ./migrations

RUN pip install --no-cache-dir .

EXPOSE 8080
CMD ["uvicorn", "task_engine.main:app", "--host", "0.0.0.0", "--port", "8080"]
