"""Generator danych testowych dla scenariuszy GAJA."""

import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Any


class DataGenerator:
    """Generator danych testowych."""
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
    
    def generate_future_date(self, days_ahead: int = 1) -> datetime:
        """Generuje datę w przyszłości."""
        base_date = datetime.now() + timedelta(days=days_ahead)
        # Dodaj losowy offset (0-23 godziny)
        offset_hours = random.randint(0, 23)
        return base_date.replace(hour=offset_hours, minute=0, second=0, microsecond=0)
    
    def generate_unique_event_name(self) -> str:
        """Generuje unikalną nazwę wydarzenia."""
        adjectives = [
            "Ważne", "Pilne", "Regularne", "Cotygodniowe", 
            "Projektowe", "Strategiczne", "Operacyjne", "Biznesowe"
        ]
        nouns = [
            "Spotkanie", "Zebranie", "Konferencja", "Warsztat", 
            "Prezentacja", "Review", "Planning", "Retrospektywa"
        ]
        
        adjective = random.choice(adjectives)
        noun = random.choice(nouns)
        
        # Dodaj unikalny suffix
        timestamp = int(datetime.now().timestamp())
        suffix = str(timestamp)[-4:]  # Ostatnie 4 cyfry timestamp
        
        return f"{adjective} {noun} #{suffix}"
    
    def generate_habit_description(self) -> str:
        """Generuje opis nawyku."""
        actions = [
            "pij wodę", "zrób przerwę", "sprawdź pocztę", 
            "wykonaj ćwiczenia", "przeczytaj artykuł", "zrób notatkę",
            "sprawdź kalendarz", "uporządkuj biurko"
        ]
        
        frequencies = [
            "co godzinę", "co 2 godziny", "co 3 godziny",
            "co 30 minut", "raz dziennie", "dwa razy dziennie"
        ]
        
        action = random.choice(actions)
        frequency = random.choice(frequencies)
        
        return f"{action} {frequency}"
    
    def generate_short_query(self) -> str:
        """Generuje krótkie zapytanie."""
        queries = [
            "Jaka jest pogoda?",
            "Co mam dzisiaj w kalendarzu?",
            "Przypomnij mi o spotkaniu",
            "Dodaj notatkę o projekcie",
            "Jak się masz?",
            "Co nowego?",
            "Sprawdź moje nawyki",
            "Pokaż ostatnie notatki"
        ]
        
        return random.choice(queries)
    
    def generate_long_prompt(self) -> str:
        """Generuje długi, realistyczny prompt."""
        contexts = [
            "Jestem programistą pracującym zdalnie",
            "Prowadzę małą firmę consultingową", 
            "Studiuję informatykę i pracuję na pół etatu",
            "Jestem freelancerem zajmującym się designem"
        ]
        
        tasks = [
            "przygotować prezentację na jutrzejsze spotkanie z klientem",
            "skończyć projekt, który mam deadline w przyszłym tygodniu", 
            "zorganizować swój harmonogram na najbliższe dni",
            "przeanalizować wyniki ostatniego tygodnia i zaplanować kolejny"
        ]
        
        context = random.choice(contexts)
        task = random.choice(tasks)
        
        return f"{context}. Potrzebuję pomocy w {task}. Czy możesz mi pomóc zaplanować to krok po kroku i dodać odpowiednie przypomnienia?"
    
    def generate_calendar_event_data(self) -> Dict[str, Any]:
        """Generuje dane wydarzenia kalendarzowego."""
        future_date = self.generate_future_date(random.randint(1, 7))
        event_name = self.generate_unique_event_name()
        
        return {
            "title": event_name,
            "date": future_date.isoformat(),
            "duration": random.choice([30, 60, 90, 120]),  # minutes
            "description": f"Auto-generated event: {event_name}"
        }
    
    def generate_note_content(self) -> str:
        """Generuje treść notatki."""
        topics = [
            "Pomysł na nowy feature w aplikacji",
            "Notatka ze spotkania z zespołem",
            "Lista rzeczy do zrobienia w projekcie",
            "Refleksje po zakończeniu sprintu",
            "Plan rozwoju osobistego na kolejny kwartał"
        ]
        
        details = [
            "Należy przemyśleć architekturę i zidentyfikować potencjalne problemy.",
            "Kluczowe decyzje zostały podjęte, ale wymaga to dalszej analizy.",
            "Priorytety muszą być ustalone zgodnie z biznesowymi potrzebami.",
            "Feedback od użytkowników pokazuje obszary do poprawy.",
            "Cele są ambitne ale osiągalne przy odpowiednim zaangażowaniu."
        ]
        
        topic = random.choice(topics)
        detail = random.choice(details)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        return f"[{timestamp}] {topic}\n\n{detail}"
    
    def generate_smart_home_device(self) -> Dict[str, Any]:
        """Generuje dane urządzenia smart home."""
        device_types = [
            {"type": "light", "name": "Żarówka", "room": "salon"},
            {"type": "thermostat", "name": "Termostat", "room": "korytarz"},
            {"type": "sensor", "name": "Czujnik", "room": "sypialnia"},
            {"type": "camera", "name": "Kamera", "room": "wejście"},
            {"type": "speaker", "name": "Głośnik", "room": "kuchnia"}
        ]
        
        device = random.choice(device_types)
        device_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        return {
            "id": device_id,
            "name": f"{device['name']} {device['room']}",
            "type": device["type"],
            "room": device["room"],
            "status": random.choice(["online", "offline"]),
            "value": random.randint(0, 100) if device["type"] != "camera" else None
        }
    
    def generate_test_credentials(self) -> Dict[str, str]:
        """Generuje dane testowe do logowania."""
        return {
            "email": "test.user@gaja.test",
            "password": "TestPass123!"
        }
