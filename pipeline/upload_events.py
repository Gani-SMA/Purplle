import sys
import os
import json
import httpx
import asyncio
import structlog
from dotenv import load_dotenv

# Load env file if exists
load_dotenv()

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger("event_uploader")

async def upload_events(jsonl_path, api_url, api_key, batch_size=500):
    if not os.path.exists(jsonl_path):
        logger.error("jsonl_file_not_found", path=jsonl_path)
        return False
        
    logger.info("starting_upload", path=jsonl_path, api_url=api_url)
    
    events = []
    with open(jsonl_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except Exception as e:
                    logger.error("failed_to_parse_line", error=str(e), line=line)

    if not events:
        logger.warning("no_events_found_to_upload")
        return True

    logger.info("total_events_read", count=len(events))
    
    # Split into batches of batch_size
    batches = [events[i:i + batch_size] for i in range(0, len(events), batch_size)]
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for idx, batch in enumerate(batches):
            logger.info("uploading_batch", batch_index=idx, batch_len=len(batch))
            payload = {"events": batch}
            try:
                response = await client.post(
                    f"{api_url.rstrip('/')}/events/ingest",
                    json=payload,
                    headers=headers
                )
                if response.status_code == 200:
                    res_data = response.json()
                    logger.info(
                        "batch_upload_success",
                        batch_index=idx,
                        accepted=res_data.get("accepted"),
                        rejected=res_data.get("rejected"),
                        errors=res_data.get("errors")
                    )
                else:
                    logger.error(
                        "batch_upload_failed",
                        batch_index=idx,
                        status_code=response.status_code,
                        response_text=response.text
                    )
            except Exception as e:
                logger.error("request_exception", batch_index=idx, error=str(e))
                
    return True

if __name__ == "__main__":
    jsonl_path = sys.argv[1] if len(sys.argv) > 1 else "events.jsonl"
    
    # Read config from env vars
    api_url = os.getenv("API_URL", "http://localhost:8000")
    api_key = os.getenv("API_KEY", "test_key_1")
    
    asyncio.run(upload_events(jsonl_path, api_url, api_key))
