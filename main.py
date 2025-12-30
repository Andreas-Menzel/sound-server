"""
Text-to-Speech REST API using Piper TTS and PulseAudio.
Works on both macOS and Linux via PulseAudio TCP bridge.
"""

import os
import subprocess
import uuid
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Piper TTS Service",
    description="Text-to-Speech service using Piper with PulseAudio output",
    version="1.0.0",
)

# Configuration
AUDIO_DIR = Path("/app/audio")
MODELS_DIR = Path("/app/models")
DEFAULT_VOICE = "lessac"
PULSE_SERVER = os.environ.get("PULSE_SERVER", "tcp:host.docker.internal:4713")

# Voice catalog with metadata
VOICES = {
    # English voices
    "lessac": {
        "description": "US English, neutral",
        "language": "en",
        "gender": "neutral",
    },
    "amy": {
        "description": "US English, female",
        "language": "en",
        "gender": "female",
    },
    "joe": {
        "description": "US English, male",
        "language": "en",
        "gender": "male",
    },
    "alan": {
        "description": "British English, male",
        "language": "en",
        "gender": "male",
    },
    "alba": {
        "description": "Scottish English, female",
        "language": "en",
        "gender": "female",
    },
    # German voices
    "thorsten": {
        "description": "German, male",
        "language": "de",
        "gender": "male",
    },
    "karlsson": {
        "description": "German, male",
        "language": "de",
        "gender": "male",
    },
    "kerstin": {
        "description": "German, female",
        "language": "de",
        "gender": "female",
    },
}


class TTSResponse(BaseModel):
    """Response model for TTS operations."""

    success: bool
    message: str
    filename: Optional[str] = None


def get_model_path(voice_name: Optional[str] = None) -> Path:
    """Get the path to the voice model."""
    voice = voice_name or DEFAULT_VOICE
    model_path = MODELS_DIR / f"{voice}.onnx"
    if not model_path.exists():
        available = list(VOICES.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Voice '{voice}' not found. Available: {available}. See GET /voices",
        )
    return model_path


def run_piper(text: str, output_path: Path, model_path: Path) -> None:
    """Generate speech using Piper TTS."""
    try:
        cmd = [
            "piper",
            "--model",
            str(model_path),
            "--output_file",
            str(output_path),
        ]
        logger.info(f"Running Piper: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            input=text,
            text=True,
            capture_output=True,
            timeout=60,
        )

        if result.returncode != 0:
            logger.error(f"Piper stderr: {result.stderr}")
            raise HTTPException(
                status_code=500, detail=f"Piper TTS failed: {result.stderr}"
            )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="TTS generation timed out")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Piper executable not found")


def play_audio(file_path: Path) -> None:
    """Play audio file using paplay via PulseAudio TCP."""
    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Audio file not found: {file_path.name}"
        )

    env = os.environ.copy()
    env["PULSE_SERVER"] = PULSE_SERVER

    try:
        cmd = ["paplay", str(file_path)]
        logger.info(f"Playing audio: {' '.join(cmd)} (PULSE_SERVER={PULSE_SERVER})")

        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            logger.error(f"paplay stderr: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Audio playback failed: {result.stderr}. "
                f"Ensure PulseAudio TCP is running on host (PULSE_SERVER={PULSE_SERVER})",
            )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Audio playback timed out")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="paplay not found")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Piper TTS",
        "status": "running",
        "pulse_server": PULSE_SERVER,
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    # Check if piper is available
    try:
        result = subprocess.run(["piper", "--help"], capture_output=True, timeout=5)
        piper_ok = result.returncode == 0
    except Exception:
        piper_ok = False

    # Check if paplay is available
    try:
        result = subprocess.run(["paplay", "--version"], capture_output=True, timeout=5)
        paplay_ok = result.returncode == 0
    except Exception:
        paplay_ok = False

    # List installed voices
    installed_voices = (
        [f.stem for f in MODELS_DIR.glob("*.onnx")] if MODELS_DIR.exists() else []
    )

    return {
        "piper_available": piper_ok,
        "paplay_available": paplay_ok,
        "pulse_server": PULSE_SERVER,
        "voices": installed_voices,
        "default_voice": DEFAULT_VOICE,
        "audio_dir": str(AUDIO_DIR),
    }


@app.get("/voices")
async def list_voices(
    language: Optional[str] = Query(None, description="Filter by language (en, de)"),
):
    """List all available voices with metadata."""
    # Check which voices are actually installed
    installed = (
        {f.stem for f in MODELS_DIR.glob("*.onnx")} if MODELS_DIR.exists() else set()
    )

    voices = {}
    for name, meta in VOICES.items():
        # Filter by language if specified
        if language and meta["language"] != language:
            continue
        if name in installed:
            voices[name] = {**meta, "installed": True}
        else:
            voices[name] = {**meta, "installed": False}

    return {
        "voices": voices,
        "default": DEFAULT_VOICE,
    }


class SayRequest(BaseModel):
    """Request model for TTS say operation."""

    text: str
    voice: Optional[str] = None


@app.post("/say", response_model=TTSResponse)
async def say(request: SayRequest):
    """Generate speech from text and play it."""
    text = request.text
    voice = request.voice
    model_path = get_model_path(voice)

    # Temporary file for audio
    filename = f"tts_{uuid.uuid4().hex[:8]}.wav"
    output_path = AUDIO_DIR / filename

    logger.info(f"Generating TTS for: '{text[:50]}...' -> {output_path}")

    # Generate speech
    run_piper(text, output_path, model_path)

    # Play the audio
    play_audio(output_path)

    # Clean up temp file
    if output_path.exists():
        output_path.unlink()

    return TTSResponse(
        success=True,
        message="Speech generated and played successfully",
    )


@app.post("/play", response_model=TTSResponse)
async def play(
    filename: str = Query(..., description="Filename of the WAV file to play"),
):
    """
    Play an existing audio file from the mounted audio directory.
    """
    if not filename.endswith(".wav"):
        filename += ".wav"

    file_path = AUDIO_DIR / filename
    logger.info(f"Playing audio file: {file_path}")

    play_audio(file_path)

    return TTSResponse(
        success=True,
        message=f"Played audio file: {filename}",
        filename=filename,
    )


@app.get("/files")
async def list_files():
    """List all audio files in the mounted directory."""
    if not AUDIO_DIR.exists():
        return {"files": []}

    files = [f.name for f in AUDIO_DIR.glob("*.wav")]
    return {"files": sorted(files)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
