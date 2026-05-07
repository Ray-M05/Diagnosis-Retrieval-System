# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

# Copy uv to the image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation and make the project venv the default runtime.
# Increase uv HTTP timeout/retries because torch CPU wheels are large.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_HTTP_TIMEOUT=300 \
    UV_HTTP_RETRIES=10 \
    UV_CACHE_DIR=/root/.cache/uv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Runtime dependencies for Docker are CPU-only. The project lock currently
# targets CUDA wheels for local GPU workflows, which pulls several GB of
# nvidia-* packages during image builds.
COPY requirements-docker.txt ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python \
    --index-url https://download.pytorch.org/whl/cpu \
    "torch==2.6.0+cpu" && \
    uv pip install --python /app/.venv/bin/python \
    -r requirements-docker.txt

# Copy the rest of the application
COPY . .

# Install the local package without re-resolving dependencies.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python /app/.venv/bin/python --no-deps -e .

EXPOSE 8501

# Default command to run Streamlit
CMD ["/app/.venv/bin/python", "-m", "streamlit", "run", "src/sri_dx/app/ui/ui_streamlit.py", "--server.port=8501", "--server.address=0.0.0.0"]