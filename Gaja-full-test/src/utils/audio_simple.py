"""Uproszczony moduł audio dla testów GAJA."""

import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

import httpx
from loguru import logger

class AudioProcessor:
    """Uproszczony procesor audio."""
    
    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = temp_dir or Path(tempfile.gettempdir()) / "gaja_test_audio"
        self.temp_dir.mkdir(exist_ok=True)
    
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
        duration_ms = max(len(text) * 50, 1000)  # min 1s
        mock_size = duration_ms * 64  # ~64 bytes per ms for opus
        
        import random
        random.seed(hash(text) % 2**32)
        mock_data = bytes([random.randint(0, 255) for _ in range(mock_size)])
        
        logger.info(f"Generated mock audio: {len(mock_data)} bytes for '{text[:30]}...'")
        return mock_data
    
    async def convert_opus_to_wav(self, opus_data: bytes) -> Optional[bytes]:
        """Konwertuje opus do WAV - uproszczona wersja."""
        logger.info("Using simplified audio conversion (returning original data)")
        return opus_data
    
    def analyze_audio_properties(self, audio_data: bytes, format_hint: str = "wav") -> Dict[str, Any]:
        """Analizuje właściwości audio - uproszczona wersja."""
        if not audio_data:
            return {"error": "No audio data"}
        
        properties = {
            "size_bytes": len(audio_data),
            "format_hint": format_hint,
            "analysis_method": "simplified"
        }
        
        # Podstawowa analiza na podstawie rozmiaru
        if format_hint == "opus":
            properties["duration_estimate"] = len(audio_data) / 8000
        elif format_hint == "wav":
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
            "size_ok": len(audio_data) > 1000,
            "properties": properties
        }
        
        if expected_duration:
            duration = properties.get("duration_estimate", 0)
            duration_diff = abs(duration - expected_duration)
            validation["duration_ok"] = duration_diff < (expected_duration * 0.5)
            validation["duration_difference"] = duration_diff
        
        validation["valid"] = (
            validation["size_ok"] and
            validation.get("duration_ok", True)
        )
        
        return validation
