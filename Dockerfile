FROM accel.way2api.fun/ghcr.io/astral-sh/uv:python3.14-trixie-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple/ \
    UV_HTTP_TIMEOUT=60 \
    UV_HTTP_RETRIES=5 \
    PYTHONUNBUFFERED=1 \
    FCC_OPEN_BROWSER=false \
    HOST=0.0.0.0 \
    PORT=8082

WORKDIR /app

# Keep dependency versions and hashes from uv.lock, but install the artifacts
# from the Tsinghua TUNA PyPI mirror instead of the URLs embedded in uv.lock.
# --frozen makes export use the checked-in lockfile without re-resolving it.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export --frozen --no-group dev --no-emit-project \
        --format requirements.txt --output-file /tmp/requirements.txt \
    && uv venv \
    && uv pip sync --require-hashes /tmp/requirements.txt

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --no-deps .

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
