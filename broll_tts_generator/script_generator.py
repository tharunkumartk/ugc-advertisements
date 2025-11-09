"""
Script Generation Module

Handles B-roll script generation using OpenAI API.
"""

import json
from pathlib import Path
from typing import Dict
from openai import OpenAI

from .config import OPENAI_API_KEY


def generate_broll_script_prompt(
    topic: str, num_scenes: int = 5, prompt_file: str = "prompts/default_prompt.txt"
) -> str:
    """
    Generate the prompt for B-roll script generation.

    Args:
        topic: The topic for the video
        num_scenes: Number of scenes to generate
        prompt_file: Path to the prompt template file (relative to script location)

    Returns:
        Formatted prompt string with topic and num_scenes filled in
    """
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.parent
    prompt_path = script_dir / prompt_file

    # Read the prompt template
    try:
        with open(prompt_path, "r") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    # Replace placeholders with actual values (using replace instead of format to avoid issues with JSON braces)
    return prompt_template.replace("{topic}", topic).replace("{num_scenes}", str(num_scenes))


def generate_broll_script(
    topic: str, num_scenes: int = 5, prompt_file: str = "prompts/default_prompt.txt"
) -> Dict:
    """Generate a B-roll script with narration and visual descriptions."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    print("\n" + "=" * 60)
    print("STEP 1: Generating B-Roll Script")
    print("=" * 60)

    client = OpenAI(api_key=OPENAI_API_KEY)

    # Define the schema for structured output
    schema = {
        "type": "object",
        "properties": {
            "scenes": {
                "type": "array",
                "minItems": num_scenes,
                "maxItems": num_scenes,
                "items": {
                    "type": "object",
                    "properties": {
                        "narration": {"type": "string"},
                        "image_prompt": {"type": "string"},
                        "video_prompt": {"type": "string"},
                        "include_product": {"type": "boolean"},
                    },
                    "required": [
                        "narration",
                        "image_prompt",
                        "video_prompt",
                        "include_product",
                    ],
                    "additionalProperties": False,
                },
            },
            "musicGenerationPrompt": {
                "type": "string",
                "description": "Description for generating background music that matches the overall mood and theme of all scenes"
            },
            "musicStyle": {
                "type": "string",
                "description": "Music style/genre for the background music (e.g., 'Ambient', 'Cinematic', 'Electronic', 'Classical')"
            },
            "musicTitle": {
                "type": "string",
                "description": "Title for the background music track"
            }
        },
        "required": ["scenes", "musicGenerationPrompt", "musicStyle", "musicTitle"],
        "additionalProperties": False,
    }

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": generate_broll_script_prompt(
                    topic, num_scenes, prompt_file=prompt_file
                ),
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"schema": schema, "strict": True, "name": "broll_script"},
        },
    )

    message = response.choices[0].message
    script_data = message.parsed

    # Fallback parsing if needed
    if script_data is None:
        content = message.content
        if content:
            try:
                content_clean = content.strip()
                if content_clean.startswith("```"):
                    lines = content_clean.split("\n")
                    content_clean = (
                        "\n".join(lines[1:-1]) if len(lines) > 2 else content_clean
                    )
                script_data = json.loads(content_clean)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON response: {e}")
        else:
            raise ValueError("No parsed data or content in API response")

    if not isinstance(script_data, dict) or "scenes" not in script_data:
        raise ValueError(f"Invalid script data structure: {script_data}")

    # Validate scene count matches requested number
    actual_scene_count = len(script_data["scenes"])
    if actual_scene_count != num_scenes:
        raise ValueError(
            f"Script generated {actual_scene_count} scenes, but {num_scenes} were requested. "
            f"Please check the prompt template or try again."
        )

    # Create full narration text
    full_narration = " ".join([scene["narration"] for scene in script_data["scenes"]])
    script_data["full_narration"] = full_narration

    print(f"✓ Script generated with {len(script_data['scenes'])} scenes")
    print(f"✓ Full narration length: {len(full_narration)} characters")

    return script_data

