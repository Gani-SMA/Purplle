#!/bin/bash
set -e

# CCTV Footage directory (fallback to local downloaded path if /data/cctv doesn't exist)
FOLDER_PATH=${1:-"/data/cctv"}

if [ ! -d "$FOLDER_PATH" ]; then
  FOLDER_PATH="/app/cctv"
fi

# If neither exists, check Windows standard local path mapping
if [ ! -d "$FOLDER_PATH" ]; then
  FOLDER_PATH="C:/Users/kkbha/Downloads/CCTV Footage-20260529T160731Z-3-00144614ea/CCTV Footage"
fi

echo "--- Running Purplle CCTV Detection Pipeline ---"
echo "CCTV Folder: $FOLDER_PATH"
echo "Redis URL:   ${REDIS_URL:-redis://localhost:6379/0}"
echo "API URL:     ${API_URL:-http://localhost:8000}"

# Run the detection/simulation pipeline
# Pass --no-ml by default if running in CPU container to keep it fast, or if specifically passed
# We can allow passing extra arguments like --no-ml from the command line
python process_clips.py --folder "$FOLDER_PATH" --output events.jsonl --frame-step 30 --redis-url "${REDIS_URL:-redis://localhost:6379/0}" "$@"

# Run the event uploader to ingest events into FastAPI
python upload_events.py events.jsonl
