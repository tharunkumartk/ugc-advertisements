"""
Music Generation Module

Handles background music generation using Suno API via kie.ai.
"""

import os
import time
import requests
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from .config import KIE_AI_API_KEY


def generate_music(
    music_prompt: str,
    style: str,
    title: str,
    output_dir: str,
    duration_seconds: Optional[float] = None,
    model: str = "V5",
    callback_url: Optional[str] = None,
) -> str:
    """
    Generate instrumental background music using Suno API.
    
    Args:
        music_prompt: Description of the desired music (used as prompt in custom mode)
        style: Music style/genre (e.g., "Ambient", "Cinematic", "Electronic")
        title: Title for the music track
        output_dir: Directory to save the generated music file
        duration_seconds: Desired duration in seconds (optional, for reference)
        model: AI model version (V3_5, V4, V4_5, V4_5PLUS, V5)
        callback_url: Optional callback URL for async completion (if None, will poll)
        
    Returns:
        Path to the downloaded music file
    """
    print("\n" + "=" * 60)
    print("STEP 2.5: Generating Background Music")
    print("=" * 60)
    
    if not KIE_AI_API_KEY:
        raise ValueError("KIE_AI_API_KEY environment variable is not set")
    
    print(f"Music prompt: {music_prompt}")
    print(f"Style: {style}")
    print(f"Title: {title}")
    print(f"Model: {model}")
    
    # Prepare request payload
    payload = {
        "prompt": music_prompt,
        "style": style,
        "title": title,
        "customMode": True,
        "instrumental": True,  # Always instrumental for background music
        "model": model,
    }
    
    # Add callback URL if provided, otherwise we'll poll
    if callback_url:
        payload["callBackUrl"] = callback_url
    
    # Make API request
    headers = {
        "Authorization": f"Bearer {KIE_AI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    print("Submitting music generation request...")
    response = requests.post(
        "https://api.kie.ai/api/v1/generate",
        json=payload,
        headers=headers,
    )
    
    if response.status_code != 200:
        error_msg = response.json().get("msg", "Unknown error")
        raise ValueError(f"Music generation API error ({response.status_code}): {error_msg}")
    
    result = response.json()
    task_id = result.get("data", {}).get("taskId")
    
    if not task_id:
        raise ValueError("No task ID returned from music generation API")
    
    print(f"✓ Music generation task created: {task_id}")
    print("Polling for completion...")
    
    # Poll for completion
    music_url = _poll_for_completion(task_id, headers)
    
    if not music_url:
        raise ValueError("Music generation completed but no audio URL found")
    
    # Download the music file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"background_music_{timestamp}.mp3")
    
    print(f"Downloading music from: {music_url}")
    _download_file(music_url, output_path)
    
    print(f"✓ Background music generated: {output_path}")
    return output_path


def _poll_for_completion(task_id: str, headers: dict, max_wait_time: int = 300, poll_interval: int = 5) -> Optional[str]:
    """
    Poll the API for music generation completion.
    
    Args:
        task_id: Task ID to poll
        headers: Request headers with auth
        max_wait_time: Maximum time to wait in seconds (default: 5 minutes)
        poll_interval: Seconds between polls (default: 5)
        
    Returns:
        URL to the generated music file, or None if timeout/error
    """
    start_time = time.time()
    
    # Try multiple possible endpoints
    endpoints_to_try = [
        f"https://api.kie.ai/api/v1/music/{task_id}",
        f"https://api.kie.ai/api/v1/music/details/{task_id}",
        f"https://api.kie.ai/api/v1/music/task/{task_id}",
    ]
    
    while time.time() - start_time < max_wait_time:
        for endpoint in endpoints_to_try:
            try:
                response = requests.get(endpoint, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Handle different response structures
                    status = None
                    audio_url = None
                    
                    # Try different response formats
                    if "data" in data:
                        status_data = data["data"]
                        status = status_data.get("status") or status_data.get("state")
                        
                        # Try to get audio URL from various possible locations
                        audio_url = (
                            status_data.get("audioUrl") or 
                            status_data.get("audio_url") or
                            status_data.get("url") or
                            status_data.get("downloadUrl") or
                            status_data.get("download_url")
                        )
                        
                        # Check tracks array
                        if not audio_url:
                            tracks = status_data.get("tracks", [])
                            if tracks and len(tracks) > 0:
                                track = tracks[0]
                                audio_url = (
                                    track.get("audioUrl") or 
                                    track.get("audio_url") or
                                    track.get("url") or
                                    track.get("downloadUrl") or
                                    track.get("download_url")
                                )
                    else:
                        # Direct response structure
                        status = data.get("status") or data.get("state")
                        audio_url = (
                            data.get("audioUrl") or 
                            data.get("audio_url") or
                            data.get("url")
                        )
                    
                    if status == "complete" or status == "success":
                        if audio_url:
                            return audio_url
                        else:
                            print(f"  Status complete but no audio URL found in response")
                            # Continue polling, might be in progress
                    
                    elif status in ["failed", "error", "fail"]:
                        error_msg = data.get("msg") or data.get("message") or "Unknown error"
                        raise ValueError(f"Music generation failed: {error_msg}")
                    
                    elif status:
                        # Still processing
                        elapsed = int(time.time() - start_time)
                        print(f"  Status: {status}... (elapsed: {elapsed}s)")
                        break  # Found working endpoint, break from endpoint loop
                
                elif response.status_code == 404:
                    # Try next endpoint
                    continue
                
                else:
                    # Try next endpoint on other errors
                    continue
                    
            except requests.RequestException as e:
                # Try next endpoint
                continue
        
        time.sleep(poll_interval)
    
    raise TimeoutError(f"Music generation timed out after {max_wait_time} seconds")


def _download_file(url: str, output_path: str):
    """Download a file from URL to local path."""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

