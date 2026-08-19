FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    FCC_OPEN_BROWSER=false \
    HOST=0.0.0.0 \
    PORT=8082

WORKDIR /app

# Install dependencies first so dependency layers cache independently of source changes.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project --no-dev

COPY src ./src
RUN uv sync --locked --no-dev

RUN useradd --create-home --uid 1000 fcc \
    && mkdir -p /home/fcc/.fcc \
    && chown -R fcc:fcc /home/fcc /app
USER fcc
ENV HOME=/home/fcc \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 8082

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8082/health', timeout=3).status == 200 else 1)"

ENTRYPOINT ["fcc-server"]
