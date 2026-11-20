FROM python:3.14-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY alembic ./alembic
RUN python -m pip install --no-cache-dir .

USER 10001
CMD ["python", "-m", "app"]
