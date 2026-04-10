#!/bin/sh
set -e

# Start Xvfb and wait for it to be ready
Xvfb :99 -screen 0 1024x768x24 -nolisten tcp &
XVFB_PID=$!

# Create the Xauthority file so Xlib stops complaining
touch /root/.Xauthority
xauth add :99 . $(mcookie)

# Wait until the display is actually up
sleep 1

export DISPLAY=:99

cd /app
python -m server.app