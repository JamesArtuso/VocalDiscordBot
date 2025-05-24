# Discord AI Voice Chat Bot
A Discord bot that can engage in voice conversations using AI. The bot uses:
- Whisper for speech-to-text
  - https://github.com/openai/whisper 
- Llama for text generation
  - https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct
- XTTS for text-to-speech
  - https://huggingface.co/coqui/XTTS-v2

Currently, this only works on Windows. This is due to the communication between Python and JavaScript. This should be easily replaceable as it is just transferring packets.

## Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- FFmpeg installed and in PATH
  - https://www.ffmpeg.org/download.html

### Python Setup
1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

### Node.js Setup
1. Install Node.js dependencies:
```bash
npm install
```
### Running the Bot
1. Add your voice samples to the `voices/` directory


2. Start the Python backend:
```bash
python start.py
```

3. Start the bot in a separate window:
```bash
node bot.js
```

## Commands
- `!join` - Bot joins your voice channel
- `!leave` - Bot leaves the voice channel
- `!volume <0-2>` - Adjust bot's volume (e.g., 0.5 for 50%, 1 for 100%, 2 for 200%)

## License
Idk what to put here. This is just a personal project. Go check out Whisper, Llama3, and XTTS. They are pretty cool libraries and this would be a much harder project without them.

## TODO
There is a lot still left to do. Specific todos are put in their respective files. However, the base program works.
The biggest project-wide to-do is to make it work with multiple speakers. Currently, it is only with one speaker, and I have not been able to test it with multiple speakers. 
