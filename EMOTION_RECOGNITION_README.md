## Real-time Emotion Detection System

This project includes a real-time multi-modal emotion detection system that analyzes both voice tone and text content.

### Features

- Real-time audio recording and processing
- Voice emotion analysis using wav2vec2 model
- Text emotion analysis using transformer models
- Multi-modal fusion combining voice and text analysis

### Installation (For PC Users)

1. Install emotion detection dependencies:
   ```bash
   pip install sounddevice soundfile transformers
Run the emotion detection system:

bash
python realtime_emotion.py
Usage
The system will record 5-second audio clips continuously and provide real-time emotion analysis.

To stop the application: Press Ctrl+C

How It Works
Audio Recording: Captures 5-second audio clips

Speech-to-Text: Uses Groq's Whisper Turbo for fast transcription

Voice Emotion: Analyzes pitch, tone, and speech characteristics

Text Emotion: Analyzes word content and sentiment

Multi-modal Fusion: Combines voice and text analysis with weighted scoring

Raspberry Pi Audio Setup
For Raspberry Pi users, additional audio configuration may be required:
Model Download Issues: First run will download models, ensure stable internet connection

arecord --format=S16_LE --duration=5 --rate=16000 --file-type=raw test.raw
No Audio Input: Check microphone permissions and ensure microphone is not muted

Troubleshooting
Voice Emotions: angry, sad, happy, neutral, fearful
Text Emotions: anger, sadness, joy, fear, disgust, surprise, neutral
Emotion Detection Models

The system detects emotions from both voice and text:
# Test microphone
arecord -l

sudo apt update
sudo apt install portaudio19-dev python3-pyaudio
bash
