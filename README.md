# Gaja

🎙️ **Gaja** is a fully offline, local-first voice assistant powered by lightweight Python modules.  
Designed for privacy, extensibility and speed – no cloud, no data leaks, just you and your assistant.

## 🚀 Features

- 🔌 Modular architecture with plugin auto-reload
- 🎤 Voice activation + speech-to-text
- 🧠 Built-in intent recognition
- 💡 Smart memory system using SQLite
- 🖥️ Cross-platform (Windows optimized; Linux support planned)
- 📡 No API keys required
- 🚅 Ability to outsource AI compute to OpenAI, Deepseek, Anthropic

## 📦 Installation

Download the latest version from [Releases](https://github.com/TymekTM/Gaja/releases).

1. Run the `install_gaja.bat` installer script (included in this repo).
2. Choose an installation folder.
3. The script will:
   - Check for Python and install it if needed
   - Download `Gaja-1.1.0.zip`, `resources.zip`, and `modules.zip`
   - Extract and launch Gaja

✅ You’re ready to go.

## 🧩 How to add plugins

Drop new plugin modules into the `modules/` folder.  
Dev documentation is build into Gaja.
