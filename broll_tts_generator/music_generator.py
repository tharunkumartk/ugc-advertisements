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
    
    # API requires callback URL, but we'll use polling mode
    # Provide a placeholder URL if none is provided (we'll poll instead)
    if callback_url:
        payload["callBackUrl"] = callback_url
    else:
        # Use a placeholder URL to satisfy API requirement, but we'll poll for results
        payload["callBackUrl"] = "https://placeholder.example.com/callback"
    
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
    
    # Check for error codes in JSON response (API may return HTTP 200 with error in body)
    error_code = result.get("code")
    if error_code and error_code != 200:
        error_msg = result.get("msg", "Unknown error")
        raise ValueError(f"Music generation API error (code {error_code}): {error_msg}")
    
    # Handle case where API returns {"data": None} - use empty dict as fallback
    data = result.get("data") or {}
    task_id = data.get("taskId")
    
    if not task_id:
        # Debug: print the actual API response to help diagnose the issue
        print(f"⚠️  Debug: API response: {result}")
        print(f"⚠️  Debug: Response data: {data}")
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
    
    # Use the correct endpoint for checking task status
    endpoint = f"https://api.kie.ai/api/v1/generate/record-info?taskId={task_id}"
    
    while time.time() - start_time < max_wait_time:
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for error codes in JSON response
                error_code = result.get("code")
                if error_code and error_code != 200:
                    error_msg = result.get("msg", "Unknown error")
                    raise ValueError(f"Music generation API error (code {error_code}): {error_msg}")
                
                # Extract data from response
                data = result.get("data") or {}
                status = data.get("status")
                
                # Check if task is complete (TEXT_SUCCESS indicates completion)
                if status == "TEXT_SUCCESS":
                    # Extract audio URL from nested response structure
                    response_data = data.get("response", {})
                    suno_data = response_data.get("sunoData", [])
                    
                    if suno_data and len(suno_data) > 0:
                        # Prefer streamAudioUrl, fallback to sourceStreamAudioUrl
                        track = suno_data[0]
                        audio_url = track.get("streamAudioUrl") or track.get("sourceStreamAudioUrl")
                        
                        if audio_url:
                            print(f"  ✓ Music generation completed!")
                            return audio_url
                        else:
                            raise ValueError("Music generation completed but no audio URL found in sunoData")
                    else:
                        raise ValueError("Music generation completed but no sunoData found in response")
                
                elif status in ["failed", "error", "fail", "TEXT_FAIL"]:
                    error_msg = data.get("errorMessage") or result.get("msg") or "Unknown error"
                    raise ValueError(f"Music generation failed: {error_msg}")
                
                elif status:
                    # Still processing
                    elapsed = int(time.time() - start_time)
                    print(f"  Status: {status}... (elapsed: {elapsed}s)")
                else:
                    # No status field, might be still processing
                    elapsed = int(time.time() - start_time)
                    print(f"  Waiting for completion... (elapsed: {elapsed}s)")
            
            elif response.status_code == 404:
                # Task not found yet, might still be processing
                elapsed = int(time.time() - start_time)
                print(f"  Task not found yet, waiting... (elapsed: {elapsed}s)")
            
            else:
                error_msg = response.text[:200] if response.text else "Unknown error"
                print(f"  ⚠️  Unexpected response ({response.status_code}): {error_msg}")
                
        except requests.RequestException as e:
            elapsed = int(time.time() - start_time)
            print(f"  ⚠️  Request error: {str(e)} (elapsed: {elapsed}s)")
        
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

