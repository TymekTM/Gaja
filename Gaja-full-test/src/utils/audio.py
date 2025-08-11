"""Moduł obsługi audio dla testów GAJA."""

import asyncio
import io
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import httpx
from loguru import logger

# Próbujemy zaimportować pydub, ale obsługujemy brak modułu audioop
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"pydub import failed: {e}. Audio processing will be limited.")
    PYDUB_AVAILABLE = False
    AudioSegment = None

try:
    import soundfile as sf
    import numpy as np
    SOUNDFILE_AVAILABLE = True
except ImportError:
    logger.warning("soundfile not available. Some audio features will be limited.")
    SOUNDFILE_AVAILABLE = False

__all__ = ['AudioProcessor']


class AudioProcessor:
    """Procesor audio dla testów."""
    
    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = temp_dir or Path(tempfile.gettempdir()) / "gaja_test_audio"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Sprawdź dostępność FFmpeg
        self.ffmpeg_available = self._check_ffmpeg()
        if not self.ffmpeg_available:
            logger.warning("FFmpeg not available. Audio conversion will be limited.")
    
    def _check_ffmpeg(self) -> bool:
        """Sprawdza dostępność FFmpeg."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    async def generate_tts_audio(
        self, 
        text: str, 
        api_key: Optional[str] = None,
        voice: str = "alloy",
        model: str = "tts-1"
    ) -> Optional[bytes]:
        """Generuje audio przez OpenAI TTS API."""
        if not api_key or api_key == "your_openai_api_key_here":
            logger.warning("No valid OpenAI API key. Returning mock audio data.")
            return self._generate_mock_audio(text)
        
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "input": text,
                "voice": voice,
                "response_format": "opus"
            }
            
            timeout = httpx.Timeout(60.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.success(f"Generated TTS audio for text: '{text[:50]}...'")
                    return response.content
                else:
                    logger.error(f"TTS API error {response.status_code}: {response.text}")
                    return self._generate_mock_audio(text)
                    
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return self._generate_mock_audio(text)
    
    def _generate_mock_audio(self, text: str) -> bytes:
        """Generuje mock dane audio."""
        # Symulujemy opus audio data
        duration_ms = max(len(text) * 50, 1000)  # min 1s
        mock_size = duration_ms * 64  # ~64 bytes per ms for opus
        
        # Generujemy pseudo-losowe dane (ale deterministyczne dla testów)
        import random
        random.seed(hash(text) % 2**32)
        mock_data = bytes([random.randint(0, 255) for _ in range(mock_size)])
        
        logger.info(f"Generated mock audio: {len(mock_data)} bytes for '{text[:30]}...'")
        return mock_data
    
    async def convert_opus_to_wav(self, opus_data: bytes) -> Optional[bytes]:
        """Konwertuje opus do WAV używając FFmpeg."""
        if not self.ffmpeg_available:
            logger.warning("FFmpeg not available. Returning original data.")
            return opus_data
        
        try:
            # Zapisz opus do tymczasowego pliku
            opus_path = self.temp_dir / f"temp_{id(opus_data)}.opus"
            wav_path = self.temp_dir / f"temp_{id(opus_data)}.wav"
            
            with open(opus_path, 'wb') as f:
                f.write(opus_data)
            
            # Konwertuj używając FFmpeg
            cmd = [
                "ffmpeg", "-y", "-i", str(opus_path),
                "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
                str(wav_path)
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and wav_path.exists():
                with open(wav_path, 'rb') as f:
                    wav_data = f.read()
                
                # Posprzątaj pliki tymczasowe
                opus_path.unlink(missing_ok=True)
                wav_path.unlink(missing_ok=True)
                
                logger.success(f"Converted {len(opus_data)} bytes opus to {len(wav_data)} bytes wav")
                return wav_data
            else:
                logger.error(f"FFmpeg conversion failed: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Audio conversion error: {e}")
            return None
    
    def analyze_audio_properties(self, audio_data: bytes, format_hint: str = "wav") -> Dict[str, Any]:
        """Analizuje właściwości audio."""
        if not audio_data:
            return {"error": "No audio data"}
        
        properties = {
            "size_bytes": len(audio_data),
            "format_hint": format_hint,
            "analysis_method": "basic"
        }
        
        # Jeśli mamy soundfile, spróbuj analizy
        if SOUNDFILE_AVAILABLE and format_hint == "wav":
            try:
                with io.BytesIO(audio_data) as buffer:
                    data, samplerate = sf.read(buffer)
                    properties.update({
                        "sample_rate": samplerate,
                        "channels": data.ndim if data.ndim > 1 else 1,
                        "duration_seconds": len(data) / samplerate,
                        "samples": len(data),
                        "analysis_method": "soundfile"
                    })
            except Exception as e:
                logger.debug(f"Soundfile analysis failed: {e}")
        
        # Podstawowa analiza na podstawie rozmiaru
        if "duration_seconds" not in properties:
            # Szacowanie dla różnych formatów
            if format_hint == "opus":
                # Opus: ~64kbps = 8000 bytes/s
                properties["duration_estimate"] = len(audio_data) / 8000
            elif format_hint == "wav":
                # WAV 16kHz mono 16-bit: 32000 bytes/s
                properties["duration_estimate"] = len(audio_data) / 32000
            else:
                properties["duration_estimate"] = len(audio_data) / 16000
        
        return properties
    
    def cleanup_temp_files(self):
        """Czyści pliki tymczasowe."""
        try:
            for file_path in self.temp_dir.glob("temp_*"):
                file_path.unlink(missing_ok=True)
            logger.debug(f"Cleaned up temp files in {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
    
    def validate_audio_quality(self, audio_data: bytes, expected_duration: Optional[float] = None) -> Dict[str, Any]:
        """Waliduje jakość audio."""
        if not audio_data:
            return {"valid": False, "reason": "No audio data"}
        
        properties = self.analyze_audio_properties(audio_data)
        
        validation = {
            "valid": True,
            "size_ok": len(audio_data) > 1000,  # Minimum 1KB
            "properties": properties
        }
        
        # Sprawdź czas trwania jeśli podano
        if expected_duration:
            duration = properties.get("duration_seconds") or properties.get("duration_estimate", 0)
            duration_diff = abs(duration - expected_duration)
            validation["duration_ok"] = duration_diff < (expected_duration * 0.5)  # ±50%
            validation["duration_difference"] = duration_diff
        
        # Ogólna ocena
        validation["valid"] = (
            validation["size_ok"] and
            validation.get("duration_ok", True)
        )
        
        return validation
