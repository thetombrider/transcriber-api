import os
import subprocess
import math
import logging
from openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")
client = OpenAI(api_key=openai_api_key)

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

def transcribe_audio(audio_file_path, ffmpeg_path, api_key):
    logger.info(f"Transcribing audio file: {audio_file_path}")
    full_transcript = []
    chunk_length_seconds = 60  # 1 minute chunks
    chunk_generator = split_audio(audio_file_path, ffmpeg_path=ffmpeg_path)
    
    client = OpenAI(api_key=api_key)
    
    for i, chunk_file in enumerate(chunk_generator):
        logger.info(f"Processing chunk {i}: {chunk_file}")
        try:
            if not os.path.exists(chunk_file):
                logger.warning(f"Chunk file not found: {chunk_file}")
                continue
            
            logger.info(f"Transcribing chunk {i}: {chunk_file}")
            with open(chunk_file, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="it"
                )
            
            timestamp = format_timestamp(i * chunk_length_seconds)
            full_transcript.append(f"{timestamp}:   {transcript.text}")
            logger.info(f"Chunk {i} transcribed: {timestamp}")
        
        except Exception as e:
            logger.error(f"Error transcribing chunk {i}: {str(e)}")
        
        finally:
            if os.path.exists(chunk_file):
                logger.info(f"Removing chunk file: {chunk_file}")
                os.remove(chunk_file)
    
    logger.info(f"Transcription completed. Total chunks transcribed: {len(full_transcript)}")
    return "\n".join(full_transcript)
