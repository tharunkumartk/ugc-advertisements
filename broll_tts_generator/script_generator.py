"""
Script Generation Module

Handles B-roll script generation using OpenAI API or xAI API.
"""

import json
from pathlib import Path
from typing import Dict
from openai import OpenAI

from .config import OPENAI_API_KEY, XAI_API_KEY


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
    topic: str, 
    num_scenes: int = 5, 
    prompt_file: str = "prompts/default_prompt.txt",
    use_xai: bool = False
) -> Dict:
    """
    Generate a B-roll script with narration and visual descriptions.
    
    Args:
        topic: The topic for the video
        num_scenes: Number of scenes to generate
        prompt_file: Path to the prompt template file
        use_xai: If True, use xAI API; otherwise use OpenAI API
        
    Returns:
        Dictionary containing script data with scenes, narration, etc.
    """
    if use_xai:
        return _generate_broll_script_xai(topic, num_scenes, prompt_file)
    else:
        return _generate_broll_script_openai(topic, num_scenes, prompt_file)


def _generate_broll_script_openai(
    topic: str, num_scenes: int = 5, prompt_file: str = "prompts/default_prompt.txt"
) -> Dict:
    """Generate a B-roll script using OpenAI API."""
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


def _generate_broll_script_xai(
    topic: str, num_scenes: int = 5, prompt_file: str = "prompts/default_prompt.txt"
) -> Dict:
    """Generate a B-roll script using xAI API."""
    try:
        from xai_sdk import Client
        from xai_sdk.chat import user
    except ImportError:
        raise ImportError(
            "xai_sdk is required for xAI API. Install it with: pip install xai-sdk"
        )
    
    if not XAI_API_KEY:
        raise ValueError("XAI_API_KEY environment variable is not set")

    print("\n" + "=" * 60)
    print("STEP 1: Generating B-Roll Script (using xAI)")
    print("=" * 60)

    client = Client(api_key=XAI_API_KEY)

    # Generate the prompt
    prompt_text = generate_broll_script_prompt(topic, num_scenes, prompt_file=prompt_file)
    
    # Add JSON schema instruction to the prompt
    schema_instruction = f"""

IMPORTANT: You must respond with ONLY a valid JSON object matching this exact schema:
{{
    "scenes": [
        {{
            "narration": "string (exactly 30 words)",
            "image_prompt": "string",
            "video_prompt": "string",
            "include_product": boolean
        }}
    ],
    "musicGenerationPrompt": "string",
    "musicStyle": "string",
    "musicTitle": "string"
}}

You must generate exactly {num_scenes} scenes. Return ONLY the JSON, no markdown, no explanations, no code blocks."""

    full_prompt = prompt_text + schema_instruction

    # Create chat and get response
    chat = client.chat.create(
        model="grok-4",  # Using grok-4 model (can be changed to grok-2-1212 or other available models)
        search_parameters={},  # Disable search for script generation
    )
    
    chat.append(user(full_prompt))
    response = chat.sample()

    # Parse JSON from response
    content = response.content.strip()
    
    # Clean up markdown code blocks if present
    if content.startswith("```"):
        lines = content.split("\n")
        if len(lines) > 2:
            # Remove first and last lines (markdown code block markers)
            content = "\n".join(lines[1:-1])
        else:
            content = content.strip("```")
    
    # Remove json language identifier if present
    if content.startswith("json\n"):
        content = content[5:]
    elif content.startswith("```json"):
        content = content[7:].rstrip("```").strip()

    try:
        script_data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response from xAI: {e}\nResponse content: {content[:500]}")

    # Validate structure
    if not isinstance(script_data, dict) or "scenes" not in script_data:
        raise ValueError(f"Invalid script data structure: {script_data}")

    # Validate scene count
    actual_scene_count = len(script_data["scenes"])
    if actual_scene_count != num_scenes:
        raise ValueError(
            f"Script generated {actual_scene_count} scenes, but {num_scenes} were requested. "
            f"Please check the prompt template or try again."
        )

    # Ensure all required fields are present
    required_fields = ["musicGenerationPrompt", "musicStyle", "musicTitle"]
    for field in required_fields:
        if field not in script_data:
            raise ValueError(f"Missing required field in script data: {field}")

    # Validate each scene has required fields
    for i, scene in enumerate(script_data["scenes"]):
        required_scene_fields = ["narration", "image_prompt", "video_prompt", "include_product"]
        for field in required_scene_fields:
            if field not in scene:
                raise ValueError(f"Scene {i+1} missing required field: {field}")

    # Create full narration text
    full_narration = " ".join([scene["narration"] for scene in script_data["scenes"]])
    script_data["full_narration"] = full_narration

    print(f"✓ Script generated with {len(script_data['scenes'])} scenes")
    print(f"✓ Full narration length: {len(full_narration)} characters")

    return script_data

