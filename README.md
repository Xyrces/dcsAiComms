# DCS Natural Language ATC

A **plug-and-play Natural Language ATC system for DCS World** that allows players to use natural speech for realistic military aviation communications powered by **Ollama** for local AI processing.

## Features

- 🎙️ **Natural Language Voice Control** - Speak naturally to ATC using military phraseology
- 🤖 **Local AI Processing** - Uses Ollama with Llama 3.2 3B (no API costs, complete privacy)
- 🔧 **Automatic Setup** - Auto-detects DCS installation and configures everything
- 🛡️ **Safe Integration** - Always creates backups before modifying DCS files
- 🎯 **Military Phraseology** - Authentic US military radio procedures (ATP 1-02.1, FAA AIM)
- 🎮 **Zero DCS Configuration** - No manual file editing required
- 📡 **SRS Ready** - Integration with DCS-SimpleRadioStandalone for radio responses

## Quick Start

### Prerequisites

1. **DCS World** (any version)
2. **Ollama** - Install from [ollama.com](https://ollama.com/download)
3. **Python 3.11+**

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/dcsAiComms.git
cd dcsAiComms

# Install dependencies
pip install -r requirements.txt

# Configure DCS integration
python atc_main.py --configure

# Setup and test Ollama
python atc_main.py --setup-ollama
```

### Testing

```bash
# Run tests
pytest

# Test NLP processing
python atc_main.py --test-nlp

# Interactive testing
python atc_main.py --interactive
```

### Usage

```bash
# Configure DCS (detects installation automatically)
python atc_main.py --configure

# Specify custom DCS path
python atc_main.py --configure --dcs-path "/path/to/DCS"

# Test the system
python atc_main.py --test-nlp

# Interactive session for testing
python atc_main.py --interactive

# Remove DCS integration
python atc_main.py --unconfigure
```

## Architecture

```
Player Voice (PTT)
    ↓
[Python Application]
    ├─ STT: Whisper (local) or Fireworks AI
    ├─ NLP: Ollama (Llama 3.2 3B)
    ├─ TTS: Piper TTS (local)
    └─ DCS Integration: Export.lua + Mission Scripts
        ↓
[DCS World + SRS Radio]
    ↓
Radio Response in Cockpit
```

## Project Structure

```
dcs-nl-atc/
├── atc_main.py              # Main application entry
├── requirements.txt         # Python dependencies
├── pytest.ini              # Test configuration
├── README.md
│
├── config/
│   ├── settings.yaml       # Configuration
│   └── phraseology.yaml    # ATC phrase templates
│
├── src/
│   ├── ollama_manager.py   # Ollama process management
│   ├── dcs_configurator.py # DCS auto-configuration
│   ├── nlp_processor.py    # Command parsing & response generation
│   ├── voice_input.py      # PTT and audio capture (TODO)
│   ├── stt_engine.py       # Speech-to-text (TODO)
│   ├── tts_engine.py       # Text-to-speech (TODO)
│   ├── dcs_bridge.py       # Export.lua data listener (TODO)
│   ├── atc_controller.py   # ATC logic engine (TODO)
│   └── srs_client.py       # SRS integration (TODO)
│
├── lua/
│   ├── export_template.lua # Export.lua injection code
│   └── mission_script.lua  # Mission ATC script
│
├── templates/
│   └── mission_atc.lua     # Installable mission script
│
└── tests/
    ├── test_ollama_manager.py
    ├── test_dcs_configurator.py
    └── test_nlp_processor.py
```

## Development Status

### ✅ Completed (TDD Implementation)
- [x] Project structure
- [x] Testing framework (pytest)
- [x] OllamaManager with auto-launch
- [x] DCS path detection and configuration
- [x] Export.lua safe injection with backups
- [x] NLP processor with intent classification
- [x] Entity extraction (callsign, altitude, heading, runway)
- [x] Response generation with Ollama
- [x] Lua templates (Export and Mission scripts)
- [x] Configuration files (YAML)
- [x] Main application CLI
- [x] Comprehensive test suite

### 🚧 In Progress
- [ ] Voice input handler (PTT detection)
- [ ] Speech-to-text engine integration
- [ ] Text-to-speech with radio effects
- [ ] DCS Export bridge (UDP listener)
- [ ] ATC controller state machine
- [ ] SRS integration

### 📋 TODO
- [ ] Configuration wizard (GUI)
- [ ] PyInstaller build spec
- [ ] Inno Setup installer
- [ ] Mission script templates
- [ ] Documentation and tutorials
- [ ] Video demo

## Testing

This project follows **Test-Driven Development (TDD)** principles. All core components have comprehensive test coverage.

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_ollama_manager.py -v

# Run specific test
pytest tests/test_ollama_manager.py::TestOllamaManager::test_start_ollama_launches_process -v
```

## Configuration

### Settings (config/settings.yaml)

```yaml
dcs:
  installation_path: "auto"  # Auto-detect or manual path
  variant: "openbeta"

ollama:
  model: "llama3.2:3b"
  auto_start: true
  port: 11434

audio:
  ptt_key: "RCtrl+RShift"
  sample_rate: 22050

stt:
  engine: "whisper"  # whisper or fireworks
  model: "base"

tts:
  engine: "piper"
  radio_effects: true

atc:
  phraseology: "military"
  strictness: "relaxed"
```

## Aviation Commands

The system understands natural military aviation communications:

```
# Startup and Taxi
"Request startup clearance"
"Request taxi to active runway"
"Ready for takeoff"

# Takeoff and Departure
"Request takeoff clearance"
"Request departure runway 27 Left"

# Enroute
"Request climb to flight level 350"
"Turn right heading 270"
"Request descent"

# Approach and Landing
"Request landing clearance"
"Inbound for landing runway 21"
```

## Military Phraseology

The system uses authentic US military radio procedures:

- **ATP 1-02.1** - Multi-Service Brevity Codes
- **FAA AIM Chapter 4** - Air Traffic Control Procedures
- **AFMAN 11-214** - Air Operations Rules and Procedures

Example responses:
```
"Viper 1-1, cleared for takeoff runway 21 Left, wind 210 at 8"
"Viper 1-1, climb and maintain flight level 350"
"Viper 1-1, turn right heading 270"
"Viper 1-1, cleared to land runway 27 Right, wind 270 at 12"
```

## How It Works

1. **Player speaks** into microphone (PTT activated)
2. **Speech-to-Text** converts audio to text (Whisper or Fireworks AI)
3. **NLP Processor** analyzes command:
   - Classifies intent (takeoff, landing, altitude change, etc.)
   - Extracts entities (callsign, runway, altitude, heading)
4. **Ollama generates** appropriate ATC response using military phraseology
5. **Text-to-Speech** converts response to audio with radio effects
6. **SRS transmits** response on appropriate radio frequency
7. **Player hears** ATC response in cockpit

## Safety Features

- ✅ **Automatic backups** before modifying any DCS files
- ✅ **Validation checks** after injection
- ✅ **Safe removal** of ATC code
- ✅ **Error recovery** with backup restoration
- ✅ **Non-destructive** hook installation

## Contributing

Contributions welcome! This project follows TDD principles:

1. Write tests first
2. Implement code to pass tests
3. Refactor as needed

```bash
# Run tests before committing
pytest

# Check code style
black src/ tests/
flake8 src/ tests/
```

## License

[Your License Here]

## Credits

Built with:
- [Ollama](https://ollama.com/) - Local LLM inference
- [Whisper](https://github.com/openai/whisper) - Speech recognition
- [Piper TTS](https://github.com/rhasspy/piper) - Text-to-speech
- [DCS-SimpleRadioStandalone](https://github.com/ciribob/DCS-SimpleRadioStandalone) - Radio integration

## References

- [DCS Scripting Engine Documentation](https://wiki.hoggitworld.com/)
- [ATP 1-02.1 Multi-Service Brevity Codes](https://irp.fas.org/doddir/army/atp1-02-1.pdf)
- [FAA AIM Chapter 4](https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap4_section_2.html)

## Support

For issues, questions, or contributions:
- GitHub Issues: [Report a bug or request a feature]
- Documentation: [See docs/]
- Community: [Discord/Forum link]

---

**⚠️ Important:** This is development software. Always backup your DCS installation before use. The system modifies `Export.lua` but creates automatic backups.

**🎯 Goal:** Create a fully voice-controlled ATC system that provides authentic military aviation communications in DCS World with zero manual configuration required.
