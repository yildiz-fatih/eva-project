Step 1: Get the Code
bash
git clone https://github.com/yildiz-fatih/eva-project.git
cd eva-project
Step 2: Install Python Dependencies
bash
pip install groq python-dotenv sounddevice soundfile transformers torch numpy
Step 3: Set up API Key
Create a file called .env in the project folder with this content:

text
GROQ_API_KEY=your_actual_groq_api_key_here
Get API key from: https://console.groq.com

Step 4: Run the Code
bash
python realtime_emotion.py
Step 5: Use It
Talk into your microphone

The system records 5-second clips automatically

See real-time emotion analysis in the console

Press Ctrl+C to stop

Troubleshooting
No microphone access? Check Windows microphone permissions

API errors? Make sure .env file has correct API key

Module errors? Run the pip install command again

Still struggling? Contact me
