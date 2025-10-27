# EVA - Voice Assistant

## Overview

```
Audio Input → Groq STT → n8n (LLM Model + Tools) → Piper TTS → Audio Output
```

## Setup

### 1. Clone the Repository

```bash
git clone git@github.com:yildiz-fatih/eva-project.git
cd eva-project
```

### 2. Virtual Environment & Dependencies

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate

# Install the dependencies
pip install -r requirements.txt
```

### 3. Download Piper Voice Model

The backend uses Piper for text-to-speech. Download the voice model files:

```bash
# Create models directory
mkdir -p models

# Download the voice model (ONNX file) - ~60MB
curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" -o models/en_US-lessac-medium.onnx

# Download the config file (JSON)
curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" -o models/en_US-lessac-medium.onnx.json
```

### 4. Configure Environment Variables

Create a `.env` file in the project root and fill in your credentials:

```properties
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/your-webhook-id
PIPER_MODEL_PATH=models/en_US-lessac-medium.onnx
```

### 5. Run the Backend

```bash
python main.py
```

The backend is now running on `http://localhost:8000`

## Testing

### Test with a Sample Audio File

1. **Create a test audio file**: Record a short voice message and save it as `test.wav` (WAV format)

2. **Send request with curl**:

```bash
curl -X POST http://localhost:8000/process-voice \
  -F "audio=@test.wav" \
  --output response.wav
```

3. **Listen to the response**: You can find the `response.wav` output in the project root directory

## API Documentation

### Endpoint: `POST /process-voice`

Processes audio input and returns AI-generated audio response.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: Audio file with field name `audio`

**Response:**
- Content-Type: `audio/wav`
- Body: WAV audio file containing the AI's spoken response

## Extras

### Session Management

Currently uses a default session ID (`test-user-001`) for all requests. In production, the session ID should be:
- Generated per user/device
- Passed by the client (Raspberry Pi)
- Used to maintain conversation history in n8n's Postgres memory

### Testing the n8n Webhook Directly

```bash
curl -X POST https://your-n8n-webhook-url \
  -H "Content-Type: application/json" \
  -d '{"chatInput": "Hello, what is 2+2?", "sessionId": "test-001"}'
```

Expected response:
```json
{"response": {"output": "2 + 2 equals 4."}}
```
