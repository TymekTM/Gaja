# Gaja

**Gaja** is an offline-first, self-hosted voice assistant built for people who care about control, speed, and privacy.
It runs fully locally, without requiring cloud services or API keys, and is designed to be extended through modular plugins.

> This repository is the **main distribution hub** for Gaja releases. Core logic and functionality live in separate submodules:
> [Gaja-Server](https://github.com/TymekTM/Gaja-Server), [Gaja-Client](https://github.com/TymekTM/Gaja-Client), and [Gaja-Web](https://github.com/TymekTM/Gaja-Web).


## What Makes Gaja Different?

Unlike most voice assistants, **Gaja does not rely on the cloud**. Everything happens on your device. No telemetry, no user accounts, no external dependencies unless explicitly enabled.

* **Modular:** Each component (STT, TTS, memory, plugins, UI) is independently manageable and replaceable.
* **Offline-first:** Gaja is usable out of the box without internet access.
* **Lightweight:** Quick to start, low on resources.
* **Extensible:** Add new functionality by dropping a Python file into the plugin folder.
* **Cross-platform:** Works on Windows, Linux support under development.


## Core Features

### Modular Architecture

* Hot-reloadable plugin system
* Clear separation between client, server, and optional web UI
* Communication via local HTTP and WebSocket

### Voice Interaction

* Whisper-based **local** speech recognition
* Wake word detection


### Memory Engine

* Built-in SQLite database
* Shared knowledge accessible by plugins

### Text-to-Speech

* Integration with OpenAI TTS, ElevenLabs, and more
* Configurable output voice per user or plugin

### Automation Friendly

* Interact with smart home systems, file system, calendars, etc.
* Customisability with custom plugins


## Development Roadmap

The following roadmap outlines ongoing and planned development:

### 🟡 In Progress

* GUI for setup and voice interaction (Gaja-Client)

* Secure plugin sandboxing

* Rework of Overlay component 

### 🔜 Planned

* Auto-update mechanism for core system and plugins

* Visual plugin store with one-click installs

* Per-user setings profiles

* Custom TTS using CSM

* Context-based plugin prioritization (plugin weighting)

You can contribute ideas and vote on roadmap priorities in the [Discussion section](https://github.com/TymekTM/Gaja/discussions)[.](https://github.com/TymekTM/Gaja/discussions)


## Installation

### Windows (Quickstart)

1. Go to [Releases](https://github.com/TymekTM/Gaja/releases)
2. Download the latest `Gaja-x.x.x.zip`
3. Run `install_gaja.bat`
4. Choose your install path
5. Let the script install Python (if missing) and extract everything

> Linux installation available via Docker in [Gaja-Server README](https://github.com/TymekTM/Gaja-Server)


## System Overview

Gaja is split into three main components:

| Component   | Purpose                                            |
| ----------- | -------------------------------------------------- |
| Gaja-Server | Manages plugins, memory, logic, and API endpoints  |
| Gaja-Client | Handles audio input/output and basic GUI           |
| Gaja-Web    | (Optional) Browser-based interface for interaction |

All communication happens locally. Each component is independent and replaceable.


## Related Repositories

* [Gaja-Server](https://github.com/TymekTM/Gaja-Server)
* [Gaja-Client](https://github.com/TymekTM/Gaja-Client)
* [Gaja-Web](https://github.com/TymekTM/Gaja-Web)


## Existing Plugins

* `calendar_plugin`: Google Calendar integration
* `weather_plugin`: Weather forecast via API
* `system_plugin`: Shell command execution
* `joke_plugin`: Random joke generator
* `tts_switcher`: Runtime TTS source switching
* `chat_plugin`: LLM-powered general conversation

You can build your own plugins by dropping `.py` files into the `/modules` folder. Examples are available in [Gaja-Server](https://github.com/TymekTM/Gaja-Server/tree/main/modules)[.](https://github.com/TymekTM/Gaja-Server/tree/main/modules)


## Philosophy

Gaja exists to prove that modern AI-powered assistants don’t need to be invasive or cloud-bound.
We believe tools that talk to you should also be understandable by you — in both code and behavior.

Our core values:

* **Privacy by default**
* **Full user control**
* **Accessible architecture for hobbyists and power users alike**

## License

Gaja is licensed under the **Mozilla Public License Version 2.0**. See [LICENSE](./LICENSE) for details.
