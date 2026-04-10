# 1. Use the official OpenEnv base image (pre-configured for uv)
FROM ghcr.io/openenv-ai/openenv-core:latest

# 2. Set working directory
WORKDIR /app

# 3. Copy only dependency files first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# 4. Install dependencies using uv (Faster and matches your lockfile)
RUN uv sync --frozen

# 5. Copy the rest of your application code
# Ensure start.sh and inference.py are in your root folder!
COPY . .

# 6. Install system dependencies for Xvfb and GUI interaction
USER root
RUN apt-get update && apt-get install -y \
    xvfb \
    x11-xserver-utils \
    python3-tk \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 7. Make start.sh executable
RUN chmod +x start.sh

# 8. Set environment variables required for the validator
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# 9. Use the start.sh script to launch both Server and Agent
CMD ["./start.sh"]