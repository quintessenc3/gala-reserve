FROM ghcr.io/astral-sh/uv:0.13 AS uv


FROM python:3.14-alpine AS base
ENV PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock ./


FROM base AS dev
ENV PYTHONDONTWRITEBYTECODE=1
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,from=uv,source=uv,target=/bin/uv \
    uv sync --locked --no-install-project
WORKDIR /app/gala_reserve
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


FROM base AS prod
ENV UV_COMPILE_BYTECODE=1
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,from=uv,source=uv,target=/bin/uv \
    uv sync --locked --no-install-project --no-dev
RUN adduser -D --no-create-home --shell /usr/sbin/nologin app
COPY . .
WORKDIR /app/gala_reserve
RUN chown -R app:app ./staticfiles ./media \
    && mkdir -p /var/lib/celery \
    && chown -R app:app /var/lib/celery
USER app
CMD ["gunicorn", "config.wsgi:application", "--config=./config/gunicorn.conf.py"]