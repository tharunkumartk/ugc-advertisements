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


def combine_broll_with_audio(
    broll_paths: List[str],
    audio_path: str,
    output_path: str,
    background_music_path: str = None,
    music_volume: float = 0.075,
):
    """
    Combine B-roll videos and add TTS audio with optional background music.

    Args:
        broll_paths: List of paths to B-roll video files
        audio_path: Path to TTS narration audio file
        output_path: Path for the final output video
        background_music_path: Optional path to background music file
        music_volume: Volume level for background music (0.0-1.0, default: 0.075 for quiet)
    """
    print("\n" + "=" * 60)
    print("STEP 4: Combining B-Roll Videos with Audio")
    print("=" * 60)

    if not broll_paths:
        raise ValueError("No B-roll videos to combine")

    # Get audio duration
    audio_duration = get_audio_duration(audio_path)
    print(f"Audio duration: {audio_duration:.2f} seconds")
    print(f"Number of B-roll clips: {len(broll_paths)}")

    if background_music_path:
        print(f"Background music: {background_music_path} (volume: {music_volume})")

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

    # Combine with audio (and background music if provided)
    if background_music_path and os.path.exists(background_music_path):
        # Mix TTS audio with background music
        # Background music should be quieter and loop/extend to match narration duration
        print("Mixing TTS audio with background music...")

        # Validate music file
        if not os.path.isfile(background_music_path):
            raise ValueError(
                f"Background music path is not a file: {background_music_path}"
            )

        # First, extend/loop background music to match narration duration if needed
        try:
            music_duration = get_audio_duration(background_music_path)
        except Exception as e:
            raise ValueError(
                f"Failed to get duration of background music file {background_music_path}: {e}"
            )

        if music_duration <= 0:
            raise ValueError(f"Invalid music duration: {music_duration} seconds")

        # Use .m4a extension when encoding to AAC (MP3 container doesn't support AAC)
        extended_music = os.path.join(temp_dir, "extended_music.m4a")

        if music_duration < audio_duration:
            # Loop the music to match narration duration
            loops_needed = int(audio_duration / music_duration) + 1
            cmd = [
                "ffmpeg",
                "-stream_loop",
                str(loops_needed),
                "-i",
                background_music_path,
                "-t",
                str(audio_duration),
                "-c:a",
                "aac",
                "-b:a",
                "192k",  # Explicit bitrate for better compatibility
                extended_music,
                "-y",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"FFmpeg stderr: {result.stderr}")
                print(f"FFmpeg stdout: {result.stdout}")
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, result.stdout, result.stderr
                )
            music_to_use = extended_music
        else:
            # Trim music to match narration duration
            # Use the minimum of music_duration and audio_duration to avoid issues
            trim_duration = min(music_duration, audio_duration)
            cmd = [
                "ffmpeg",
                "-i",
                background_music_path,
                "-t",
                str(trim_duration),
                "-c:a",
                "aac",
                "-b:a",
                "192k",  # Explicit bitrate for better compatibility
                extended_music,
                "-y",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"FFmpeg stderr: {result.stderr}")
                print(f"FFmpeg stdout: {result.stdout}")
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, result.stdout, result.stderr
                )
            music_to_use = extended_music

        # Mix TTS (foreground) with background music (quieter)
        # Use amix filter to mix two audio tracks
        # Use .m4a extension when encoding to AAC (MP3 container doesn't support AAC)
        mixed_audio = os.path.join(temp_dir, "mixed_audio.m4a")
        cmd = [
            "ffmpeg",
            "-i",
            audio_path,  # TTS narration (foreground)
            "-i",
            music_to_use,  # Background music
            "-filter_complex",
            f"[0:a]volume=1.0[a0];[1:a]volume={music_volume}[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=2",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            mixed_audio,
            "-y",
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        final_audio = mixed_audio
    else:
        final_audio = audio_path
        print("Adding TTS audio to video...")

    # Combine video with mixed audio
    cmd = [
        "ffmpeg",
        "-i",
        temp_video,
        "-i",
        final_audio,
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

    if background_music_path:
        print("Adding mixed audio (TTS + background music) to video...")
    else:
        print("Adding TTS audio to video...")
    subprocess.run(cmd, check=True, capture_output=True)

    print(f"✓ Final video created: {output_path}")

    # Cleanup
    shutil.rmtree(temp_dir)
