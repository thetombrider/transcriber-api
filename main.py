import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
import tempfile
import requests
from transcribe import transcribe_audio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

class TranscriptionResponse(BaseModel):
    transcript: str

class UrlRequest(BaseModel):
    url: HttpUrl

@app.post("/transcribe/file", response_model=TranscriptionResponse)
async def transcribe_file(file: UploadFile = File(...), api_key: str = Form(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        transcript = transcribe_audio(temp_file_path, "ffmpeg", api_key)
        os.unlink(temp_file_path)
        return {"transcript": transcript}
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail="Transcription failed")

@app.post("/transcribe/url", response_model=TranscriptionResponse)
async def transcribe_url(url_request: UrlRequest, api_key: str):
    try:
        response = requests.get(url_request.url)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name

        transcript = transcribe_audio(temp_file_path, "ffmpeg", api_key)
        os.unlink(temp_file_path)
        return {"transcript": transcript}
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail="Transcription failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))