"""
Video Generation Module

Handles B-roll video generation using Kie AI Sora 2 API.
"""

import os
import json
import time
import requests
import subprocess
from typing import Dict, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import KIE_AI_API_KEY, VIDEO_WIDTH, VIDEO_HEIGHT
from .product_image import generate_product_image, upload_image_to_tmpfiles


def create_sora2_task(
    prompt: str,
    api_key: str = None,
    aspect_ratio: str = "portrait",
    n_frames: str = "10",
    remove_watermark: bool = True,
    image_urls: Optional[List[str]] = None,
) -> Dict:
    """
    Create a video generation task using Kie AI's Sora 2 model.

    Args:
        prompt: Text description of the video to generate
        api_key: Kie AI API key (or set KIE_AI_API_KEY environment variable)
        aspect_ratio: Video aspect ratio - "portrait" or "landscape" (default: "portrait")
        n_frames: Number of frames/duration - "10" (10s) or "15" (15s) (default: "10")
        remove_watermark: Whether to remove watermarks (default: True)
        image_urls: Optional list of image URLs for image-to-video generation

    Returns:
        dict containing task information including taskId
    """
    if not api_key:
        api_key = os.getenv("KIE_AI_API_KEY")
        if not api_key:
            raise ValueError(
                "KIE_AI_API_KEY environment variable is not set. "
                "Please set it using: export KIE_AI_API_KEY='your-api-key-here'"
            )

    url = "https://api.kie.ai/api/v1/jobs/createTask"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # Determine model and input based on whether image URLs are provided
    if image_urls:
        model = "sora-2-image-to-video"
        input_data = {
            "prompt": prompt,
            "image_urls": image_urls,
            "aspect_ratio": aspect_ratio,
            "n_frames": n_frames,
            "remove_watermark": remove_watermark,
        }
    else:
        model = "sora-2-text-to-video"
        input_data = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "n_frames": n_frames,
            "remove_watermark": remove_watermark,
        }

    payload = {
        "model": model,
        "input": input_data,
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

        if result.get("code") != 200:
            error_msg = result.get("message", "Unknown error")
            raise Exception(f"API error: {error_msg}")

        task_id = result.get("data", {}).get("taskId")
        if not task_id:
            raise Exception("No taskId returned from API")

        return {
            "task_id": task_id,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "n_frames": n_frames,
            "remove_watermark": remove_watermark,
            "response": result,
        }

    except requests.exceptions.RequestException as e:
        print(f"\n✗ HTTP Error: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Response text: {e.response.text}")
        raise
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        raise


def query_task_status(task_id: str, api_key: str = None) -> Dict:
    """
    Query the status of a video generation task.

    Args:
        task_id: The task ID returned from create_sora2_task
        api_key: Kie AI API key (or set KIE_AI_API_KEY environment variable)

    Returns:
        dict containing task status and result information
    """
    if not api_key:
        api_key = os.getenv("KIE_AI_API_KEY")
        if not api_key:
            raise ValueError(
                "KIE_AI_API_KEY environment variable is not set. "
                "Please set it using: export KIE_AI_API_KEY='your-api-key-here'"
            )

    url = "https://api.kie.ai/api/v1/jobs/recordInfo"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    params = {"taskId": task_id}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        result = response.json()

        if result.get("code") != 200:
            error_msg = result.get("message", "Unknown error")
            raise Exception(f"API error: {error_msg}")

        return result.get("data", {})

    except requests.exceptions.RequestException as e:
        print(f"\n✗ HTTP Error querying task status: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Response text: {e.response.text}")
        raise
    except Exception as e:
        print(f"\n✗ Error querying task status: {str(e)}")
        raise


def poll_task_until_complete(
    task_id: str,
    api_key: str = None,
    poll_interval: int = 10,
    timeout: int = 600,
) -> Dict:
    """
    Poll the task status until it completes (success or failure).

    Args:
        task_id: The task ID returned from create_sora2_task
        api_key: Kie AI API key (or set KIE_AI_API_KEY environment variable)
        poll_interval: Time in seconds between status checks (default: 10)
        timeout: Maximum time to wait in seconds (default: 600 = 10 minutes)

    Returns:
        dict containing task status and result information
    """
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise Exception(
                f"Timeout waiting for task completion after {timeout} seconds"
            )

        status_data = query_task_status(task_id, api_key)
        state = status_data.get("state")

        elapsed_str = f"{int(elapsed)}s"
        print(f"\r    Status: {state}... (elapsed: {elapsed_str})", end="", flush=True)

        if state == "success":
            print(" Done!")
            return status_data
        elif state == "fail":
            fail_msg = status_data.get("failMsg", "Unknown error")
            fail_code = status_data.get("failCode", "Unknown")
            print(f"\n✗ Video generation failed!")
            print(f"Error code: {fail_code}")
            print(f"Error message: {fail_msg}")
            raise Exception(f"Task failed: {fail_msg} (code: {fail_code})")

        time.sleep(poll_interval)


def download_video(url: str, output_path: str) -> str:
    """
    Download a video from a URL to a local file.

    Args:
        url: URL of the video to download
        output_path: Local file path to save the video

    Returns:
        Path to the downloaded file
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        os.makedirs(
            os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
            exist_ok=True,
        )

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(
                            f"\r    Downloading: {percent:.1f}%",
                            end="",
                            flush=True,
                        )

        print(" Done!")
        return output_path

    except Exception as e:
        print(f"\n✗ Error downloading video: {str(e)}")
        raise


def create_video_from_image(
    image_path: str,
    output_path: str,
    duration: float = 10.0,
) -> str:
    """
    Create a video from a static image using ffmpeg.
    
    Args:
        image_path: Path to the input image file
        output_path: Path where the output video will be saved
        duration: Duration of the video in seconds (default: 10.0)
    
    Returns:
        Path to the created video file
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    # Build ffmpeg command to create video from image
    # Scale image to video dimensions, loop it for the specified duration
    cmd = [
        "ffmpeg",
        "-loop", "1",
        "-i", image_path,
        "-t", str(duration),
        "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",  # No audio
        output_path,
        "-y",  # Overwrite output file
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else "Unknown error"
        raise Exception(f"Failed to create video from image: {error_msg}")


def generate_broll_video(
    video_prompt: str,
    output_dir: str,
    scene_index: int,
    image_url: Optional[str] = None,
) -> str:
    """Generate a single B-roll video using Kie AI Sora 2.

    Args:
        video_prompt: Video prompt describing actions and motion for the video
        output_dir: Directory to save the video
        scene_index: Index of the scene (for naming)
        image_url: Optional image URL for image-to-video generation
    """
    if not KIE_AI_API_KEY:
        raise ValueError("KIE_AI_API_KEY environment variable is not set")

    print(f"  Scene {scene_index}: Generating B-roll...")
    print(f"    Video prompt: {video_prompt[:80]}...")
    if image_url:
        print(f"    Using image-to-video with image URL")

    # Create task
    task_result = create_sora2_task(
        prompt=video_prompt,
        api_key=KIE_AI_API_KEY,
        aspect_ratio="portrait",  # 9:16 aspect ratio for social media
        n_frames="10",
        remove_watermark=True,
        image_urls=[image_url] if image_url else None,
    )

    task_id = task_result["task_id"]

    # Poll until complete
    print(f"    Generating video...", end="", flush=True)
    status_data = poll_task_until_complete(
        task_id=task_id,
        api_key=KIE_AI_API_KEY,
        poll_interval=10,
        timeout=600,
    )

    # Extract video URL from resultJson
    result_json_str = status_data.get("resultJson", "{}")
    try:
        result_json = json.loads(result_json_str)
    except json.JSONDecodeError:
        raise Exception(f"Failed to parse resultJson: {result_json_str}")

    video_urls = result_json.get("resultUrls", [])
    if not video_urls:
        raise Exception(f"No video URLs found in task result for scene {scene_index}")

    # Download video (use first video URL)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"broll_scene{scene_index}_{timestamp}.mp4")
    download_video(video_urls[0], output_path)

    print(f"    ✓ Saved: {output_path}")
    return output_path


def _generate_product_image_and_upload(
    scene_index: int,
    image_prompt: str,
    output_dir: str,
    product_image_path: str,
) -> Optional[str]:
    """Helper function to generate and upload product image for a scene."""
    try:
        print(f"\nScene {scene_index+1}: Generating product image...")
        print(f"  Image prompt: {image_prompt[:100]}...")

        # Generate image using Gemini with the scene's image prompt
        image_bytes = generate_product_image(
            prompt=image_prompt,
            product_image_path=product_image_path,
        )

        # Save image temporarily
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_image_path = os.path.join(
            output_dir, f"product_placement_scene{scene_index+1}_{timestamp}.png"
        )
        with open(temp_image_path, "wb") as f:
            f.write(image_bytes)
        print(f"  ✓ Product image generated: {temp_image_path}")

        # Upload to tmpfiles.org
        print(f"  Uploading image to tmpfiles.org...")
        image_url = upload_image_to_tmpfiles(temp_image_path)
        print(f"  ✓ Image uploaded: {image_url}")
        return image_url

    except Exception as e:
        print(
            f"  ⚠️  Failed to generate/upload product image for scene {scene_index+1}: {e}"
        )
        print(f"  Continuing with text-to-video for scene {scene_index+1}...")
        return None


def _generate_single_broll_video(
    scene_index: int,
    scene: Dict,
    output_dir: str,
    image_url: Optional[str],
) -> Optional[str]:
    """Helper function to generate a single B-roll video."""
    try:
        video_path = generate_broll_video(
            scene["video_prompt"], output_dir, scene_index + 1, image_url
        )
        print(f"  ✓ Scene {scene_index+1} completed")
        return video_path
    except Exception as e:
        print(f"  ✗ Failed to generate scene {scene_index+1}: {e}")
        return None


def _generate_product_image_local(
    scene_index: int,
    image_prompt: str,
    output_dir: str,
    product_image_path: str,
) -> Optional[str]:
    """Helper function to generate product image locally (without uploading) for dry run."""
    try:
        print(f"\nScene {scene_index+1}: Generating product image...")
        print(f"  Image prompt: {image_prompt[:100]}...")

        # Generate image using Gemini with the scene's image prompt
        image_bytes = generate_product_image(
            prompt=image_prompt,
            product_image_path=product_image_path,
        )

        # Save image locally
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_image_path = os.path.join(
            output_dir, f"product_placement_scene{scene_index+1}_{timestamp}.png"
        )
        with open(temp_image_path, "wb") as f:
            f.write(image_bytes)
        print(f"  ✓ Product image generated: {temp_image_path}")
        return temp_image_path

    except Exception as e:
        print(
            f"  ⚠️  Failed to generate product image for scene {scene_index+1}: {e}"
        )
        return None


def _create_video_from_image_dry_run(
    scene_index: int,
    image_path: str,
    output_dir: str,
) -> Optional[str]:
    """Helper function to create a video from an image in dry run mode."""
    try:
        print(f"  Scene {scene_index+1}: Creating video from image...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"broll_scene{scene_index+1}_{timestamp}.mp4")
        
        create_video_from_image(image_path, output_path, duration=10.0)
        print(f"  ✓ Scene {scene_index+1} completed: {output_path}")
        return output_path
    except Exception as e:
        print(f"  ✗ Failed to create video for scene {scene_index+1}: {e}")
        return None


def generate_all_broll_videos(
    script_data: Dict,
    output_dir: str,
    product_image_path: str = "product.png",
    max_workers: int = 5,
    dry_run: bool = False,
) -> List[str]:
    """Generate all B-roll videos from script in parallel.

    Args:
        script_data: Script data containing scenes (each scene should have include_product boolean flag)
        output_dir: Directory to save videos
        product_image_path: Path to product image file
        max_workers: Maximum number of parallel workers for video generation (default: 5)
        dry_run: If True, skip video generation and create videos from images instead (default: False)
    """
    print("\n" + "=" * 60)
    print("STEP 3: Generating B-Roll Videos (Parallel)")
    print("=" * 60)

    scenes = script_data["scenes"]
    if dry_run:
        print(f"DRY RUN MODE: Creating {len(scenes)} B-roll videos from images (10 seconds each)...")
    else:
        print(f"Generating {len(scenes)} B-roll videos with Sora 2 in parallel...")

    if dry_run:
        # Dry run mode: Generate images and convert them to videos
        image_paths = {}  # Store local image paths instead of URLs
        
        # Generate product images for scenes where include_product is True
        scenes_with_product = [
            i for i, scene in enumerate(scenes) if scene.get("include_product", False)
        ]
        
        if scenes_with_product and len(scenes_with_product) > 0:
            print("\n" + "-" * 60)
            print(
                f"Generating product placement images for {len(scenes_with_product)} scene(s) in parallel..."
            )
            print("-" * 60)

            # Generate product images in parallel (but don't upload them)
            with ThreadPoolExecutor(
                max_workers=min(len(scenes_with_product), 3)
            ) as executor:
                future_to_index = {
                    executor.submit(
                        _generate_product_image_local,
                        i,
                        scenes[i]["image_prompt"],
                        output_dir,
                        product_image_path,
                    ): i
                    for i in scenes_with_product
                }

                for future in as_completed(future_to_index):
                    scene_index = future_to_index[future]
                    try:
                        image_path = future.result()
                        if image_path:
                            image_paths[scene_index] = image_path
                    except Exception as e:
                        print(f"  ✗ Error processing scene {scene_index+1}: {e}")
        
        # For scenes without product images, use the product image as placeholder
        if os.path.exists(product_image_path):
            for i, scene in enumerate(scenes):
                if i not in image_paths:
                    image_paths[i] = product_image_path
        else:
            # If product image doesn't exist and we have scenes without images, warn
            missing_scenes = [i for i in range(len(scenes)) if i not in image_paths]
            if missing_scenes:
                print(f"\n⚠️  Warning: Product image not found at {product_image_path}")
                print(f"   Scenes {[s+1 for s in missing_scenes]} will fail without images")
                print("   Please ensure product image exists or scenes have include_product=True")
        
        # Convert all images to 10-second videos
        print("\n" + "-" * 60)
        print(f"Converting {len(image_paths)} images to 10-second videos...")
        print("-" * 60)
        
        broll_paths = [None] * len(scenes)  # Pre-allocate list to maintain order
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(
                    _create_video_from_image_dry_run,
                    i,
                    image_paths.get(i, product_image_path),
                    output_dir,
                ): i
                for i in range(len(scenes))
            }

            for future in as_completed(future_to_index):
                scene_index = future_to_index[future]
                try:
                    video_path = future.result()
                    if video_path:
                        broll_paths[scene_index] = video_path
                except Exception as e:
                    print(f"  ✗ Error processing scene {scene_index+1}: {e}")
        
        # Filter out None values and maintain order
        broll_paths = [path for path in broll_paths if path is not None]
        
        print(f"\n✓ Generated {len(broll_paths)}/{len(scenes)} B-roll videos (dry run)")
        return broll_paths
    
    else:
        # Normal mode: Generate videos using API
        # Generate product images only for scenes where include_product is True
        image_urls = {}
        scenes_with_product = [
            i for i, scene in enumerate(scenes) if scene.get("include_product", False)
        ]

        if scenes_with_product and len(scenes_with_product) > 0:
            print("\n" + "-" * 60)
            print(
                f"Generating product placement images for {len(scenes_with_product)} scene(s) in parallel..."
            )
            print("-" * 60)

            # Generate product images in parallel
            with ThreadPoolExecutor(
                max_workers=min(len(scenes_with_product), 3)
            ) as executor:
                future_to_index = {
                    executor.submit(
                        _generate_product_image_and_upload,
                        i,
                        scenes[i]["image_prompt"],
                        output_dir,
                        product_image_path,
                    ): i
                    for i in scenes_with_product
                }

                for future in as_completed(future_to_index):
                    scene_index = future_to_index[future]
                    try:
                        image_url = future.result()
                        if image_url:
                            image_urls[scene_index] = image_url
                    except Exception as e:
                        print(f"  ✗ Error processing scene {scene_index+1}: {e}")

        # Generate videos for all scenes in parallel
        print("\n" + "-" * 60)
        print(f"Generating {len(scenes)} B-roll videos in parallel...")
        print("-" * 60)

        broll_paths = [None] * len(scenes)  # Pre-allocate list to maintain order

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(
                    _generate_single_broll_video,
                    i,
                    scene,
                    output_dir,
                    image_urls.get(i) if scene.get("include_product", False) else None,
                ): i
                for i, scene in enumerate(scenes)
            }

            for future in as_completed(future_to_index):
                scene_index = future_to_index[future]
                try:
                    video_path = future.result()
                    if video_path:
                        broll_paths[scene_index] = video_path
                except Exception as e:
                    print(f"  ✗ Error processing scene {scene_index+1}: {e}")

        # Filter out None values and maintain order
        broll_paths = [path for path in broll_paths if path is not None]

        print(f"\n✓ Generated {len(broll_paths)}/{len(scenes)} B-roll videos")
        return broll_paths

