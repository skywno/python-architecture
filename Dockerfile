FROM python:3.9-slim-buster

WORKDIR /app

COPY pyproject.toml /app/
COPY src/ /app/src/
COPY tests/ /app/tests/
RUN pip install --no-cache-dir -e ".[dev]"

ENV FLASK_APP=allocation.entrypoints.flask_app:app FLASK_DEBUG=1 PYTHONUNBUFFERED=1
CMD flask run --host=0.0.0.0 --port=80
