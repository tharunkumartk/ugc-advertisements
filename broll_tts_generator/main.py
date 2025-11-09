"""
Main Orchestration Module

Coordinates the complete B-roll + TTS video generation pipeline.
"""

import os
import json
import random
from pathlib import Path
from typing import Dict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import OPENAI_API_KEY, KIE_AI_API_KEY, ELEVEN_LABS_API_KEY
from .script_generator import generate_broll_script
from .tts_generator import generate_tts_audio
from .music_generator import generate_music
from .video_generator import generate_all_broll_videos
from .video_combiner import combine_broll_with_audio
from .prompt_generator import generate_themed_prompt, save_prompt_template
from .product_image import remove_background
from .supabase_upload import upload_to_supabase


def generate_broll_video_with_tts(
    topic: str,
    num_scenes: int = 5,
    tts_voice: str = "nova",
    output_dir: str = "output",
    product_image_path: str = "product.png",
    prompt_file: str = "prompts/default_prompt.txt",
    max_workers: int = 5,
    dry_run: bool = False,
    use_eleven_labs: bool = False,
    remove_bg: bool = False,
    upload_supabase: bool = False,
    enable_music: bool = True,
    music_model: str = "V5",
) -> Dict:
    """
    Complete B-roll + TTS video generation pipeline.

    Args:
        topic: Topic/description for the video content
        num_scenes: Number of B-roll scenes to generate (default: 5)
        tts_voice: OpenAI TTS voice (alloy, echo, fable, onyx, nova, shimmer) or ElevenLabs voice_id
        output_dir: Directory to save output files
        product_image_path: Path to product image file (default: product.png)
        prompt_file: Path to prompt template file (default: prompts/default_prompt.txt)
        max_workers: Maximum number of parallel workers for video generation (default: 5)
        dry_run: If True, skip video generation and use images extended to 10 seconds (default: False)
        use_eleven_labs: If True, use ElevenLabs API for TTS instead of OpenAI (default: False)
        remove_bg: If True, remove background from product image before processing (default: False)
        upload_supabase: If True, upload final video to Supabase bucket (default: False)
        enable_music: If True, generate background music (default: True)
        music_model: AI model version for music generation (V3_5, V4, V4_5, V4_5PLUS, V5) (default: V5)

    Returns:
        Dictionary with paths to generated files
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    results = {"timestamp": timestamp, "output_dir": output_dir, "topic": topic}

    if dry_run:
        results["dry_run"] = True
        print("\n" + "=" * 60)
        print("DRY RUN MODE ENABLED")
        print("=" * 60)
        print("Videos will be created from images extended to 10 seconds")
        print("No video generation API calls will be made")
        print("=" * 60 + "\n")

    try:
        # Step 0: Remove background if requested (before any other processing)
        # This updated product_image_path will be used for ALL product image generation
        # including nano banana and other product placement images
        if remove_bg:
            print("\n" + "=" * 60)
            print("REMOVING BACKGROUND FROM PRODUCT IMAGE")
            print("=" * 60)
            bg_removed_path = os.path.join(output_dir, "product_bg_rm.png")
            print(f"Removing background from: {product_image_path}")
            try:
                remove_background(product_image_path, bg_removed_path)
                product_image_path = bg_removed_path  # Update to use bg-removed version for all subsequent operations
                print(f"✓ Background removed. Using: {product_image_path}")
                print("  This image will be used for all product image generation.")
                results["bg_removed_image_path"] = bg_removed_path
            except Exception as e:
                print(f"⚠️  Warning: Failed to remove background: {e}")
                print("Continuing with original product image...")
            print("=" * 60 + "\n")

        # Step 1: Generate script
        script_data = generate_broll_script(topic, num_scenes, prompt_file=prompt_file)
        script_path = os.path.join(output_dir, f"broll_script_{timestamp}.json")
        with open(script_path, "w") as f:
            json.dump(script_data, f, indent=2)
        results["script_path"] = script_path
        results["script"] = script_data

        # Step 2: Generate TTS audio
        tts_audio_path = generate_tts_audio(
            script_data["full_narration"],
            output_dir,
            voice=tts_voice,
            use_eleven_labs=use_eleven_labs,
        )
        results["tts_audio_path"] = tts_audio_path

        # Step 2.5: Generate background music (if enabled)
        background_music_path = None
        if enable_music:
            try:
                music_prompt = script_data.get("musicGenerationPrompt", "")
                music_style = script_data.get("musicStyle", "Ambient")
                music_title = script_data.get("musicTitle", "Background Music")

                if music_prompt:
                    # Get TTS audio duration to generate music of appropriate length
                    import subprocess

                    cmd = [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "default=noprint_wrappers=1:nokey=1",
                        tts_audio_path,
                    ]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, check=True
                    )
                    narration_duration = float(result.stdout.strip())

                    background_music_path = generate_music(
                        music_prompt=music_prompt,
                        style=music_style,
                        title=music_title,
                        output_dir=output_dir,
                        duration_seconds=narration_duration,
                        model=music_model,
                    )
                    results["background_music_path"] = background_music_path
                else:
                    print(
                        "⚠️  Warning: No musicGenerationPrompt in script data, skipping music generation"
                    )
            except Exception as e:
                print(f"⚠️  Warning: Failed to generate background music: {e}")
                print("Continuing without background music...")

        # Step 3: Generate B-roll videos (in parallel)
        broll_paths = generate_all_broll_videos(
            script_data,
            output_dir,
            product_image_path=product_image_path,
            max_workers=max_workers,
            dry_run=dry_run,
        )
        results["broll_paths"] = broll_paths

        if not broll_paths:
            raise Exception("No B-roll videos were generated successfully")

        # Step 4: Combine B-roll with audio (and background music if available)
        # Extract prompt name from prompt_file path (e.g., "prompts/default_prompt.txt" -> "default_prompt")
        prompt_name = Path(prompt_file).stem
        final_video_path = os.path.join(
            output_dir, f"final_{prompt_name}_{timestamp}.mp4"
        )
        combine_broll_with_audio(
            broll_paths,
            tts_audio_path,
            final_video_path,
            background_music_path=background_music_path,
        )
        results["final_video_path"] = final_video_path

        # Upload to Supabase if requested
        if upload_supabase:
            public_url = upload_to_supabase(final_video_path)
            if public_url:
                results["supabase_url"] = public_url

        print("\n" + "=" * 60)
        print("✓ VIDEO GENERATION COMPLETE!")
        print("=" * 60)
        print(f"Final video: {final_video_path}")
        if upload_supabase and results.get("supabase_url"):
            print(f"Supabase URL: {results['supabase_url']}")

        return results

    except Exception as e:
        print(f"\n✗ Error during video generation: {e}")
        import traceback

        traceback.print_exc()
        results["error"] = str(e)
        return results


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate B-roll video with TTS narration"
    )
    parser.add_argument(
        "topic",
        nargs="?",
        help="Topic/description for the video (optional if --all-prompts is used)",
    )
    parser.add_argument(
        "--scenes",
        type=int,
        default=5,
        help="Number of B-roll scenes to generate (default: 5)",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=None,
        help="OpenAI TTS voice (alloy, echo, fable, onyx, nova, shimmer) or ElevenLabs voice_id when using --eleven-labs (default: random for OpenAI, default voice_id for ElevenLabs)",
    )
    parser.add_argument(
        "--output-dir", default="output", help="Output directory (default: output)"
    )
    parser.add_argument(
        "--product-image",
        type=str,
        default="product.png",
        help="Path to product image file (default: product.png)",
    )
    parser.add_argument(
        "--prompt-file",
        type=str,
        default="prompts/default_prompt.txt",
        help="Path to prompt template file (default: prompts/default_prompt.txt)",
    )
    parser.add_argument(
        "--all-prompts",
        action="store_true",
        help="Generate videos for all prompts in prompts/ directory in parallel",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Maximum number of parallel workers for video generation (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode: skip video generation and use images extended to 10 seconds instead",
    )
    parser.add_argument(
        "--new-prompt",
        type=str,
        default=None,
        help="Generate a new themed prompt template with the given theme name (e.g., 'space', 'ocean'). The generated prompt will be saved to prompts/ and used for video generation.",
    )
    parser.add_argument(
        "--eleven-labs",
        action="store_true",
        help="Use ElevenLabs API for TTS instead of OpenAI (requires ELEVEN_LABS_API_KEY)",
    )
    parser.add_argument(
        "--remove-background",
        action="store_true",
        help="Remove background from product image using Gemini 2.5 Flash before processing (saves as product_bg_rm.png)",
    )
    parser.add_argument(
        "--upload-supabase",
        action="store_true",
        help="Upload final video to Supabase bucket 'generated-ugc' (requires SUPABASE_KEY environment variable)",
    )
    parser.add_argument(
        "--no-music",
        action="store_true",
        help="Disable background music generation (music is enabled by default)",
    )
    parser.add_argument(
        "--music-model",
        type=str,
        default="V5",
        choices=["V3_5", "V4", "V4_5", "V4_5PLUS", "V5"],
        help="AI model version for music generation (default: V5)",
    )

    args = parser.parse_args()

    # Select random voice if not specified
    if args.voice is None:
        if args.eleven_labs:
            # Default ElevenLabs voice_id (you can change this to any voice_id you prefer)
            args.voice = "RXtWW6etvimS8QJ5nhVk"
            print(f"🎲 Using default ElevenLabs voice_id: {args.voice}")
        else:
            available_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
            args.voice = random.choice(available_voices)
            print(f"🎲 Using random OpenAI voice: {args.voice}")
    elif not args.eleven_labs:
        # Validate OpenAI voice if specified
        available_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if args.voice not in available_voices:
            print(f"⚠️  Warning: '{args.voice}' is not a valid OpenAI voice.")
            print(f"   Valid voices: {', '.join(available_voices)}")
            print(f"   Using '{args.voice}' anyway (may cause an error)")

    # Check for required API keys (skip in dry run mode for video generation)
    missing_keys = []
    if args.eleven_labs:
        if not ELEVEN_LABS_API_KEY:
            missing_keys.append("ELEVEN_LABS_API_KEY")
    else:
        if not OPENAI_API_KEY:
            missing_keys.append("OPENAI_API_KEY")
    # KIE_AI_API_KEY needed for video generation (unless dry run) or music generation
    needs_kie_api = (not args.dry_run) or (not args.no_music)
    if needs_kie_api and not KIE_AI_API_KEY:
        if not args.dry_run and not args.no_music:
            missing_keys.append(
                "KIE_AI_API_KEY (required for video and music generation)"
            )
        elif not args.dry_run:
            missing_keys.append("KIE_AI_API_KEY (required for video generation)")
        else:
            missing_keys.append("KIE_AI_API_KEY (required for music generation)")

    if missing_keys:
        print(f"⚠️  Missing required API keys: {', '.join(missing_keys)}")
        print("Please set them as environment variables or in a .env file")
        if args.dry_run:
            print("Note: KIE_AI_API_KEY is not required in dry run mode")
        return 1

    # Check if product image exists (will be needed if any scene has include_product=true)
    if not os.path.exists(args.product_image):
        print(f"⚠️  Product image not found: {args.product_image}")
        print("Note: Product image is required if any scene has include_product=true")
        print(
            "The script will continue, but product image generation will fail for those scenes."
        )

    # Check if Gemini libraries are available (needed for product image generation)
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
    except ImportError:
        print("⚠️  Product image generation requires google-genai and pillow")
        print("Please install: pip install google-genai pillow")
        print(
            "The script will continue, but product image generation will fail if needed."
        )

    # Handle --all-prompts flag
    if args.all_prompts:
        # Find all prompt files in prompts/ directory
        script_dir = Path(__file__).parent.parent
        prompts_dir = script_dir / "prompts"

        if not prompts_dir.exists():
            print(f"❌ Prompts directory not found: {prompts_dir}")
            return 1

        prompt_files = list(prompts_dir.glob("*.txt"))

        if not prompt_files:
            print(f"❌ No prompt files found in {prompts_dir}")
            return 1

        print(f"\n{'=' * 60}")
        print(f"Generating videos for {len(prompt_files)} prompts in parallel")
        print(f"{'=' * 60}")

        # Get topic from args or use default
        topic = args.topic or "premium product"

        # Generate videos for all prompts in parallel
        all_results = []
        with ThreadPoolExecutor(max_workers=len(prompt_files)) as executor:
            future_to_prompt = {
                executor.submit(
                    generate_broll_video_with_tts,
                    topic=topic,
                    num_scenes=args.scenes,
                    tts_voice=args.voice,
                    output_dir=args.output_dir,
                    product_image_path=args.product_image,
                    prompt_file=f"prompts/{prompt_file.name}",
                    max_workers=args.max_workers,
                    dry_run=args.dry_run,
                    use_eleven_labs=args.eleven_labs,
                    remove_bg=args.remove_background,
                    upload_supabase=args.upload_supabase,
                    enable_music=not args.no_music,
                    music_model=args.music_model,
                ): prompt_file.name
                for prompt_file in prompt_files
            }

            for future in as_completed(future_to_prompt):
                prompt_name = future_to_prompt[future]
                try:
                    result = future.result()
                    all_results.append((prompt_name, result))
                    if "error" in result:
                        print(
                            f"\n❌ Generation failed for {prompt_name}: {result['error']}"
                        )
                    else:
                        print(f"\n✅ Success for {prompt_name}!")
                        print(
                            f"   Final video: {result.get('final_video_path', 'N/A')}"
                        )
                except Exception as e:
                    print(f"\n❌ Error generating video for {prompt_name}: {e}")
                    all_results.append((prompt_name, {"error": str(e)}))

        print(f"\n{'=' * 60}")
        print(
            f"Completed {len([r for _, r in all_results if 'error' not in r])}/{len(all_results)} videos"
        )
        print(f"{'=' * 60}")

        return 0 if all("error" not in r for _, r in all_results) else 1

    # Handle --new-prompt flag: generate a new themed prompt
    prompt_file_to_use = args.prompt_file
    if args.new_prompt:
        if not args.topic:
            parser.error("topic is required when using --new-prompt")

        print(f"\n{'=' * 60}")
        print(f"Generating new prompt template with theme: {args.new_prompt}")
        print(f"{'=' * 60}")

        try:
            # Generate the new prompt
            generated_prompt = generate_themed_prompt(
                theme=args.new_prompt,
                topic=args.topic,
            )

            # Save the prompt to prompts folder
            saved_path = save_prompt_template(
                prompt_content=generated_prompt,
                theme=args.new_prompt,
            )

            # Use the newly generated prompt for video generation
            # Convert absolute path to relative path from script directory
            script_dir = Path(__file__).parent.parent
            prompt_file_to_use = saved_path.relative_to(script_dir)

            print(f"✓ Using newly generated prompt: {prompt_file_to_use}")

        except Exception as e:
            print(f"\n❌ Error generating prompt template: {e}")
            import traceback

            traceback.print_exc()
            return 1

    # Single video generation
    if not args.topic:
        parser.error("topic is required unless --all-prompts is used")

    # Run generation
    results = generate_broll_video_with_tts(
        topic=args.topic,
        num_scenes=args.scenes,
        tts_voice=args.voice,
        output_dir=args.output_dir,
        product_image_path=args.product_image,
        prompt_file=str(prompt_file_to_use),
        max_workers=args.max_workers,
        dry_run=args.dry_run,
        use_eleven_labs=args.eleven_labs,
        remove_bg=args.remove_background,
        upload_supabase=args.upload_supabase,
        enable_music=not args.no_music,
        music_model=args.music_model,
    )

    if "error" in results:
        print(f"\n❌ Generation failed: {results['error']}")
        return 1

    print("\n✅ Success! Check the output directory for generated files.")
    return 0


if __name__ == "__main__":
    exit(main())
