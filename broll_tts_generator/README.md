# B-Roll TTS Generator

A modular Python package for generating B-roll videos with text-to-speech narration.

## Package Structure

```
broll_tts_generator/
├── __init__.py          # Package initialization and exports
├── config.py            # Configuration (API keys, video dimensions)
├── product_image.py     # Product image generation using Gemini API
├── script_generator.py  # B-roll script generation using OpenAI
├── tts_generator.py     # Text-to-speech audio generation
├── video_generator.py   # B-roll video generation using Kie AI Sora 2
├── video_combiner.py    # Video combination and editing with FFmpeg
└── main.py              # Main orchestration and CLI interface
```

## Module Overview

### `config.py`
- Manages API keys and configuration constants
- Loads environment variables from `.env` file
- Defines video dimensions (720x1280 for 9:16 aspect ratio)

### `product_image.py`
- Generates product placement images using Google Gemini API
- Uploads images to tmpfiles.org for use in video generation
- Handles image extraction and error handling

### `script_generator.py`
- Generates B-roll scripts with narration and visual descriptions
- Uses OpenAI GPT-4o-mini with structured output
- Supports custom prompt templates

### `tts_generator.py`
- Generates text-to-speech audio using OpenAI TTS API
- Supports multiple voice options (alloy, echo, fable, onyx, nova, shimmer)
- Saves audio files in MP3 format

### `video_generator.py`
- Creates and manages video generation tasks using Kie AI Sora 2 API
- Supports both text-to-video and image-to-video generation
- Handles parallel video generation with thread pool execution
- Manages task polling and video downloading

### `video_combiner.py`
- Combines multiple B-roll clips into a single video
- Synchronizes video with TTS audio
- Handles video scaling, trimming, and speed adjustment
- Uses FFmpeg for video processing

### `main.py`
- Orchestrates the complete video generation pipeline
- Provides CLI interface with argument parsing
- Supports single video generation or batch processing with `--all-prompts`

## Usage

### As a Package

```python
from broll_tts_generator import generate_broll_video_with_tts

results = generate_broll_video_with_tts(
    topic="premium product",
    num_scenes=5,
    tts_voice="nova",
    output_dir="output",
    product_image_path="product.png",
    prompt_file="prompts/default_prompt.txt",
    max_workers=5
)
```

### Command Line Interface

```bash
# Single video generation
python broll_tts_generator_cli.py "premium product" --scenes 5 --voice nova

# Generate videos for all prompts in parallel
python broll_tts_generator_cli.py "premium product" --all-prompts

# With custom options
python broll_tts_generator_cli.py "my topic" \
    --scenes 7 \
    --voice shimmer \
    --output-dir my_output \
    --product-image my_product.png \
    --prompt-file prompts/custom_prompt.txt \
    --max-workers 3
```

## Dependencies

- `openai` - For script generation and TTS
- `google-genai` - For product image generation
- `pillow` - For image processing
- `requests` - For API calls and file uploads
- `python-dotenv` - For environment variable management
- `ffmpeg` - For video processing (system dependency)

## Environment Variables

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_openai_api_key
KIE_AI_API_KEY=your_kie_ai_api_key
```

## Migration from Monolithic Script

The original `broll_tts_generator.py` has been modularized into this package structure. The CLI interface (`broll_tts_generator_cli.py`) provides the same functionality as the original script.

