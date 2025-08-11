# GAJA Full Test - End-to-End Testing Framework

Kompletny system testów end-to-end dla asystenta GAJA, który wykonuje realne testy przez API, generuje audio przez TTS, ocenia odpowiedzi przez lokalną instancję LLM i tworzy szczegółowe raporty HTML.

## 🎯 Funkcje

- **Realne testy API** - zero mocków, tylko prawdziwe wywołania REST/WebSocket
- **Audio processing** - generowanie TTS przez OpenAI, planowana obsługa Whisper
- **Inteligentna ocena** - lokalna instancja LM Studio ocenia jakość odpowiedzi
- **Akcje systemowe** - restart serwera, zarządzanie cache, backup danych
- **Interaktywny raport HTML** - automatycznie otwierany w przeglądarce

## 📋 Wymagania

### System
- Python 3.11+
- FFmpeg (wymagane przez pydub)
- LM Studio z modelem gpt-oss-20b (opcjonalnie dla oceny semantycznej)

### Serwisy
- GAJA Server działający na `http://localhost:8001`
- LM Studio na `http://localhost:1234` (opcjonalnie)

## 🚀 Instalacja

1. **Sklonuj/przejdź do folderu:**
   ```bash
   cd Gaja-full-test
   ```

2. **Utwórz środowisko wirtualne:**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Zainstaluj zależności:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Skonfiguruj zmienne środowiskowe:**
   ```bash
   cp .env.example .env
   ```
   
   Wypełnij `.env`:
   ```env
   GAJA_API_KEY=your_gaja_api_key_if_needed
   OPENAI_API_KEY=your_openai_api_key_for_tts
   ```

5. **Sprawdź FFmpeg:**
   ```bash
   ffmpeg -version
   ```

## ⚙️ Konfiguracja

Edytuj `config.yaml` aby dostosować ustawienia:

```yaml
gaja:
  base_url: "http://localhost:8001"    # URL serwera GAJA
  api_key: "${GAJA_API_KEY}"           # Klucz API (jeśli wymagany)

voice:
  tts_provider: "openai"
  tts_model: "tts-1"                   # Model OpenAI TTS
  tts_voice: "alloy"                   # Głos (alloy, echo, fable, onyx, nova, shimmer)
  sample_rate: 16000
  output_format: "wav"

grader:
  lmstudio_base_url: "http://localhost:1234/v1/chat/completions"
  model: "gpt-oss-20b"                 # Model w LM Studio
  max_tokens: 512
  temperature: 0.1

report:
  output_path: "results/report.html"
  fail_threshold: 8.0                  # Próg oceny (0-10)

runtime:
  seed: 42
  default_timeout_s: 45
  between_steps_sleep_ms: 300
  allow_parallel: false
```

## 🎮 Uruchomienie

### Pojedynczy scenariusz
```bash
python src/runner.py --scenario scenarios/conversation_basic.yaml
```

### Wszystkie scenariusze
```bash
python src/runner.py --all
```

### Niestandardowa konfiguracja
```bash
python src/runner.py --all --config custom_config.yaml
```

## 📝 Scenariusze testowe

Scenariusze są zdefiniowane w plikach YAML w folderze `scenarios/`:

### Dostępne scenariusze:
- `conversation_basic.yaml` - Podstawowa konwersacja
- `habits_learning.yaml` - Dodawanie i przypominanie nawyków
- `tts_roundtrip.yaml` - Test pełnej pętli audio (TTS → GAJA → odpowiedź)
- `whisper_input.yaml` - Przetwarzanie wejścia audio
- `calendar_integration.yaml` - Integracja z kalendarzem
- `notes_plugin.yaml` - Funkcjonalność notatek
- `web_search.yaml` - Wyszukiwanie w internecie
- `iot_smart_home.yaml` - Kontrola urządzeń IoT
- `longform_generation.yaml` - Generowanie długich treści

### Struktura scenariusza:

```yaml
meta:
  name: "Test Name"
  tags: ["tag1", "tag2"]

steps:
  - type: "text"                    # text|audio|action
    message: "Cześć! Jak się masz?"
    expect:
      action: "greeting_response"
      assertions:
        - kind: "contains"          # contains|semantic_ok|effect_ok|jsonpath_eq
          target: "assistant_text"  # assistant_text|plugin_result|side_effect
          value: "cześć"
        - kind: "semantic_ok"

  - type: "audio"
    tts_text: "Wygeneruj audio z tego tekstu"
    expect:
      action: "transcribe_and_answer"
      assertions:
        - kind: "semantic_ok"

  - type: "action"
    action: "restart_gaja"          # restart_gaja|clear_cache|backup_data
    expect:
      action: "service_restarted"
      assertions:
        - kind: "effect_ok"
```

