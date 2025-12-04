import asyncio
import websockets
import json
import base64
import wave
import io
import pyaudio

class VoiceAssistantClient:
    def __init__(self, server_url="ws://localhost:8000/ws/process-voice", session_id="pi-001"):
        self.server_url = server_url
        self.session_id = session_id
        self.audio_chunks = []
        self.sample_rate = 22050
        
    async def connect_and_process(self, audio_file_path):
        """
        Connect to backend and process audio file
        
        Args:
            audio_file_path: Path to WAV audio file to send
        """
        # Read audio file
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()
        
        # Encode to base64
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        async with websockets.connect(self.server_url) as websocket:
            print("Connected to server")
            
            # Send audio
            await websocket.send(json.dumps({
                "audio": audio_base64,
                "sessionId": self.session_id
            }))
            print("Audio sent, waiting for response...")
            
            self.audio_chunks = []
            
            # Receive responses
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "transcription":
                    print(f"[Transcription] {data['text']}")
                
                elif msg_type == "ai_response":
                    print(f"[AI Response] {data['text']}")
                
                elif msg_type == "audio_chunk":
                    # Decode and store audio chunk
                    chunk_data = base64.b64decode(data["data"])
                    self.audio_chunks.append(chunk_data)
                    print(f"[Audio Chunk] Received chunk {data['index']}")
                
                elif msg_type == "audio_complete":
                    print(f"[Complete] Received {data['total_chunks']} chunks")
                    self.sample_rate = data["sample_rate"]
                    
                    # Save complete audio
                    self.save_audio("response.wav")
                    print("Response saved to response.wav")
                    
                    # Play audio
                    self.play_audio()
                    break
                
                elif msg_type == "error":
                    print(f"[Error] {data['message']}")
                    break
    
    def save_audio(self, filename):
        """Save received audio chunks to WAV file"""
        audio_data = b''.join(self.audio_chunks)
        
        with wave.open(filename, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)
    
    def play_audio(self):
        """Play the received audio"""
        try:
            audio_data = b''.join(self.audio_chunks)
            
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                output=True
            )
            
            print("Playing audio...")
            stream.write(audio_data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            print("Playback complete")
            
        except Exception as e:
            print(f"Could not play audio: {e}")
            print("Audio saved to response.wav - play it manually")


class StreamingVoiceAssistantClient:
    """
    Advanced client that plays audio as it arrives (streaming playback)
    """
    def __init__(self, server_url="ws://localhost:8000/ws/process-voice", session_id="pi-001"):
        self.server_url = server_url
        self.session_id = session_id
        self.audio_queue = asyncio.Queue()
        self.playback_started = False
        
    async def connect_and_process(self, audio_file_path):
        """Connect and process with streaming playback"""
        # Read audio file
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()
        
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        async with websockets.connect(self.server_url) as websocket:
            print("Connected to server")
            
            # Send audio
            await websocket.send(json.dumps({
                "audio": audio_base64,
                "sessionId": self.session_id
            }))
            print("Audio sent, waiting for response...")
            
            # Start playback task
            playback_task = asyncio.create_task(self.play_audio_stream())
            
            # Receive and queue audio chunks
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "transcription":
                    print(f"[Transcription] {data['text']}")
                
                elif msg_type == "ai_response":
                    print(f"[AI Response] {data['text']}")
                
                elif msg_type == "audio_chunk":
                    # Decode and queue audio chunk for immediate playback
                    chunk_data = base64.b64decode(data["data"])
                    await self.audio_queue.put(chunk_data)
                    if not self.playback_started:
                        print("[Streaming] Starting playback...")
                        self.playback_started = True
                
                elif msg_type == "audio_complete":
                    print(f"[Complete] Received {data['total_chunks']} chunks")
                    # Signal end of stream
                    await self.audio_queue.put(None)
                    break
                
                elif msg_type == "error":
                    print(f"[Error] {data['message']}")
                    await self.audio_queue.put(None)
                    break
            
            # Wait for playback to finish
            await playback_task
    
    async def play_audio_stream(self):
        """Play audio chunks as they arrive"""
        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=22050,
                output=True
            )
            
            while True:
                chunk = await self.audio_queue.get()
                if chunk is None:  # End of stream
                    break
                stream.write(chunk)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            print("[Streaming] Playback complete")
            
        except Exception as e:
            print(f"Playback error: {e}")


# Example usage
async def main():
    # Choose client type
    
    """
    Option 1: Basic client (receive all audio, then play)
    client = VoiceAssistantClient(
        server_url="ws://localhost:8000/ws/process-voice",
        session_id="pi-001"
    )
    """
    # Option 2: Streaming client (play audio as it arrives)
    client = StreamingVoiceAssistantClient(
        server_url="ws://localhost:8000/ws/process-voice",
        session_id="pi-001"
    )
    
    # Process audio file
    await client.connect_and_process("test.wav")


if __name__ == "__main__":
    # Run the client
    asyncio.run(main())