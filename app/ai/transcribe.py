"""Voice -> text.

Default: faster-whisper running locally (free, offline; downloads the model
once on first use). Optional: OpenAI Whisper API when ai_provider=openai.
The CPU-bound local model runs in a thread so it never blocks the event loop.
"""
from __future__ import annotations

import asyncio
import os
import tempfile

from app.config import settings

_model = None  # lazy faster-whisper singleton


def _get_local_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        # int8 keeps it fast and light on CPU.
        _model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
    return _model


def _local_sync(audio: bytes) -> str:
    model = _get_local_model()
    # Write to a temp file — most reliable decode path across formats (ogg/opus).
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(audio)
        path = f.name
    try:
        segments, _info = model.transcribe(
            path,
            language=settings.whisper_language or None,
            beam_size=5,
        )
        return " ".join(seg.text for seg in segments).strip()
    finally:
        os.unlink(path)


async def _transcribe_local(audio: bytes) -> str:
    return await asyncio.to_thread(_local_sync, audio)


async def _transcribe_groq(audio: bytes, filename: str) -> str:
    """FREE Whisper large-v3 via Groq's OpenAI-compatible API."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
    )
    result = await client.audio.transcriptions.create(
        model=settings.groq_transcribe_model,
        file=(filename, audio),
        language=settings.whisper_language or None,
    )
    return (result.text or "").strip()


async def _transcribe_openai(audio: bytes, filename: str) -> str:
    from app.ai.client import get_client

    client = get_client()
    result = await client.audio.transcriptions.create(
        model=settings.openai_transcribe_model,
        file=(filename, audio),
    )
    return (result.text or "").strip()


async def transcribe(audio: bytes, filename: str = "voice.ogg") -> str:
    # Priority: Groq (free, best) -> OpenAI (paid) -> local faster-whisper.
    if settings.groq_api_key:
        return await _transcribe_groq(audio, filename)
    if settings.ai_provider == "openai" and settings.openai_api_key:
        return await _transcribe_openai(audio, filename)
    return await _transcribe_local(audio)
