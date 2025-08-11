"""Klient API dla komunikacji z serwerem GAJA."""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import websockets
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


class ResponseBundle:
    """Odpowiedź z serwera GAJA."""
    
    def __init__(
        self,
        text: str = "",
        audio_path: Optional[str] = None,
        plugin_result: Optional[Dict[str, Any]] = None,
        side_effect: Optional[Dict[str, Any]] = None,
        raw_response: Optional[Dict[str, Any]] = None
    ):
        self.text = text
        self.audio_path = audio_path
        self.plugin_result = plugin_result
        self.side_effect = side_effect
        self.raw_response = raw_response or {}


class GajaApiClient:
    """Klient API dla serwera GAJA."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session_token: Optional[str] = None
        self.client = httpx.AsyncClient(timeout=60.0)
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Tworzy nagłówki HTTP z autoryzacją."""
        headers = {"Content-Type": "application/json"}
        
        if self.session_token:
            headers["Authorization"] = f"Bearer {self.session_token}"
        elif self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        return headers
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Wykonuje zapytanie HTTP z retry."""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await self.client.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = await self.client.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = await self.client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            
            # Sprawdź czy odpowiedź to JSON
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()
            else:
                return {"content": response.content, "headers": dict(response.headers)}
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error for {method} {url}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {method} {url}: {e}")
            raise
    
    async def authenticate(self, email: str = "test@example.com", password: str = "test123") -> bool:
        """Uwierzytelnia użytkownika i pobiera token sesji."""
        try:
            response = await self._make_request(
                "POST", 
                "/api/v1/auth/login",
                {"email": email, "password": password}
            )
            
            if response.get("success") and response.get("token"):
                self.session_token = response["token"]
                logger.info("✅ Authenticated successfully")
                return True
            else:
                logger.warning("❌ Authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def send_text(self, message: str) -> ResponseBundle:
        """Wysyła wiadomość tekstową do AI."""
        try:
            response = await self._make_request(
                "POST",
                "/api/v1/ai/query",
                {
                    "query": message,
                    "context": {}
                }
            )
            
            # Wyciągnij odpowiedź asystenta
            assistant_response = response.get("response", {})
            text = ""
            
            if isinstance(assistant_response, dict):
                text = assistant_response.get("text", str(assistant_response))
            else:
                text = str(assistant_response)
            
            return ResponseBundle(
                text=text,
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Send text error: {e}")
            raise
    
    async def send_audio(self, audio_path: str) -> ResponseBundle:
        """Wysyła plik audio do Whisper i przetwarza odpowiedź."""
        # TODO: Sprawdź czy GAJA ma endpoint dla upload audio + whisper
        # Na razie używamy TTS tylko dla wyjścia, nie ma endpointu dla Whisper input
        logger.warning("Audio input not implemented yet - GAJA may not have Whisper endpoint")
        
        # Symulacja - czytamy plik i próbujemy przetworzyć jako tekst
        try:
            # W przyszłości tutaj będzie upload audio + Whisper transcription
            # Na razie zwracamy placeholder
            return ResponseBundle(
                text="[Audio input not implemented]",
                audio_path=audio_path
            )
        except Exception as e:
            logger.error(f"Send audio error: {e}")
            raise
    
    async def get_tts_audio(self, text: str, voice: str = "alloy") -> Optional[str]:
        """Pobiera audio TTS dla tekstu."""
        try:
            response = await self._make_request(
                "POST",
                "/api/v1/tts/stream", 
                {
                    "text": text,
                    "voice": voice,
                    "model": "tts-1"
                }
            )
            
            # Sprawdź czy to streaming response z audio
            if "content" in response:
                # Zapisz audio do pliku
                artifacts_dir = Path("results/artifacts")
                artifacts_dir.mkdir(parents=True, exist_ok=True)
                
                import time
                timestamp = int(time.time())
                audio_file = artifacts_dir / f"tts_{timestamp}.opus"
                
                with open(audio_file, "wb") as f:
                    f.write(response["content"])
                
                logger.info(f"TTS audio saved to {audio_file}")
                return str(audio_file)
            
            return None
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise
    
    async def get_calendar_events(self, from_ts: int, to_ts: int) -> List[Dict[str, Any]]:
        """Pobiera wydarzenia z kalendarza."""
        try:
            # TODO: Check if GAJA has calendar integration endpoint
            response = await self._make_request(
                "GET",
                "/api/v1/plugins",  # Sprawdź dostępne pluginy
            )
            
            # Na razie placeholder
            return []
            
        except Exception as e:
            logger.error(f"Calendar events error: {e}")
            return []
    
    async def get_notes(self) -> List[Dict[str, Any]]:
        """Pobiera notatki."""
        try:
            # TODO: Check if GAJA has notes endpoint
            response = await self._make_request(
                "GET",
                "/api/v1/memory",  # Może być w pamięci
            )
            
            if isinstance(response, list):
                return response
            elif isinstance(response, dict) and "memories" in response:
                return response["memories"]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Get notes error: {e}")
            return []
    
    async def smart_home_list(self) -> List[Dict[str, Any]]:
        """Lista urządzeń smart home."""
        try:
            # TODO: Check if GAJA has smart home integration
            response = await self._make_request(
                "GET",
                "/api/v1/plugins",
            )
            
            # Na razie placeholder
            return []
            
        except Exception as e:
            logger.error(f"Smart home list error: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Sprawdza czy serwer działa."""
        try:
            response = await self._make_request("GET", "/health")
            return response.get("status") == "healthy"
        except Exception:
            return False
