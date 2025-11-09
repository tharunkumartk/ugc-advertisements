"""
Product Image Generation Module

Handles product image generation using Gemini API and uploading to tmpfiles.org.
"""

import os
import json
import requests
from typing import Optional
from PIL import Image
from google import genai
from google.genai import types

from .config import KIE_AI_API_KEY


class GeminiImageError(RuntimeError):
    """Raised when the Gemini API does not return a valid image payload."""


def _extract_image_bytes(response: genai.types.GenerateContentResponse) -> bytes:
    """Extract the first inline image payload from a Gemini response."""
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and getattr(inline_data, "data", None):
                data = inline_data.data
                # `data` may already be bytes; if it's a memoryview convert accordingly.
                if isinstance(data, bytes):
                    return data
                if isinstance(data, memoryview):
                    return data.tobytes()
    raise GeminiImageError("Gemini response did not include generated image data.")


def generate_product_image(
    prompt: str, product_image_path: str = "product.png"
) -> bytes:
    """Generate an image using Gemini API with product image and prompt.

    Args:
        prompt: Text prompt describing what to generate.
        product_image_path: Path to the product image file.

    Returns:
        Raw bytes of the generated image.

    Raises:
        FileNotFoundError: If product_image_path doesn't exist.
        GeminiImageError: If the Gemini API fails to return an image payload.
    """
    if not os.path.exists(product_image_path):
        raise FileNotFoundError(f"Product image not found: {product_image_path}")

    # Load product image
    product_image = Image.open(product_image_path)
    product_image.load()  # Ensure image is fully loaded

    # Initialize Gemini client
    client = genai.Client()

    # Generate content with image and prompt
    model = "gemini-2.5-flash-image"
    config = types.GenerateContentConfig(
        image_config=types.ImageConfig(
            aspect_ratio="9:16",
        )
    )
    response = client.models.generate_content(
        model=model,
        contents=[product_image, prompt],
        config=config,
    )

    return _extract_image_bytes(response)


def remove_background(product_image_path: str, output_path: str = "product_bg_rm.png") -> str:
    """Remove background from product image using Gemini 2.5 Flash.
    
    Args:
        product_image_path: Path to the product image file.
        output_path: Path where the background-removed image will be saved.
    
    Returns:
        Path to the saved background-removed image.
    
    Raises:
        FileNotFoundError: If product_image_path doesn't exist.
        GeminiImageError: If the Gemini API fails to return an image payload.
    """
    if not os.path.exists(product_image_path):
        raise FileNotFoundError(f"Product image not found: {product_image_path}")
    
    # Load product image
    product_image = Image.open(product_image_path)
    product_image.load()  # Ensure image is fully loaded
    
    # Initialize Gemini client
    client = genai.Client()
    
    # Use Gemini 2.5 Flash to remove background
    model = "gemini-2.5-flash-image"
    prompt = "Remove the background from this product image. Keep only the product itself with a transparent background. Make sure the product edges are clean and sharp."
    
    config = types.GenerateContentConfig(
        image_config=types.ImageConfig(
            aspect_ratio="9:16",
        )
    )
    response = client.models.generate_content(
        model=model,
        contents=[product_image, prompt],
        config=config,
    )
    
    # Extract image bytes
    image_bytes = _extract_image_bytes(response)
    
    # Save the background-removed image
    with open(output_path, "wb") as f:
        f.write(image_bytes)
    
    return output_path


def upload_image_to_tmpfiles(image_path: str) -> str:
    """
    Upload an image file to tmpfiles.org and return the public download URL.

    Args:
        image_path: Path to the image file to upload

    Returns:
        Public URL to the uploaded image

    Raises:
        Exception: If upload fails
    """
    url = "https://tmpfiles.org/api/v1/upload"

    try:
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f)}
            response = requests.post(url, files=files)
            response.raise_for_status()
            result = response.json()

            # Parse the response to get the download URL
            # The API returns: {"status":"success","data":{"url":"http://tmpfiles.org/{id}/{filename}"}}
            if result.get("status") == "success":
                url = result.get("data", {}).get("url")
                if url:
                    # Convert to direct download URL
                    # Format: http://tmpfiles.org/{id}/{filename} -> https://tmpfiles.org/dl/{id}/{filename}
                    if url.startswith("http://tmpfiles.org/"):
                        # Extract the path after the domain
                        path = url.replace("http://tmpfiles.org/", "")
                        # Convert to direct download URL
                        return f"https://tmpfiles.org/dl/{path}"
                    elif url.startswith("https://tmpfiles.org/"):
                        # Already HTTPS, just add /dl/
                        path = url.replace("https://tmpfiles.org/", "")
                        return f"https://tmpfiles.org/dl/{path}"
                    else:
                        # Return as-is if already a full URL
                        return url
            else:
                error_msg = result.get("message", "Unknown error")
                raise Exception(f"Upload failed: {error_msg}")

            raise Exception("Could not extract download URL from response")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ HTTP Error uploading image: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Response text: {e.response.text}")
        raise
    except Exception as e:
        print(f"\n✗ Error uploading image: {str(e)}")
        raise

