from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response
import httpx
from groq import Groq
import os
from dotenv import load_dotenv
from piper import PiperVoice
import io
import wave

load_dotenv()

app = FastAPI()

# Initialize clients with validation
_groq_api_key = os.getenv("GROQ_API_KEY")
_n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
piper_model_path = os.getenv("PIPER_MODEL_PATH", "models/en_US-lessac-medium.onnx")

# Get absolute path relative to this file
if not os.path.isabs(piper_model_path):
    piper_model_path = os.path.join(os.path.dirname(__file__), piper_model_path)

if not _groq_api_key:
    raise ValueError("GROQ_API_KEY environment variable is required")
if not _n8n_webhook_url:
    raise ValueError("N8N_WEBHOOK_URL environment variable is required")

# Now these are guaranteed to be str
groq_api_key: str = _groq_api_key
n8n_webhook_url: str = _n8n_webhook_url

groq_client = Groq(api_key=groq_api_key)

# Initialize Piper voice
print(f"Loading Piper voice model from: {piper_model_path}")
if not os.path.exists(piper_model_path):
    raise FileNotFoundError(
        f"Piper model not found at {piper_model_path}\n"
        "Run the download commands from the README to get the model files."
    )

piper_voice = PiperVoice.load(piper_model_path)
print(f"Piper voice loaded successfully!")

# Default session ID for testing (in production, this would come from the client)
DEFAULT_SESSION_ID = "test-user-001"


@app.post("/process-voice")
async def process_voice(audio: UploadFile = File(...)):
    try:
        # Step 1: Read audio file
        audio_bytes = await audio.read()
        
        # Step 2: STT with Groq
        transcription = groq_client.audio.transcriptions.create(
            file=("audio.wav", audio_bytes),
            model="whisper-large-v3-turbo",
        )
        text = transcription.text
        
        # Step 3: Send to n8n
        async with httpx.AsyncClient(timeout=30.0) as client:
            n8n_response = await client.post(
                n8n_webhook_url,
                json={
                    "chatInput": text,
                    "sessionId": DEFAULT_SESSION_ID
                }
            )
            n8n_response.raise_for_status()
            response_data = n8n_response.json()
            
            # Extract response from n8n's nested structure
            response_text = response_data["response"]["output"]
        
        # Step 4: TTS with Piper
        audio_chunks = []
        for chunk in piper_voice.synthesize(response_text):
            audio_chunks.append(chunk.audio_int16_bytes)
        
        audio_data = b''.join(audio_chunks)
        
        # Step 5: Create WAV file in memory
        audio_buffer = io.BytesIO()
        with wave.open(audio_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(piper_voice.config.sample_rate)
            wav_file.writeframes(audio_data)
        
        audio_buffer.seek(0)
        
        # Step 6: Return audio
        return Response(
            content=audio_buffer.read(),
            media_type="audio/wav"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)