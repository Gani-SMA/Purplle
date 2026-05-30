# Run script for Windows PowerShell
$folder = $args[0]
if (-not $folder) {
    $folder = "C:\Users\kkbha\Downloads\CCTV Footage-20260529T160731Z-3-00144614ea\CCTV Footage"
}

Write-Host "--- Running Purplle CCTV Detection Pipeline (Windows PowerShell) ---" -ForegroundColor Purple
Write-Host "CCTV Folder: $folder"
Write-Host "Redis URL:   $($env:REDIS_URL ?? 'redis://localhost:6379/0')"
Write-Host "API URL:     $($env:API_URL ?? 'http://localhost:8000')"

# Set env vars if not set
if (-not $env:REDIS_URL) { $env:REDIS_URL = "redis://localhost:6379/0" }
if (-not $env:API_URL) { $env:API_URL = "http://localhost:8000" }
if (-not $env:API_KEY) { $env:API_KEY = "test_key_1" }

# Run Python processor
python process_clips.py --folder "$folder" --output events.jsonl --frame-step 30 --redis-url $env:REDIS_URL $args

# Upload events
python upload_events.py events.jsonl
