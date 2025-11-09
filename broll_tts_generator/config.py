"""
Configuration module for B-Roll TTS Generator.

Contains API keys, video dimensions, and other configuration constants.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
KIE_AI_API_KEY = os.getenv("KIE_AI_API_KEY")
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")

# Video dimensions (9:16 for social media)
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280