## 📊 Interpretacja wyników

### Raport HTML
Po uruchomieniu testów automatycznie otwiera się raport HTML zawierający:

- **Statystyki ogólne** - liczba scenariuszy, kroków, wskaźnik sukcesu
- **Wykresy wizualne** - słupkowe i kołowe przedstawienie wyników
- **Szczegółowe wyniki** - tabela z wynikami każdego scenariusza
- **Nieudane testy** - lista błędów z detalami
- **Konfiguracja** - ustawienia użyte podczas testów

### Progi oceny
- **semantic_ok**: ocena LM Studio ≥ 8.0/10 (konfigurowalny próg)
- **effect_ok**: sprawdzenie czy akcja systemowa się powiodła
- **contains**: czy tekst zawiera oczekiwaną frazę

### Pliki wynikowe
```
results/
├── report.html              # Główny raport
├── logs/
│   ├── test_run_*.jsonl     # Logi wykonania (JSON Lines)
│   └── grades_*.json        # Oceny z LM Studio
└── artifacts/
    ├── tts_input_*.wav      # Pliki audio wejściowe (TTS)
    └── tts_output_*.opus    # Pliki audio wyjściowe (GAJA)
```

## 🔧 Rozwiązywanie problemów

### FFmpeg nie znaleziony
```bash
# Windows (przez chocolatey)
choco install ffmpeg

# Windows (ręcznie)
# Pobierz z https://ffmpeg.org/download.html i dodaj do PATH

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS (przez Homebrew)
brew install ffmpeg
```

### GAJA Server niedostępny
```bash
# Sprawdź status
curl http://localhost:8001/health

# Restart Docker
cd ../Gaja-server
docker compose restart
```

### LM Studio niedostępny
- Uruchom LM Studio
- Załaduj model gpt-oss-20b (lub inny zgodny)
- Sprawdź czy server endpoint jest aktywny na porcie 1234
- Ocena semantyczna będzie pominięta jeśli LM Studio niedostępny

### Błędy TTS
- Sprawdź klucz `OPENAI_API_KEY` w `.env`
- Sprawdź limit API OpenAI
- Sprawdź połączenie internetowe

### Błędy autoryzacji GAJA
- Sprawdź czy `GAJA_API_KEY` jest ustawiony (jeśli wymagany)
- Sprawdź endpoint autoryzacji w `api/routes.py`

## 🔍 Przykład uruchomienia

```bash
# Terminal 1: Uruchom serwisy
cd ../Gaja-server && docker compose up -d
cd ../Gaja-Web && docker compose up -d

# Terminal 2: Uruchom LM Studio (opcjonalnie)
# Uruchom aplikację LM Studio i załaduj model

# Terminal 3: Uruchom testy
cd Gaja-full-test
python src/runner.py --all
```

Oczekiwany wynik:
```
2025-08-09 13:30:00 | INFO | ✅ Configuration loaded and validated
2025-08-09 13:30:01 | INFO | ✅ FFmpeg available
2025-08-09 13:30:01 | INFO | ✅ All components initialized
2025-08-09 13:30:02 | INFO | ✅ GAJA Server is healthy
2025-08-09 13:30:03 | INFO | ✅ LM Studio is available
2025-08-09 13:30:04 | INFO | ✅ Authenticated successfully
2025-08-09 13:30:05 | INFO | ✅ Loaded scenario: Basic Conversation
...
2025-08-09 13:35:30 | INFO | 📖 Report generated and opened: results/report.html
2025-08-09 13:35:30 | INFO | 🎉 Testing completed: 8/9 scenarios passed
```

## 📚 Dokumentacja API

System wykorzystuje następujące endpointy GAJA:

- `GET /health` - sprawdzenie stanu serwera
- `POST /api/v1/auth/login` - uwierzytelnienie
- `POST /api/v1/ai/query` - główny endpoint konwersacji
- `POST /api/v1/tts/stream` - generowanie TTS
- `GET /api/v1/memory` - pobieranie notatek/pamięci
- `GET /api/v1/plugins` - lista dostępnych pluginów

## 🤝 Wkład w projekt

Aby dodać nowy scenariusz:

1. Utwórz plik YAML w `scenarios/`
2. Zdefiniuj metadane i kroki zgodnie ze schematem
3. Przetestuj pojedynczy scenariusz przed dodaniem do suite
4. Udokumentuj specjalne wymagania (pluginy, konfiguracja)

## 📄 Licencja

Zgodna z licencją głównego projektu GAJA.
