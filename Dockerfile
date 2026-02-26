FROM python:3.11-slim

# Copy uv to the image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Install dependencies in a separate layer
COPY pyproject.toml uv.lock* ./
RUN if [ -f uv.lock ]; then \
    uv sync --frozen --no-install-project; \
    else \
    uv sync --no-install-project; \
    fi

# Copy the rest of the application
COPY . .

# Install the project
RUN uv sync --frozen

EXPOSE 8501

# Default command to run Streamlit
CMD ["uv", "run", "streamlit", "run", "src/sri_dx/app/ui_streamlit.py", "--server.port=8501", "--server.address=0.0.0.0"]
