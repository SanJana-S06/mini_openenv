#!/bin/bash
set -e

# Start Virtual Display
Xvfb :99 -screen 0 1024x768x24 -nolisten tcp &
sleep 2

# Start the Server in the background
# Using -m because your app.py is inside the 'server' folder
python -m server.app &

# Wait for the server to be ready
sleep 5

# Start the Agent in the foreground
# This ensures the [START]/[STEP]/[END] logs are captured
python inference.py