FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV XAUTHORITY=/root/.Xauthority

RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11-utils \
    xauth \
    python3-tk \
    tk-dev \
    xdotool \
    scrot \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

# Run Xvfb and start the server
CMD ["sh", "-c", "Xvfb :99 -screen 0 1024x768x24 & sleep 2 && python -m server.app"]
