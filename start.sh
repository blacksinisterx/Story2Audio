#!/bin/bash
# start.sh – launch all services in order

# 1. Start gRPC servers (as background processes)
python story_service.py &
python audio_service.py &

# 2. Start FastAPI server (background)
uvicorn main:app --host 0.0.0.0 --port 5000 &

# 3. Wait for FastAPI to be ready before launching the UI
echo "Waiting for FastAPI on port 5000..."
while ! nc -z localhost 5000; do
  sleep 1
done

# 4. Start the Gradio UI (after FastAPI is up)
python utils/frontend.py
