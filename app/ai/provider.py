from typing import Protocol


class VisionProvider(Protocol):
    """Provider-agnostic vision/text interface for persona agents."""

    async def analyze_image(self, image_bytes: bytes, prompt: str) -> str: ...

    async def analyze_text(self, prompt: str) -> str: ...
