import os
import logging
import uuid  # Add this import
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks
from pydantic import BaseModel, HttpUrl
import tempfile
import requests
from transcribe import transcribe_audio, cancellation_flags, save_transcript
from fastapi.middleware.cors import CORSMiddleware  # Add this import
from sse_starlette.sse import EventSourceResponse
from collections import defaultdict
import json
from shared import latest_transcripts

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Add this block after creating the FastAPI app instance
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],  # Add any other local URLs you need
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TranscriptionResponse(BaseModel):
    transcript: str

class UrlRequest(BaseModel):
    url: HttpUrl

@app.post("/transcribe/file", response_model=TranscriptionResponse)
async def transcribe_file(file: UploadFile = File(...), api_key: str = Form(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    try:
        job_id = str(uuid.uuid4())
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        return EventSourceResponse(transcribe_audio(temp_file_path, "ffmpeg", api_key, job_id, background_tasks))
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail="Transcription failed")

@app.post("/transcribe/url", response_model=TranscriptionResponse)
async def transcribe_url(url_request: UrlRequest, api_key: str, background_tasks: BackgroundTasks = BackgroundTasks()):
    try:
        job_id = str(uuid.uuid4())
        response = requests.get(url_request.url)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name

        background_tasks.add_task(transcribe_audio, temp_file_path, "ffmpeg", api_key, job_id)
        return {"transcript": "Transcription started", "job_id": job_id}
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail="Transcription failed")

@app.post("/cancel_transcription/{job_id}")
async def cancel_transcription(job_id: str):
    if job_id in cancellation_flags:
        cancellation_flags[job_id] = True
        return {"message": f"Transcription job {job_id} cancellation requested"}
    else:
        raise HTTPException(status_code=404, detail="Transcription job not found")

@app.get("/get_transcript/{job_id}")
async def get_transcript(job_id: str):
    if job_id in latest_transcripts:
        chunks = latest_transcripts[job_id]
        if chunks:
            # Return all available chunks and clear the list
            response = {"chunks": chunks}
            latest_transcripts[job_id] = []
            return response
        else:
            return {"chunks": []}
    else:
        raise HTTPException(status_code=404, detail="Transcript not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))