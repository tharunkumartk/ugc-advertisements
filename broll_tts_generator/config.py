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
XAI_API_KEY = os.getenv("XAI_API_KEY")
KIE_AI_API_KEY = os.getenv("KIE_AI_API_KEY")
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pnvpjqqgnhtvjdnujaur.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "generated-ugc")

# Video dimensions (9:16 for social media)
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280
