from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class TwitterSession(BaseModel):
    cookies: list

@app.post("/set-session")
async def set_session(session: TwitterSession):
    """Set Twitter session cookies."""
    try:
        cookies_file = Path("data/cookies.json")
        cookies_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(cookies_file, 'w') as f:
            json.dump(session.cookies, f)
            
        logger.info("Successfully saved Twitter session cookies")
        return {"status": "success", "message": "Session cookies saved"}
    except Exception as e:
        logger.error(f"Error saving session cookies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 