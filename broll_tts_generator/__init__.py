"""
B-Roll + TTS Video Generator Package

Generates a video with:
1. Multiple B-roll footage clips (using Kie AI Sora 2)
2. Script with voiceover narration (using OpenAI)
3. TTS audio (using OpenAI)
4. Combined output with audio over B-roll sequence

No A-roll (talking head) - just cinematic B-roll with voiceover.
"""

from .main import generate_broll_video_with_tts

__all__ = ["generate_broll_video_with_tts"]

