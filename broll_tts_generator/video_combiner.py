"""
Video Combination Module

Handles combining B-roll videos with TTS audio using FFmpeg.
"""

import os
import subprocess
import tempfile
import shutil
from typing import List

from .config import VIDEO_WIDTH, VIDEO_HEIGHT


def get_audio_duration(audio_path: str) -> float:
    """Get duration of audio file using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def get_video_duration(video_path: str) -> float:
    """Get duration of video file using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def combine_broll_with_audio(broll_paths: List[str], audio_path: str, output_path: str):
    """Combine B-roll videos and add TTS audio."""
    print("\n" + "=" * 60)
    print("STEP 4: Combining B-Roll Videos with Audio")
    print("=" * 60)

    if not broll_paths:
        raise ValueError("No B-roll videos to combine")

    # Get audio duration
    audio_duration = get_audio_duration(audio_path)
    print(f"Audio duration: {audio_duration:.2f} seconds")
    print(f"Number of B-roll clips: {len(broll_paths)}")

    # Create temporary concat file for FFmpeg
    temp_dir = tempfile.mkdtemp()
    concat_file = os.path.join(temp_dir, "concat_list.txt")

    # Calculate target duration per clip
    duration_per_clip = audio_duration / len(broll_paths)
    print(f"Target duration per clip: {duration_per_clip:.2f} seconds")

    # Process each clip to target duration and scale to consistent size
    processed_clips = []
    for i, broll_path in enumerate(broll_paths):
        processed_path = os.path.join(temp_dir, f"processed_{i}.mp4")

        # Get original video duration
        original_duration = get_video_duration(broll_path)

        # Build video filter with scaling
        vf_parts = [
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}"
        ]

        # If video is shorter than target, slow it down
        if original_duration < duration_per_clip:
            speed_factor = original_duration / duration_per_clip
            # setpts filter slows down video (larger value = slower)
            vf_parts.insert(0, f"setpts={1/speed_factor}*PTS")
            print(
                f"  Clip {i+1}: Slowing down ({original_duration:.2f}s -> {duration_per_clip:.2f}s)"
            )

        video_filter = ",".join(vf_parts)

        # Trim to target duration and scale to consistent dimensions
        cmd = [
            "ffmpeg",
            "-i",
            broll_path,
            "-t",
            str(duration_per_clip),  # Trim to target duration
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-an",  # No audio
            processed_path,
            "-y",
        ]

        subprocess.run(cmd, check=True, capture_output=True)
        processed_clips.append(processed_path)
        print(f"  Processed clip {i+1}/{len(broll_paths)}")

    # Create concat file
    with open(concat_file, "w") as f:
        for clip in processed_clips:
            f.write(f"file '{clip}'\n")

    # Concatenate all clips
    temp_video = os.path.join(temp_dir, "concatenated.mp4")
    cmd = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_file,
        "-c",
        "copy",
        temp_video,
        "-y",
    ]

    print("Concatenating B-roll clips...")
    subprocess.run(cmd, check=True, capture_output=True)

    # Combine with audio
    cmd = [
        "ffmpeg",
        "-i",
        temp_video,
        "-i",
        audio_path,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-shortest",  # End when audio ends
        output_path,
        "-y",
    ]

    print("Adding TTS audio to video...")
    subprocess.run(cmd, check=True, capture_output=True)

    print(f"✓ Final video created: {output_path}")

    # Cleanup
    shutil.rmtree(temp_dir)

