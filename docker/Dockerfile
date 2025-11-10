FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV PATH="/root/.local/bin/:$PATH"
ENV UV_PROJECT_ENVIRONMENT=/usr/local
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-cache
WORKDIR /app
COPY . /app
ENV PYTHONUNBUFFERED=1
