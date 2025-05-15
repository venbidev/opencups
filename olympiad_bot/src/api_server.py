#!/usr/bin/env python3
import logging
import sqlite3
import re
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, validator, Field

DATABASE_NAME = "olympiad_bot/olympiad_portal.db"
API_KEY_NAME = "X-API-KEY"
# THIS IS A DEMO API KEY. In a real application, use a secure way to store and manage API keys.
VALID_API_KEY = "your_secret_api_key_here" 

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

app = FastAPI(title="Olympiad Results API", version="1.0.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Helper Functions (similar to bot, but adapted for API context) ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def validate_snils_api_format(snils: str) -> bool:
    return bool(re.fullmatch(r"\d{3}-\d{3}-\d{3} \d{2}", snils))

async def get_api_key(
    api_key_header_value: str = Security(api_key_header),
):
    if api_key_header_value == VALID_API_KEY:
        return api_key_header_value
    else:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API Key",
        )

# --- Pydantic Models for API --- 
class ResultItem(BaseModel):
    full_name: str = Field(..., min_length=1)
    snils: str
    score: int
    place: int
    diploma_link: Optional[str] = None

    @validator("snils")
    def snils_must_be_valid(cls, value):
        if not validate_snils_api_format(value):
            raise ValueError("Invalid SNILS format. Must be XXX-XXX-XXX XX")
        return value

class ResultsPayload(BaseModel):
    olympiad_id: int
    results: List[ResultItem]

    @validator("results")
    def results_must_not_be_empty(cls, value):
        if not value:
            raise ValueError("Results array cannot be empty")
        return value

# --- API Endpoint --- 
@app.post("/api/v1/results", status_code=201)
async def add_olympiad_results(
    payload: ResultsPayload,
    api_key: str = Depends(get_api_key)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if olympiad_id exists
    cursor.execute("SELECT id FROM Olympiads WHERE id = ?", (payload.olympiad_id,))
    olympiad = cursor.fetchone()
    if not olympiad:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Olympiad with id {payload.olympiad_id} not found")

    added_count = 0
    errors = []

    for index, result_item in enumerate(payload.results):
        try:
            # Pydantic models already perform some validation
            # Additional specific checks can be done here if needed
            cursor.execute("""INSERT INTO Results (olympiad_id, user_snils, full_name, score, place, diploma_link)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                           (payload.olympiad_id, result_item.snils, result_item.full_name,
                            result_item.score, result_item.place, result_item.diploma_link))
            added_count += 1
        except sqlite3.IntegrityError as e: # e.g. foreign key constraint, though olympiad_id is checked
            logger.error(f"DB IntegrityError for item {index}: {e}")
            errors.append({"index": index, "error": "Database integrity error", "detail": str(e)})
        except Exception as e:
            logger.error(f"Error processing item {index}: {e}")
            errors.append({"index": index, "error": "Processing error", "detail": str(e)})
    
    if errors:
        conn.rollback()
        conn.close()
        # If any error occurred during batch processing, we might choose to raise an error for the whole batch
        # or return a partial success with error details. Here, we raise a 400 if any item failed.
        raise HTTPException(status_code=400, detail={"message": "Error processing some results", "errors": errors})

    conn.commit()
    conn.close()
    return {"message": "Results added successfully", "added_count": added_count}

# --- To run this API (example command, not executed by the agent directly) ---
# uvicorn api_server:app --host 0.0.0.0 --port 8000

if __name__ == "__main__":
    # This part is for local execution if you run `python api_server.py`
    # However, FastAPI apps are typically run with Uvicorn or similar ASGI server.
    print("FastAPI server script created: api_server.py")
    print("To run: uvicorn /home/ubuntu/olympiad_bot/src/api_server:app --host 0.0.0.0 --port 8000")
    print("Remember to replace 'your_secret_api_key_here' with an actual secret key.")

