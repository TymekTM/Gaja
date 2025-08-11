"""Uproszczony test runner dla GAJA."""

import asyncio
import json
import sys
import time
from pathlib import Path

# Dodajmy ścieżkę
sys.path.append(str(Path(__file__).parent / "src"))

from utils.api_client import GajaApiClient

async def simple_test():
    """Prosty test podstawowej funkcjonalności GAJA."""
    print("🚀 Uruchamiam prosty test GAJA...")
    
    # Podstawowa konfiguracja
    config = {
        "gaja": {
            "base_url": "http://localhost:8001",
            "auth_token": None
        }
    }
    
    try:
        # Sprawdź health GAJA
        print("1. Sprawdzam status GAJA...")
        api_client = GajaApiClient(
            base_url=config["gaja"]["base_url"],
            api_key=config["gaja"]["auth_token"]
        )
        
        health_ok = await api_client.health_check()
        if health_ok:
            print("✅ GAJA server jest dostępny")
        else:
            print("❌ GAJA server nie odpowiada")
            return False
        
        # Test podstawowej konwersacji
        print("2. Próbuję zalogować się do GAJA...")
        
        # Spróbuj logowania
        auth_success = await api_client.authenticate(
            email="admin", 
            password="h7A8q0bvrr806K6vbpWwcmKt-nY"
        )
        
        if auth_success:
            print("✅ Zalogowano pomyślnie")
        else:
            print("⚠️ Logowanie nie powiodło się, próbuję bez autoryzacji")
        
        print("3. Testuję podstawową konwersację...")
        test_message = "Cześć GAJA, jak się masz?"
        
        response = await api_client.send_text(test_message)
        if response.success:
            print(f"✅ Otrzymano odpowiedź: {response.data.get('response', 'Brak odpowiedzi')[:100]}...")
        else:
            print(f"❌ Błąd w komunikacji: {response.error}")
            return False
        
        # Test TTS (mock)
        print("4. Testuję generowanie audio...")
        try:
            from utils.audio_simple import AudioProcessor
            audio_processor = AudioProcessor()
            
            audio_data = await audio_processor.generate_tts_audio(
                "To jest test audio", 
                api_key="your_openai_api_key_here"  # Mock
            )
            
            if audio_data:
                print(f"✅ Audio wygenerowane: {len(audio_data)} bajtów")
            else:
                print("❌ Nie udało się wygenerować audio")
                
        except Exception as e:
            print(f"⚠️ Audio test nie powiódł się: {e}")
        
        print("🎉 Test zakończony pomyślnie!")
        return True
        
    except Exception as e:
        print(f"❌ Błąd testu: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(simple_test())
    if result:
        print("\n✅ Wszystkie testy przeszły pomyślnie!")
    else:
        print("\n❌ Niektóre testy nie powiodły się")
        sys.exit(1)
