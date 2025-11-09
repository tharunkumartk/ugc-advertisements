"""
TTS Audio Generation Module

Handles text-to-speech audio generation using OpenAI API or ElevenLabs API.
"""

import os
from datetime import datetime
from openai import OpenAI

from .config import OPENAI_API_KEY, ELEVEN_LABS_API_KEY


def generate_tts_audio(
    text: str, output_dir: str, voice: str = "nova", use_eleven_labs: bool = False
) -> str:
    """
    Generate TTS audio using OpenAI or ElevenLabs API.
    
    Args:
        text: Text to convert to speech
        output_dir: Directory to save the audio file
        voice: Voice ID/name (OpenAI voice name or ElevenLabs voice_id)
        use_eleven_labs: If True, use ElevenLabs API; otherwise use OpenAI API
        
    Returns:
        Path to the generated audio file
    """
    print("\n" + "=" * 60)
    print("STEP 2: Generating TTS Audio")
    print("=" * 60)

    if use_eleven_labs:
        return _generate_eleven_labs_audio(text, output_dir, voice)
    else:
        return _generate_openai_audio(text, output_dir, voice)


def _generate_openai_audio(text: str, output_dir: str, voice: str = "nova") -> str:
    """Generate TTS audio using OpenAI API."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    print(f"Using OpenAI TTS with voice '{voice}'...")
    print(f"Text length: {len(text)} characters")

    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.audio.speech.create(
        model="tts-1",  # Use tts-1-hd for higher quality
        voice=voice,  # Options: alloy, echo, fable, onyx, nova, shimmer
        input=text,
    )

    # Save audio
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"tts_audio_{timestamp}.mp3")

    response.stream_to_file(output_path)

    print(f"✓ TTS audio generated: {output_path}")
    return output_path


def _generate_eleven_labs_audio(
    text: str, output_dir: str, voice_id: str = "RXtWW6etvimS8QJ5nhVk"
) -> str:
    """Generate TTS audio using ElevenLabs API."""
    if not ELEVEN_LABS_API_KEY:
        raise ValueError("ELEVEN_LABS_API_KEY environment variable is not set")

    try:
        from elevenlabs import ElevenLabs
    except ImportError:
        raise ImportError(
            "elevenlabs package is required for ElevenLabs TTS. "
            "Install it with: pip install elevenlabs"
        )

    print(f"Using ElevenLabs TTS with voice_id '{voice_id}'...")
    print(f"Text length: {len(text)} characters")

    client = ElevenLabs(api_key=ELEVEN_LABS_API_KEY)

    # Generate audio using ElevenLabs API
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    # Save audio
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"tts_audio_{timestamp}.mp3")

    # Write audio bytes to file
    # Handle both bytes and generator/stream responses
    with open(output_path, "wb") as f:
        if isinstance(audio, bytes):
            f.write(audio)
        else:
            # Assume it's an iterable (generator/stream)
            for chunk in audio:
                if isinstance(chunk, bytes):
                    f.write(chunk)
                else:
                    # If chunk is not bytes, try to convert it
                    f.write(bytes(chunk))

    print(f"✓ TTS audio generated: {output_path}")
    return output_path

