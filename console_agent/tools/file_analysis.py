"""
File Analysis tool wrapper.
Supports PDF, images, and video processing via Gemini's multimodal capabilities.
"""

from __future__ import annotations

import base64
from typing import Dict


def prepare_file_content(file_data: bytes, mime_type: str) -> Dict[str, str]:
    """Prepare file content for inclusion in the prompt.

    Converts bytes into base64-encoded format expected by the AI provider.
    """
    b64 = base64.b64encode(file_data).decode("ascii")
    return {
        "type": "file",
        "data": b64,
        "mimeType": mime_type,
    }


def detect_mime_type(filename: str) -> str:
    """Detect MIME type from file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime_map = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
        "mp4": "video/mp4",
        "webm": "video/webm",
    }
    return mime_map.get(ext, "application/octet-stream")
