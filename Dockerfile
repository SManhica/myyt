FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/myyt-venv/bin:$PATH"

WORKDIR /app

RUN python -m venv /opt/myyt-venv

COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
COPY docs ./docs

RUN python -m pip install --no-cache-dir ".[dev]" \
    && useradd --create-home --uid 10001 myyt \
    && chown -R myyt:myyt /app

USER myyt

ENTRYPOINT ["myyt"]
