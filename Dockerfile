# 1. Use a standard Python image (Always available)
FROM python:3.10-slim

# 2. Install system dependencies for Xvfb and GUI interaction
RUN apt-get update && apt-get install -y \
    xvfb \
    x11-xserver-utils \
    python3-tk \
    python3-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Install 'uv' and 'openenv-core' manually
RUN pip install --no-cache-dir uv openenv-core

# 4. Set working directory
WORKDIR /app

# 5. Copy dependency files and install
COPY pyproject.toml uv.lock* ./
RUN uv pip install --system -r pyproject.toml

# 6. Copy the rest of the code
COPY . .

# 7. Setup permissions and environment
RUN chmod +x start.sh
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# 8. Launch via start.sh
CMD ["./start.sh"]