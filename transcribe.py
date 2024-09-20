import os
import subprocess
import math
import logging
from openai import OpenAI
from dotenv import load_dotenv
import asyncio
from typing import Dict
from fastapi import BackgroundTasks
from sse_starlette.sse import EventSourceResponse
from shared import latest_transcripts

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global dictionary to store cancellation flags for each transcription job
cancellation_flags: Dict[str, bool] = {}

def split_audio(audio_file_path, chunk_length_ms=60000, ffmpeg_path="ffmpeg"):
    logger.info(f"Splitting audio file: {audio_file_path}")
    ffprobe_path = "ffprobe"
    
    try:
        output = subprocess.check_output([ffprobe_path, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audio_file_path])
        duration = float(output)
        logger.info(f"Audio duration: {duration} seconds")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting audio duration: {str(e)}")
        return

    chunks = math.ceil(duration / (chunk_length_ms / 1000))
    logger.info(f"Number of chunks: {chunks}")

    for i in range(chunks):
        start_time = i * (chunk_length_ms / 1000)
        chunk_file = f"temp_chunk_{i}.ogg"
        logger.info(f"Creating chunk {i}: {chunk_file}")
        
        try:
            subprocess.call([ffmpeg_path, '-i', audio_file_path, '-ss', str(start_time), '-t', str(chunk_length_ms / 1000), '-c:a', 'libvorbis', '-q:a', '4', chunk_file, '-y'])
            
            if os.path.exists(chunk_file):
                logger.info(f"Chunk file created: {chunk_file}")
                yield chunk_file
            else:
                logger.warning(f"Failed to create chunk file: {chunk_file}")
        except Exception as e:
            logger.error(f"Error creating chunk {i}: {str(e)}")

def format_timestamp(seconds):
    minutes = int(seconds / 60)
    return f"{minutes:02d}:00"

async def transcribe_audio(audio_file_path, ffmpeg_path, api_key, job_id, background_tasks: BackgroundTasks):
    async def event_generator():
        logger.info(f"Transcribing audio file: {audio_file_path}")
        full_transcript = []
        chunk_length_seconds = 60  # 1 minute chunks
        chunk_generator = split_audio(audio_file_path, ffmpeg_path=ffmpeg_path)

        cancellation_flags[job_id] = False

        for i, chunk_file in enumerate(chunk_generator):
            if cancellation_flags[job_id]:
                logger.info(f"Transcription job {job_id} cancelled")
                yield {"event": "cancel", "data": "Transcription cancelled"}
                break

            logger.info(f"Processing chunk {i}: {chunk_file}")
            try:
                if not os.path.exists(chunk_file):
                    logger.warning(f"Chunk file not found: {chunk_file}")
                    continue
                
                logger.info(f"Transcribing chunk {i}: {chunk_file}")
                with open(chunk_file, "rb") as audio_file:
                    transcript = OpenAI(api_key=api_key).audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="it"
                    )
                
                timestamp = format_timestamp(i * chunk_length_seconds)
                chunk_transcript = f"{timestamp}:   {transcript.text}"
                full_transcript.append(chunk_transcript)
                logger.info(f"Chunk {i} transcribed: {timestamp}")
                
                # Yield the chunk transcript immediately
                yield {"event": "chunk", "data": chunk_transcript}
            
            except Exception as e:
                logger.error(f"Error transcribing chunk {i}: {str(e)}")
                yield {"event": "error", "data": f"Error transcribing chunk {i}: {str(e)}"}
            
            finally:
                if os.path.exists(chunk_file):
                    logger.info(f"Removing chunk file: {chunk_file}")
                    os.remove(chunk_file)
            
            await asyncio.sleep(0)  # Allow other coroutines to run

        del cancellation_flags[job_id]
        logger.info(f"Transcription completed. Total chunks transcribed: {len(full_transcript)}")
        final_transcript = "\n".join(full_transcript)
        
        # Store the transcript in a file or database associated with the job_id
        save_transcript(job_id, final_transcript)
        
        yield {"event": "complete", "data": "Transcription completed"}

    return EventSourceResponse(event_generator())

def save_transcript(job_id, transcript):
    with open(f"{job_id}_transcript.txt", "w") as f:
        f.write(transcript)
    # Clear the latest_transcripts for this job_id
    if job_id in latest_transcripts:
        del latest_transcripts[job_id]
