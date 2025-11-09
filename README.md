# UGC Video Generator

A Python tool for generating professional B-roll videos with text-to-speech narration, background music, and product placement. Perfect for creating social media content, product showcases, and marketing videos.

## Features

- 🎬 **B-roll Video Generation**: Create multiple video scenes using AI-powered video generation (KIE AI Sora 2)
- 🎤 **Text-to-Speech**: Generate natural-sounding narration using OpenAI TTS or ElevenLabs
- 🎵 **Background Music**: Automatically generate matching background music for your videos
- 📦 **Product Placement**: Seamlessly integrate product images into video scenes
- 🎨 **Multiple Themes**: Support for custom prompt templates and themed video generation
- ⚡ **Parallel Processing**: Generate multiple videos simultaneously for efficiency
- ☁️ **Cloud Upload**: Optional Supabase integration for cloud storage

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd UGC
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install FFmpeg (required for video processing):
   - **macOS**: `brew install ffmpeg`
   - **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
   - **Windows**: Download from [FFmpeg website](https://ffmpeg.org/download.html)

4. Set up environment variables:
   Create a `.env` file in the project root:
```env
OPENAI_API_KEY=your_openai_api_key
KIE_AI_API_KEY=your_kie_ai_api_key
ELEVEN_LABS_API_KEY=your_elevenlabs_api_key  # Optional
SUPABASE_URL=your_supabase_url  # Optional
SUPABASE_KEY=your_supabase_key  # Optional
```

## Quick Start

### Basic Usage

Generate a video with specific configurable settings. 
```bash
python broll_tts_generator_cli.py "robot dog advertisement" --scenes 3 --new-prompt "playground at school" --eleven-labs  --max-workers 5 --remove-background --upload-supabase
```
