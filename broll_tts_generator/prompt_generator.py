"""
Prompt Generation Module

Generates new themed prompt templates using OpenAI API or xAI API based on default prompt.
"""

import os
from pathlib import Path
from typing import Optional
from openai import OpenAI

from .config import OPENAI_API_KEY, XAI_API_KEY


def generate_themed_prompt(
    theme: str,
    topic: Optional[str] = None,
    default_prompt_file: str = "prompts/default_prompt.txt",
    model: str = "gpt-5",
    use_xai: bool = False,
) -> str:
    """
    Generate a new themed prompt template using OpenAI API or xAI API.

    Args:
        theme: The theme name (e.g., "space", "ocean", "forest")
        topic: Optional topic to include in the generation context
        default_prompt_file: Path to the default prompt template
        model: Model to use (OpenAI model name or ignored if use_xai=True)
        use_xai: If True, use xAI API; otherwise use OpenAI API

    Returns:
        Generated prompt template as a string
    """
    if use_xai:
        return _generate_themed_prompt_xai(theme, topic, default_prompt_file)
    else:
        return _generate_themed_prompt_openai(theme, topic, default_prompt_file, model)


def _generate_themed_prompt_openai(
    theme: str,
    topic: Optional[str] = None,
    default_prompt_file: str = "prompts/default_prompt.txt",
    model: str = "gpt-5",
) -> str:
    """Generate a new themed prompt template using OpenAI API."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    # Get the directory where this script is located
    script_dir = Path(__file__).parent.parent

    # Read the default prompt
    default_prompt_path = script_dir / default_prompt_file
    try:
        with open(default_prompt_path, "r") as f:
            default_prompt = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Default prompt file not found: {default_prompt_path}")

    # Create the generation prompt
    generation_prompt = f"""You are an expert at creating prompt templates for AI video generation.

I need you to create a new prompt template that follows the same structure and quality standards as the default prompt, but with a different theme: "{theme}".

Here is the DEFAULT prompt template (base structure):
{default_prompt}

Your task:
1. Create a new prompt template with the theme: "{theme}"
2. Maintain the EXACT same structure, format, and output requirements as the default prompt
3. Adapt the language, visual descriptions, and examples to match the "{theme}" theme
4. Keep all the critical requirements (exactly {{num_scenes}} scenes, 30 words per narration, no people/hands, different camera angles, etc.)
5. Include a complete example JSON structure at the end with the theme applied
6. Use the same formatting and placeholders ({{topic}}, {{num_scenes}})

The generated prompt should:
- Have the same structure and sections as the default prompt
- Include theme-specific language and visual descriptions
- Maintain all quality requirements and constraints
- Include a complete example that demonstrates the theme
- Be ready to use as a prompt template file

Return ONLY the prompt template text, without any markdown formatting, code blocks, or explanations."""

    if topic:
        generation_prompt += (
            f"\n\nNote: The prompt will be used for videos about: {topic}"
        )

    print(f"\n{'=' * 60}")
    print(f"Generating prompt template with theme: {theme}")
    print(f"{'=' * 60}")

    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert at creating prompt templates for AI video generation. You maintain strict adherence to structure and formatting requirements.",
            },
            {"role": "user", "content": generation_prompt},
        ],
    )

    generated_prompt = response.choices[0].message.content.strip()

    # Clean up any markdown formatting that might have been added
    if generated_prompt.startswith("```"):
        lines = generated_prompt.split("\n")
        if len(lines) > 2:
            generated_prompt = "\n".join(lines[1:-1])
        else:
            generated_prompt = generated_prompt.strip("```")

    print(f"✓ Prompt template generated successfully")
    print(f"  Length: {len(generated_prompt)} characters")

    return generated_prompt


def _generate_themed_prompt_xai(
    theme: str,
    topic: Optional[str] = None,
    default_prompt_file: str = "prompts/default_prompt.txt",
) -> str:
    """Generate a new themed prompt template using xAI API."""
    try:
        from xai_sdk import Client
        from xai_sdk.chat import user
    except ImportError:
        raise ImportError(
            "xai_sdk is required for xAI API. Install it with: pip install xai-sdk"
        )

    if not XAI_API_KEY:
        raise ValueError("XAI_API_KEY environment variable is not set")

    # Get the directory where this script is located
    script_dir = Path(__file__).parent.parent

    # Read the default prompt
    default_prompt_path = script_dir / default_prompt_file
    try:
        with open(default_prompt_path, "r") as f:
            default_prompt = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Default prompt file not found: {default_prompt_path}")

    # Create the generation prompt
    generation_prompt = f"""You are an expert at creating prompt templates for AI video generation.

I need you to create a new prompt template that follows the same structure and quality standards as the default prompt, but with a different theme: "{theme}".

Here is the DEFAULT prompt template (base structure):
{default_prompt}

Your task:
1. Create a new prompt template with the theme: "{theme}"
2. Maintain the EXACT same structure, format, and output requirements as the default prompt
3. Adapt the language, visual descriptions, and examples to match the "{theme}" theme
4. Keep all the critical requirements (exactly {{num_scenes}} scenes, 30 words per narration, no people/hands, different camera angles, etc.)
5. Include a complete example JSON structure at the end with the theme applied
6. Use the same formatting and placeholders ({{topic}}, {{num_scenes}})

The generated prompt should:
- Have the same structure and sections as the default prompt
- Include theme-specific language and visual descriptions
- Maintain all quality requirements and constraints
- Include a complete example that demonstrates the theme
- Be ready to use as a prompt template file

Return ONLY the prompt template text, without any markdown formatting, code blocks, or explanations."""

    if topic:
        generation_prompt += (
            f"\n\nNote: The prompt will be used for videos about: {topic}"
        )

    print(f"\n{'=' * 60}")
    print(f"Generating prompt template with theme: {theme} (using xAI)")
    print(f"{'=' * 60}")

    client = Client(api_key=XAI_API_KEY)

    # Create chat and get response
    chat = client.chat.create(
        model="grok-4",  # Using grok-4 model (can be changed to grok-2-1212 or other available models)
        search_parameters={},  # Disable search for prompt generation
    )

    chat.append(user(generation_prompt))
    response = chat.sample()

    generated_prompt = response.content.strip()

    # Clean up any markdown formatting that might have been added
    if generated_prompt.startswith("```"):
        lines = generated_prompt.split("\n")
        if len(lines) > 2:
            generated_prompt = "\n".join(lines[1:-1])
        else:
            generated_prompt = generated_prompt.strip("```")

    print(f"✓ Prompt template generated successfully")
    print(f"  Length: {len(generated_prompt)} characters")

    return generated_prompt


def save_prompt_template(
    prompt_content: str,
    theme: str,
    prompts_dir: str = "prompts",
) -> Path:
    """
    Save the generated prompt template to a file.

    Args:
        prompt_content: The prompt template content to save
        theme: The theme name (used for filename)
        prompts_dir: Directory to save the prompt file

    Returns:
        Path to the saved prompt file
    """
    script_dir = Path(__file__).parent.parent
    prompts_path = script_dir / prompts_dir

    # Create prompts directory if it doesn't exist
    prompts_path.mkdir(exist_ok=True)

    # Create filename from theme (sanitize for filesystem)
    safe_theme = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in theme)
    filename = f"{safe_theme}_prompt.txt"
    file_path = prompts_path / filename

    # Save the prompt
    with open(file_path, "w") as f:
        f.write(prompt_content)

    print(f"✓ Prompt template saved to: {file_path}")

    return file_path
