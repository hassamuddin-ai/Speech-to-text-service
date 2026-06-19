import io
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config.loader import load_config
from src.transcription.whisper_client import WhisperClient
from src.utils.text_normalizer import TextNormalizer
from src.transcription.language_filter import LanguageFilter, is_urdu
from src.utils.roman_urdu import to_roman_urdu
from src.utils.logger import get_logger

app = FastAPI(title="STI Transcribe API")

# Allow CORS for the Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = load_config()
logger = get_logger(__name__, config)

# Initialize components
whisper_client = WhisperClient(config)
normalizer = TextNormalizer(config.get("normalizer", {}).get("mode", "auto"))
lang_filter = LanguageFilter(config)

@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    try:
        # Read the file bytes
        file_bytes = await audio.read()
        
        # Create a BytesIO buffer and set a name so Groq knows the extension
        wav_buf = io.BytesIO(file_bytes)
        wav_buf.name = audio.filename or "audio.webm"
        
        # Transcribe using Groq Whisper
        text, language = whisper_client.transcribe(wav_buf)
        if not text:
            return {"text": "", "language": language}
            
        # Normalize text (math symbols, etc.)
        text = normalizer.normalize(text)
        
        # Check language filter
        keep, norm_lang = lang_filter.check(text, language)
        if not keep:
            return {"text": "", "language": norm_lang, "error": "Language not supported"}
            
        # Convert to Roman Urdu if necessary
        if is_urdu(norm_lang):
            display_text = to_roman_urdu(text)
        else:
            display_text = text
            
        return {"text": display_text, "language": norm_lang}
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8501))
    uvicorn.run(app, host="0.0.0.0", port=port)
