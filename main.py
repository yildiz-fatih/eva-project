from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
import httpx
from groq import Groq
import os
from dotenv import load_dotenv
from piper import PiperVoice
import io
import wave
import json
import base64

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
    """HTTP endpoint - returns complete audio file"""
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


@app.websocket("/ws/process-voice")
async def websocket_process_voice(websocket: WebSocket):
    """
    WebSocket endpoint - streams audio chunks back in real-time
    
    Protocol:
    1. Client connects
    2. Client sends: {"audio": "<base64_encoded_audio>", "sessionId": "optional"}
    3. Server sends: {"type": "transcription", "text": "..."}
    4. Server sends: {"type": "ai_response", "text": "..."}
    5. Server streams: {"type": "audio_chunk", "data": "<base64_audio>", "index": N}
    6. Server sends: {"type": "audio_complete", "sample_rate": 22050}
    7. Connection closes or waits for next audio
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive audio from client
            data = await websocket.receive_json()
            
            # Extract audio and session ID
            audio_base64 = data.get("audio")
            session_id = data.get("sessionId", DEFAULT_SESSION_ID)
            
            if not audio_base64:
                await websocket.send_json({
                    "type": "error",
                    "message": "No audio data provided"
                })
                continue
            
            # Decode audio
            audio_bytes = base64.b64decode(audio_base64)
            
            try:
                # Step 1: STT with Groq
                transcription = groq_client.audio.transcriptions.create(
                    file=("audio.wav", audio_bytes),
                    model="whisper-large-v3-turbo",
                )
                text = transcription.text
                
                # Send transcription to client
                await websocket.send_json({
                    "type": "transcription",
                    "text": text
                })
                
                # Step 2: Send to n8n
                async with httpx.AsyncClient(timeout=30.0) as client:
                    n8n_response = await client.post(
                        n8n_webhook_url,
                        json={
                            "chatInput": text,
                            "sessionId": session_id
                        }
                    )
                    n8n_response.raise_for_status()
                    response_data = n8n_response.json()
                    response_text = response_data["response"]["output"]
                
                # Send AI response text to client
                await websocket.send_json({
                    "type": "ai_response",
                    "text": response_text
                })
                
                # Step 3: TTS with Piper - stream chunks
                chunk_index = 0
                for chunk in piper_voice.synthesize(response_text):
                    # Send each audio chunk immediately
                    audio_chunk_base64 = base64.b64encode(chunk.audio_int16_bytes).decode('utf-8')
                    await websocket.send_json({
                        "type": "audio_chunk",
                        "data": audio_chunk_base64,
                        "index": chunk_index
                    })
                    chunk_index += 1
                
                # Send completion message
                await websocket.send_json({
                    "type": "audio_complete",
                    "total_chunks": chunk_index,
                    "sample_rate": piper_voice.config.sample_rate,
                    "channels": 1,
                    "sample_width": 2
                })
                
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)