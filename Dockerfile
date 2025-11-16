# Use whatever Python version you target in pyproject.toml
FROM python:3.12-slim

# Don't buffer stdout/stderr (nice for logs)
ENV PYTHONUNBUFFERED=1

# 1) Install system deps and uv
RUN apt-get update && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (goes to ~/.local/bin/uv)
RUN curl -LsSf https://astral.sh/uv/install.sh \
    | env UV_NO_MODIFY_PATH=1 UV_UNMANAGED_INSTALL=/usr/local/bin sh
ENV PATH="/root/.local/bin:${PATH}"

# 2) Set workdir
WORKDIR /app

# 3) Copy dependency files first (better Docker cache)
COPY pyproject.toml uv.lock ./

# Create venv and install deps from lockfile
RUN uv sync --frozen --no-dev

# Use the venv Python by default
ENV PATH="/app/.venv/bin:${PATH}"

# 4) Copy the rest of the project
COPY . .

# 5) Default command (change if you have a console script)
CMD ["python", "main.py"]
