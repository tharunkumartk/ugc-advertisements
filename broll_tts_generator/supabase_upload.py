"""
Supabase Upload Module

Handles uploading files to Supabase storage buckets.
"""

import os
from pathlib import Path
from typing import Optional
from supabase import create_client, Client
from .config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET


def upload_to_supabase(
    file_path: str,
    bucket_name: Optional[str] = None,
    object_name: Optional[str] = None,
) -> Optional[str]:
    """
    Upload a file to Supabase storage bucket.

    Args:
        file_path: Path to the file to upload
        bucket_name: Name of the bucket (defaults to SUPABASE_BUCKET from config)
        object_name: Name/path for the object in the bucket (defaults to filename)

    Returns:
        Public URL of the uploaded file, or None if upload failed
    """
    if not SUPABASE_KEY:
        print("⚠️  SUPABASE_KEY not set. Cannot upload to Supabase.")
        return None

    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        return None

    try:
        # Initialize Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Use default bucket if not specified
        bucket = bucket_name or SUPABASE_BUCKET

        # Use filename if object_name not specified
        if object_name is None:
            object_name = Path(file_path).name

        print(f"\n{'=' * 60}")
        print("UPLOADING TO SUPABASE")
        print("=" * 60)
        print(f"File: {file_path}")
        print(f"Bucket: {bucket}")
        print(f"Object: {object_name}")

        # Read file content
        with open(file_path, "rb") as f:
            file_content = f.read()

        # Upload file - try with upsert first, then fallback to regular upload
        storage = supabase.storage.from_(bucket)
        try:
            # Try upload with upsert (allows overwriting)
            response = storage.upload(
                path=object_name,
                file=file_content,
                file_options={"content-type": "video/mp4", "upsert": True},
            )
        except Exception:
            # If upsert fails, try regular upload (for new files)
            try:
                response = storage.upload(
                    path=object_name,
                    file=file_content,
                    file_options={"content-type": "video/mp4"},
                )
            except Exception as e:
                # If file exists, try update
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    response = storage.update(
                        path=object_name,
                        file=file_content,
                        file_options={"content-type": "video/mp4"},
                    )
                else:
                    raise

        # Get public URL
        public_url = storage.get_public_url(object_name)

        print(f"✓ Upload successful!")
        print(f"Public URL: {public_url}")
        print("=" * 60 + "\n")

        return public_url

    except Exception as e:
        print(f"\n❌ Error uploading to Supabase: {e}")
        import traceback

        traceback.print_exc()
        return None

