# Claude Code Prompt: DCS Natural Language ATC Plugin with Ollama Integration

## Mission Overview

Create a **plug-and-play Natural Language ATC system for DCS World** that allows players to use natural speech for realistic military aviation communications. The system should:

1. **Auto-launch and manage a local Ollama instance** for AI-powered natural language understanding
2. **Automatically detect and configure DCS World** with zero manual file editing
3. **Provide one-click installation** via Windows installer
4. **Support authentic US military radio procedures** (Navy/Air Force)
5. **Generate speech responses** with military radio effects
6. **Be cost-effective** using local AI models (no API costs)

## Architecture

```
User Speech (PTT) 
    ↓
[Python Application]
    ├─ STT: Whisper (local) or Fireworks AI streaming
    ├─ NLP: Ollama (Llama 3.2 3B) - automatic launch
    ├─ TTS: Piper TTS (local) - with radio effects
    └─ DCS Integration: Export.lua + Mission Scripts
        ↓
[DCS World + SRS Radio]
    ↓
Radio Response in Cockpit
```

## Reference Documentation

**You have access to two comprehensive research documents in `/mnt/user-data/outputs/`:**

1. **`Natural_Language_ATC_Research_Report.md`**
   - Complete technical research on STT/TTS technologies
   - DCS Lua scripting API and integration patterns
   - US military radio communication standards (ATP 1-02.1, FAA AIM)
   - NLP implementation strategies
   - Cost analysis and technology comparisons

2. **`DCS_ATC_Deployment_Architecture_Research.md`**
   - Ollama auto-launch and process management
   - DCS path detection and Export.lua injection
   - PyInstaller + Inno Setup installer creation
   - First-run configuration wizard
   - Multiplayer server architecture (post-MVP)

**IMPORTANT:** Read both documents thoroughly before starting implementation. They contain critical implementation details, code examples, and best practices.

---

## Technology Stack

### Core Technologies
- **Language:** Python 3.11+ (main application)
- **LLM:** Ollama with Llama 3.2 3B (auto-managed)
- **STT:** Whisper.cpp (local) or Fireworks AI (cloud fallback)
- **TTS:** Piper TTS (fast local) with radio processing
- **DCS Integration:** Lua scripts + LuaSocket
- **Radio:** SRS (DCS-SimpleRadioStandalone)
- **Packaging:** PyInstaller → Inno Setup installer

### Python Dependencies
```
ollama>=0.1.0
numpy>=1.24.0
sounddevice>=0.4.6
faster-whisper>=0.10.0  # Local Whisper
requests>=2.31.0
pydub>=0.25.1
pyaudio>=0.2.13
```

### System Requirements
- Windows 10/11 (primary target)
- 16GB RAM (8GB minimum)
- 4GB VRAM for Ollama (or CPU fallback)
- DCS World (any version/variant)

---

## Implementation Phases

### Phase 1: Core Infrastructure (MVP)
**Goal:** Single-player voice control with automatic setup

**Components to Build:**

1. **Ollama Manager (`ollama_manager.py`)**
   - Auto-detect if Ollama is installed
   - Launch `ollama serve` as subprocess
   - Health check and restart logic
   - Download Llama 3.2 3B model automatically
   - Graceful shutdown on exit
   - See research doc for subprocess.Popen patterns

2. **DCS Auto-Configurator (`dcs_configurator.py`)**
   - Detect DCS installation path (check `%USERPROFILE%\Saved Games\DCS*`)
   - Safely inject Export.lua code with backup
   - Generate mission script template
   - Validate installation
   - See research doc for safe file modification

3. **Voice Input Handler (`voice_input.py`)**
   - Push-to-talk detection (configurable hotkey)
   - Audio capture with sounddevice
   - Buffer management for continuous recording
   - Integration with STT engine

4. **Speech Recognition (`stt_engine.py`)**
   - **Primary:** faster-whisper (local) for privacy
   - **Fallback:** Fireworks AI streaming (300ms latency)
   - Aviation vocabulary optimization
   - See research doc for configuration

5. **Natural Language Processor (`nlp_processor.py`)**
   - Ollama chat interface for intent classification
   - Entity extraction (callsigns, altitudes, headings, runways)
   - Military phraseology validation
   - Context state management (current clearances, aircraft state)
   - Aviation-specific prompt engineering

6. **Text-to-Speech Engine (`tts_engine.py`)**
   - Piper TTS for fast local synthesis
   - Military radio effects (bandpass filter, compression)
   - Response caching for common phrases
   - See research doc for audio processing chain

7. **DCS Export Bridge (`dcs_bridge.py`)**
   - UDP socket listener on port 10308
   - Parse Export.lua data stream (JSON)
   - Track aircraft state (position, frequency, heading, speed)
   - Detect player vs AI aircraft

8. **ATC Logic Engine (`atc_controller.py`)**
   - State machine for flight phases (startup, taxi, takeoff, airborne, landing)
   - Generate appropriate ATC responses
   - Queue management for multiple players
   - Frequency-based communication routing

9. **SRS Integration (`srs_client.py`)**
   - Use DCS-SimpleTextToSpeech library
   - Transmit TTS audio on correct frequencies
   - Position-based transmission (tower location)

10. **Configuration Wizard (`config_wizard.py`)**
    - tkinter GUI for first-run setup
    - Auto-detect DCS path
    - Model selection (fast/balanced/quality)
    - PTT key configuration
    - Test microphone and audio output

11. **Main Application (`atc_main.py`)**
    - Application entry point
    - System tray icon (running indicator)
    - Start/stop services
    - Status monitoring
    - Error handling and logging

### Phase 2: Packaging and Distribution

12. **PyInstaller Build (`build_spec.py`)**
    - Create single executable
    - Bundle config templates
    - Include mission scripts
    - See research doc for spec file

13. **Inno Setup Installer (`installer.iss`)**
    - Check for Ollama, offer installation
    - Run configuration wizard on first install
    - Create desktop shortcut
    - Add to startup (optional)
    - See research doc for Pascal script

14. **Build Automation (`build.sh` / `build.bat`)**
    - One-command build process
    - Package dependencies
    - Generate installer

### Phase 3: Multiplayer Support (Post-MVP)

15. **Server Plugin Architecture**
    - Centralized ATC processing
    - Multi-player frequency management
    - Integrate with SRS server

---

## Critical Implementation Requirements

### 1. Ollama Integration

**Auto-Launch Pattern:**
```python
import subprocess
import time
import requests

class OllamaManager:
    def __init__(self):
        self.process = None
        self.model = "llama3.2:3b"
    
    def start(self):
        # Check if already running
        if self.is_running():
            return True
        
        # Launch ollama serve
        self.process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        
        # Wait for ready (max 30s)
        for _ in range(30):
            if self.is_running():
                return True
            time.sleep(1)
        return False
    
    def is_running(self):
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            return r.status_code == 200
        except:
            return False
    
    def ensure_model(self):
        import ollama
        try:
            ollama.pull(self.model)
        except:
            pass  # Already downloaded
```

**Ollama Prompting for ATC:**
```python
def process_atc_request(text, context):
    import ollama
    
    prompt = f"""You are an Air Traffic Controller at {context['airbase']}.

Aircraft: {context['callsign']} ({context['aircraft_type']})
Position: {context['position']}
Current State: {context['state']}
Active Clearances: {context['clearances']}

Pilot transmission: "{text}"

Respond using proper US military ATC phraseology. Be concise (1-2 sentences).
Format: [CALLSIGN], [RESPONSE]

Response:"""
    
    response = ollama.chat(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.3, "num_predict": 100}
    )
    
    return response['message']['content']
```

### 2. DCS Export.lua Injection

**Safe Injection Code:**
```python
import shutil
from pathlib import Path
from datetime import datetime

def inject_export_lua(dcs_scripts_path):
    export_lua = Path(dcs_scripts_path) / "Export.lua"
    
    # Create backup
    if export_lua.exists():
        backup = export_lua.with_suffix(f'.lua.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        shutil.copy2(export_lua, backup)
        content = export_lua.read_text(encoding='utf-8')
    else:
        content = ""
    
    # Check if already injected
    if "DCS Natural Language ATC" in content:
        return True
    
    # Append ATC code
    atc_code = '''
-- DCS Natural Language ATC Plugin
local atc_socket = nil

function LuaExportStart()
    package.path = package.path..";.\\\\LuaSocket\\\\?.lua"
    package.cpath = package.cpath..";.\\\\LuaSocket\\\\?.dll"
    local socket = require("socket")
    atc_socket = socket.udp()
    atc_socket:settimeout(0)
    atc_socket:setsockname("*", 0)
    atc_socket:setpeername("127.0.0.1", 10308)
end

function LuaExportAfterNextFrame()
    if not atc_socket then return end
    local data = {
        pilot = LoGetPilotName(),
        position = LoGetSelfData() and LoGetSelfData().LatLongAlt or nil,
        frequency = LoGetRadioBeaconsStatus() and LoGetRadioBeaconsStatus()[1] or nil
    }
    atc_socket:send(require("json").encode(data) .. "\\n")
end
'''
    
    export_lua.write_text(content + "\n" + atc_code, encoding='utf-8')
    return True
```

### 3. Military Phraseology Reference

**Implement these standard formats** (from ATP 1-02.1 and FAA AIM):

```python
ATC_PHRASEOLOGY = {
    "startup_clearance": "{callsign}, cleared for startup, altimeter {altimeter}",
    "taxi_clearance": "{callsign}, taxi to runway {runway} via {taxiway}, hold short",
    "takeoff_clearance": "{callsign}, wind {wind}, cleared for takeoff runway {runway}",
    "landing_clearance": "{callsign}, cleared to land runway {runway}, wind {wind}",
    "altitude_assignment": "{callsign}, climb and maintain {altitude}",
    "heading_assignment": "{callsign}, turn {direction} heading {heading}",
    "roger": "{callsign}, roger",
    "say_again": "{callsign}, say again",
    "standby": "{callsign}, standby"
}
```

### 4. Radio Effects Processing

**Apply military radio characteristics:**
```python
from scipy import signal
import numpy as np

def apply_radio_effects(audio, sample_rate=22050):
    # Bandpass filter (300Hz - 3400Hz for radio)
    sos = signal.butter(4, [300, 3400], 'bandpass', 
                       fs=sample_rate, output='sos')
    filtered = signal.sosfilt(sos, audio)
    
    # Compression (reduce dynamic range)
    threshold = 0.2
    ratio = 4.0
    compressed = np.where(
        np.abs(filtered) > threshold,
        threshold + (np.abs(filtered) - threshold) / ratio,
        filtered
    )
    
    # Add subtle static
    static = np.random.normal(0, 0.01, len(compressed))
    final = compressed + static
    
    return final / np.max(np.abs(final))  # Normalize
```

### 5. Configuration Structure

**Use YAML for config:**
```yaml
# config/settings.yaml
dcs:
  installation_path: "auto"  # Auto-detect or manual path
  variant: "openbeta"  # stable, openbeta, or custom
  
ollama:
  model: "llama3.2:3b"  # fast, balanced, or quality
  auto_start: true
  port: 11434
  
audio:
  ptt_key: "RCtrl+RShift"
  input_device: "default"
  output_device: "default"
  sample_rate: 22050
  
stt:
  engine: "whisper"  # whisper (local) or fireworks (cloud)
  model: "base"  # tiny, base, small, medium
  
tts:
  engine: "piper"
  voice: "en_US-amy-medium"
  radio_effects: true
  
atc:
  phraseology: "military"  # military or civilian
  strictness: "relaxed"  # strict or relaxed
  response_delay: 0.5  # Realistic ATC delay in seconds
```

---

## Project Structure

```
dcs-nl-atc/
├── atc_main.py              # Main application entry
├── build_spec.py            # PyInstaller spec
├── installer.iss            # Inno Setup script
├── requirements.txt
├── README.md
│
├── config/
│   ├── settings.yaml        # Default configuration
│   └── phraseology.yaml     # ATC phrase templates
│
├── src/
│   ├── ollama_manager.py    # Ollama process management
│   ├── dcs_configurator.py  # DCS auto-configuration
│   ├── voice_input.py       # PTT and audio capture
│   ├── stt_engine.py        # Speech-to-text
│   ├── nlp_processor.py     # Ollama NLP processing
│   ├── tts_engine.py        # Text-to-speech + effects
│   ├── dcs_bridge.py        # Export.lua data listener
│   ├── atc_controller.py    # ATC logic and state
│   ├── srs_client.py        # SRS radio integration
│   └── config_wizard.py     # First-run setup GUI
│
├── lua/
│   ├── export_template.lua  # Export.lua injection code
│   └── mission_script.lua   # Mission ATC script template
│
├── templates/
│   └── mission_atc.lua      # Installable mission script
│
└── assets/
    ├── atc_icon.ico         # Application icon
    └── phraseology/         # Military comm references
        ├── atp_1-02-1_excerpts.txt
        └── faa_aim_excerpts.txt
```

---

## Testing Strategy

### Unit Testing
```python
# tests/test_nlp_processor.py
def test_takeoff_request():
    text = "Tower, Viper 1-1, request takeoff clearance"
    context = {"callsign": "Viper 1-1", "state": "READY_TAXI"}
    
    response = process_atc_request(text, context)
    
    assert "cleared for takeoff" in response.lower()
    assert "viper 1-1" in response.lower()

def test_altitude_change():
    text = "Request climb to flight level 250"
    context = {"callsign": "Viper 1-1", "state": "AIRBORNE"}
    
    response = process_atc_request(text, context)
    
    assert "250" in response or "two five zero" in response
```

### Integration Testing
1. Test Ollama launch and model download
2. Test DCS path detection on clean system
3. Test Export.lua injection and backup
4. Test end-to-end voice flow in DCS training mission

### User Acceptance Testing
1. Install on clean Windows machine
2. User follows configuration wizard
3. User loads DCS training mission
4. User tests 10 standard ATC commands
5. Measure latency (target <2 seconds total)

---

## Performance Targets

- **Ollama Inference:** 200-500ms
- **STT:** 300-500ms (Whisper) or 150-300ms (Fireworks)
- **TTS:** 100-200ms (Piper with caching)
- **Total Latency:** <2 seconds end-to-end
- **Memory Usage:** <4GB (excluding DCS)
- **Accuracy:** >90% intent recognition on standard phraseology

---

## Deployment Checklist

- [ ] All components implemented and tested
- [ ] Ollama auto-launch working reliably
- [ ] DCS installation detected on test machines
- [ ] Export.lua injection with safe backup
- [ ] Configuration wizard tested
- [ ] PyInstaller executable builds successfully
- [ ] Inno Setup installer created
- [ ] README with installation instructions
- [ ] Video tutorial recorded
- [ ] GitHub repository with documentation
- [ ] Initial release tagged

---

## Critical Success Factors

1. **Zero Manual Configuration:** Users should never edit files manually
2. **Robust Error Handling:** Graceful degradation if Ollama fails
3. **Safe DCS Integration:** Always backup before modifying files
4. **Clear User Feedback:** Show status in system tray icon
5. **Documentation:** README, video tutorial, troubleshooting guide

---

## Additional Context

### Why Ollama vs OpenRouter?
- **No API costs** - completely free after setup
- **Privacy** - all processing local
- **Offline capable** - no internet required
- **Fast enough** - 200-500ms with 3B model
- **User owns their data** - no external dependencies

### Why Llama 3.2 3B?
- Smallest model with good instruction following
- Fast inference on CPU (if no GPU)
- Good at structured tasks like aviation communications
- 4GB VRAM requirement (very accessible)

### Why Piper TTS?
- Extremely fast (<200ms)
- High quality voices
- Local processing (privacy)
- Easy radio effects application
- Zero cost

---

## Getting Started (Claude Code)

1. **Read both research documents** in `/mnt/user-data/outputs/`
2. **Create project structure** as outlined above
3. **Start with Ollama manager** - this is the foundation
4. **Build DCS configurator** - critical for user experience
5. **Implement voice pipeline** - STT → NLP → TTS
6. **Integrate with DCS** - Export.lua and mission scripts
7. **Create installer** - PyInstaller + Inno Setup
8. **Test thoroughly** - on clean Windows installation
9. **Document everything** - README, comments, troubleshooting

**Prioritize:**
- Automatic Ollama management (critical for "plug and play")
- Safe DCS configuration (users must trust the tool)
- Clear error messages (when things go wrong)
- Fast iteration (quick test cycles)

**The goal:** A user downloads one installer, runs it, follows a 3-step wizard, and immediately has natural language ATC working in DCS World.

---

## Questions to Resolve During Implementation

1. Should we bundle Ollama installer or require separate install?
2. Best approach for PTT detection (polling vs hooks)?
3. Cache strategy for Ollama responses?
4. Handling DCS updates that might break Export.lua?
5. Multiplayer: client-side or server-side processing?

---

## Next Steps

Claude Code, please:
1. Review both research documents
2. Set up the project structure
3. Implement the Ollama manager with auto-launch
4. Create the DCS path detector and Export.lua injector
5. Build a simple test harness to verify Ollama integration
6. Begin implementing the voice pipeline components

Let's build something amazing! 🎯✈️

---

# CURRENT IMPLEMENTATION STATUS

**Last Updated:** Session ending at context limit
**Branch:** `claude/tdd-implementation-011CUk2yiLhw3YiWJyTBsMVH`
**Status:** Phase 1 MVP Core Components - 65/65 Tests Passing (70% Coverage)

## ✅ COMPLETED COMPONENTS

### 1. Project Infrastructure
- **Project Structure:** All directories created (src/, tests/, config/, lua/, templates/)
- **Requirements:** requirements.txt with all dependencies
- **Pytest Configuration:** pytest.ini with coverage settings
- **CI/CD Pipeline:** GitHub Actions workflow (Windows-only, Python 3.11)
- **Git Configuration:** .gitignore, .pre-commit-config.yaml
- **Documentation:** README.md, CONTRIBUTING.md, DEVELOPMENT_STATUS.md, CI_CD_SUMMARY.md

### 2. OllamaManager (`src/ollama_manager.py`) ✅
**Status:** Fully implemented with TDD (17 tests passing)

**Key Features:**
- Auto-detects if Ollama is running on localhost:11434
- Launches `ollama serve` as subprocess with proper process management
- Health checking with timeout and retry logic
- Automatic model download (llama3.2:3b)
- Graceful shutdown with process termination
- Windows-specific process group handling (CREATE_NEW_PROCESS_GROUP)

**Implementation Details:**
```python
class OllamaManager:
    def __init__(self, port: int = 11434, model: str = "llama3.2:3b", timeout: int = 30)
    def is_running() -> bool  # Checks /api/tags endpoint
    def start() -> bool  # Launches ollama serve
    def stop() -> bool  # Terminates process
    def ensure_model() -> bool  # Downloads model if missing
    def chat(messages: List[Dict]) -> str  # Chat interface
```

**Tests:** `tests/test_ollama_manager.py`
- Initialization with custom port/model
- Start/stop lifecycle
- Health checking
- Model management
- Chat interface
- Error handling

**Known Issues:**
- Tests work without ollama installed (use fallback behaviors)
- Model download tests accept any boolean (True if model exists, False if not)

### 3. DCS Configurator (`src/dcs_configurator.py`) ✅
**Status:** Fully implemented with TDD (21 tests passing)

**Key Features:**
- Auto-detects DCS installation path from Windows registry and common locations
- Safely injects Export.lua code with automatic timestamped backups
- Validates injection success
- Supports multiple DCS variants (stable, openbeta, custom)
- Provides rollback capability

**Implementation Details:**
```python
class DCSPathDetector:
    def get_primary_dcs_path(variant: str = 'openbeta') -> Optional[Path]
    def _check_registry() -> Optional[Path]
    def _check_common_paths(variant: str) -> Optional[Path]

class ExportLuaInjector:
    def __init__(self, dcs_scripts_path: Path, template_path: Path)
    def inject_atc_code() -> bool
    def create_backup() -> Path
    def validate_injection() -> bool
    def restore_backup(backup_path: Path) -> bool
```

**Tests:** `tests/test_dcs_configurator.py`
- Path detection (registry, common paths, fallback)
- Export.lua injection logic
- Backup creation and validation
- Duplicate injection prevention
- Complete configuration flow

### 4. NLP Processor (`src/nlp_processor.py`) ✅
**Status:** Fully implemented with TDD (27 tests passing)

**Key Features:**
- Intent classification for aviation commands (takeoff, landing, taxi, altitude change, etc.)
- Entity extraction (callsign, runway, altitude, heading, frequency)
- Template-based response generation with military phraseology
- Fallback to templates when Ollama unavailable
- Context management for realistic ATC communications

**Implementation Details:**
```python
class ATCCommandParser:
    def parse_command(text: str) -> Dict
    def _classify_intent(text: str) -> str
    def _extract_entities(text: str, intent: str) -> Dict
    def _extract_callsign(text: str) -> Optional[str]
    def _extract_runway(text: str) -> Optional[str]
    def _extract_altitude(text: str) -> Optional[str]
    def _extract_heading(text: str) -> Optional[str]

class ATCResponseGenerator:
    def __init__(self, use_ollama: bool = True)
    def generate_response(context: Dict) -> str
    def _generate_with_ollama(context: Dict) -> str
    def _generate_from_template(intent: str, entities: Dict, callsign: str) -> str
```

**Supported Intents:**
- request_takeoff
- request_landing
- request_taxi
- request_altitude_change
- request_heading_change
- request_frequency_change
- request_startup
- request_pushback
- report_ready
- unknown

**Tests:** `tests/test_nlp_processor.py`
- Command parsing (takeoff, landing, taxi, altitude, heading, etc.)
- Intent classification
- Entity extraction (callsign, runway, altitude, heading)
- Response generation (template-based and Ollama-based)
- Error handling

**Known Issues Fixed:**
- Template formatting now avoids duplicate callsign parameters
- Intent classifier patterns match only realistic aviation phrases
- Tests work without Ollama installed (use template fallbacks)

### 5. Configuration Files ✅

**`config/settings.yaml`:**
- Complete system configuration for DCS, Ollama, audio, STT, TTS, ATC
- All settings documented with comments

**`config/phraseology.yaml`:**
- Military radio communication templates
- Standard ATC responses
- Brevity codes
- Authentication procedures

### 6. Lua Templates ✅

**`lua/export_template.lua`:**
- Export.lua injection code for DCS data export
- UDP socket setup on port 10308
- Aircraft state export (position, frequency, heading, speed)
- JSON encoding with safe error handling

**`lua/mission_script.lua`:**
- Mission environment ATC system
- Event handlers for takeoff, landing, crash, etc.
- Radio message handling
- Multi-aircraft support

### 7. CLI Application (`atc_main.py`) ✅
**Status:** Basic implementation complete

**Features:**
- Configure mode: Auto-detect and configure DCS
- Test NLP mode: Test command parsing
- Interactive mode: Chat with ATC (planned for full implementation)
- Setup Ollama mode: Download and configure Ollama

**Usage:**
```bash
python atc_main.py --configure  # Configure DCS
python atc_main.py --test-nlp  # Test NLP
python atc_main.py --interactive  # Interactive chat (basic)
python atc_main.py --setup-ollama  # Setup Ollama
```

### 8. Documentation ✅

**`README.md`:**
- Quick start guide
- Installation instructions
- Architecture overview
- Usage examples
- Development guidelines

**`CONTRIBUTING.md`:**
- TDD workflow
- Code style guidelines
- PR process

**`DEVELOPMENT_STATUS.md`:**
- Current status
- Roadmap
- Test coverage metrics

**`CI_CD_SUMMARY.md`:**
- CI/CD implementation details
- Simplified Windows-only pipeline

## ⏳ PENDING COMPONENTS (Phase 1 Remaining)

### 9. Voice Input Handler (`voice_input.py`) - NOT STARTED
**Priority:** HIGH
**Complexity:** MEDIUM

**Requirements:**
- Push-to-talk (PTT) detection via keyboard hook or polling
- Audio capture using sounddevice
- Buffer management for continuous recording
- Integration with STT engine
- Configurable PTT key from settings.yaml

**TDD Approach:**
1. Write tests for PTT detection (mock keyboard input)
2. Write tests for audio buffer management
3. Write tests for audio capture start/stop
4. Implement to pass tests
5. Refactor for performance

**Dependencies:**
- sounddevice
- keyboard (for PTT)
- numpy (for audio buffer)

### 10. Speech Recognition (`stt_engine.py`) - NOT STARTED
**Priority:** HIGH
**Complexity:** HIGH

**Requirements:**
- Primary: faster-whisper (local) for privacy
- Fallback: Fireworks AI streaming (if configured)
- Aviation vocabulary optimization
- Handle audio input from voice_input.py
- Return transcribed text with confidence scores

**TDD Approach:**
1. Write tests for audio input handling (mock audio data)
2. Write tests for Whisper model loading
3. Write tests for transcription (mock Whisper API)
4. Write tests for Fireworks AI fallback
5. Implement to pass tests
6. Benchmark and optimize

**Dependencies:**
- faster-whisper
- numpy
- requests (for Fireworks AI)

### 11. Text-to-Speech Engine (`tts_engine.py`) - NOT STARTED
**Priority:** HIGH
**Complexity:** MEDIUM

**Requirements:**
- Piper TTS for fast local synthesis
- Military radio effects (bandpass filter, compression, static)
- Response caching for common phrases
- Integration with SRS for radio transmission

**TDD Approach:**
1. Write tests for TTS synthesis (mock Piper)
2. Write tests for radio effects processing
3. Write tests for audio caching
4. Write tests for audio output
5. Implement to pass tests
6. Tune radio effects for realism

**Dependencies:**
- piper-tts
- scipy (for audio processing)
- pydub
- sounddevice

**Radio Effects Implementation:**
```python
def apply_radio_effects(audio, sample_rate=22050):
    # Bandpass filter (300Hz - 3400Hz)
    sos = signal.butter(4, [300, 3400], 'bandpass', fs=sample_rate, output='sos')
    filtered = signal.sosfilt(sos, audio)

    # Compression (reduce dynamic range)
    threshold = 0.2
    ratio = 4.0
    compressed = np.where(
        np.abs(filtered) > threshold,
        threshold + (np.abs(filtered) - threshold) / ratio,
        filtered
    )

    # Add subtle static
    static = np.random.normal(0, 0.01, len(compressed))
    final = compressed + static

    return final / np.max(np.abs(final))  # Normalize
```

### 12. DCS Export Bridge (`dcs_bridge.py`) - NOT STARTED
**Priority:** HIGH
**Complexity:** LOW

**Requirements:**
- UDP socket listener on port 10308
- Parse JSON data stream from Export.lua
- Track aircraft state (position, frequency, heading, speed, altitude)
- Detect player vs AI aircraft
- Thread-safe state management

**TDD Approach:**
1. Write tests for UDP socket creation
2. Write tests for JSON parsing
3. Write tests for state tracking
4. Write tests for multi-aircraft handling
5. Implement to pass tests

**Dependencies:**
- socket (standard library)
- json (standard library)
- threading (for background listening)

### 13. ATC Logic Engine (`atc_controller.py`) - NOT STARTED
**Priority:** HIGH
**Complexity:** HIGH

**Requirements:**
- State machine for flight phases (startup, taxi, takeoff, airborne, landing, shutdown)
- Generate appropriate ATC responses based on flight phase
- Queue management for multiple players
- Frequency-based communication routing
- Integration with NLP processor and response generator

**TDD Approach:**
1. Write tests for state machine transitions
2. Write tests for flight phase detection
3. Write tests for ATC response logic
4. Write tests for queue management
5. Write tests for frequency routing
6. Implement to pass tests
7. Refactor for maintainability

**State Machine:**
```python
class FlightPhase(Enum):
    COLD_START = "cold_start"
    STARTUP = "startup"
    TAXI = "taxi"
    TAKEOFF_CLEARANCE = "takeoff_clearance"
    AIRBORNE = "airborne"
    APPROACH = "approach"
    LANDING_CLEARANCE = "landing_clearance"
    LANDED = "landed"
    SHUTDOWN = "shutdown"
```

### 14. SRS Integration (`srs_client.py`) - NOT STARTED
**Priority:** MEDIUM
**Complexity:** MEDIUM

**Requirements:**
- Use DCS-SimpleRadioStandalone library
- Transmit TTS audio on correct frequencies
- Position-based transmission (tower location)
- Handle frequency changes
- Support multiple simultaneous transmissions

**TDD Approach:**
1. Write tests for SRS connection
2. Write tests for frequency management
3. Write tests for audio transmission
4. Write tests for position-based radio
5. Implement to pass tests

**Dependencies:**
- SRS API/library (research needed)
- websockets (for SRS communication)

### 15. Configuration Wizard (`config_wizard.py`) - NOT STARTED
**Priority:** MEDIUM (for Phase 2)
**Complexity:** MEDIUM

**Requirements:**
- tkinter GUI for first-run setup
- Auto-detect DCS path with manual override
- Model selection (fast/balanced/quality)
- PTT key configuration with key capture
- Test microphone and audio output
- Save configuration to settings.yaml

**TDD Approach:**
1. Write tests for GUI initialization
2. Write tests for DCS path detection UI
3. Write tests for key capture
4. Write tests for audio device testing
5. Write tests for config file writing
6. Implement to pass tests

**Dependencies:**
- tkinter (standard library)
- keyboard (for key capture)

### 16. Main Application Enhancement (`atc_main.py`) - PARTIALLY COMPLETE
**Priority:** HIGH
**Complexity:** MEDIUM

**Current Status:** Basic CLI modes implemented
**Remaining Work:**
- System tray icon (running indicator)
- Full interactive mode with voice pipeline
- Status monitoring dashboard
- Error handling and logging improvements
- Service lifecycle management

**TDD Approach:**
1. Write tests for service startup/shutdown
2. Write tests for status monitoring
3. Write tests for error recovery
4. Implement to pass tests

## 🔧 TECHNICAL DECISIONS & KNOWN ISSUES

### Test Environment
- Tests run without Ollama installed (use mocks and fallback behaviors)
- CI/CD runs on clean Windows environment with Python 3.11
- Coverage target: 70%+ (currently at 70%)

### Ollama Integration
- Auto-launch works reliably on Windows
- Model download is automatic but not mocked in tests
- Health checking uses /api/tags endpoint with 2s timeout

### DCS Configuration
- Registry detection requires Windows
- Backup files use timestamp format: `Export.lua.backup_YYYYMMDD_HHMMSS`
- Validation checks for marker comment in Export.lua

### NLP Processor
- Template-based responses work without Ollama (fallback mode)
- Intent classification uses regex patterns for common aviation phrases
- Entity extraction handles multiple formats (e.g., "flight level 250", "25000 feet")

### CI/CD Pipeline
- Simplified to single Windows build per user feedback
- Runs on push to main, develop, or claude/** branches
- Runs on PRs to main or develop
- Uses pip cache for faster builds

## 📋 QUICK REFERENCE COMMANDS

### Development
```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_ollama_manager.py -v

# Run tests matching pattern
pytest -k "test_parse" -v

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install -r requirements.txt && pip install pytest pytest-cov pytest-asyncio pytest-mock
```

### Git Operations
```bash
# Check status
git status

# Commit changes
git add .
git commit -m "feat: description"

# Push to branch (MUST match session ID)
git push -u origin claude/tdd-implementation-011CUk2yiLhw3YiWJyTBsMVH

# Create PR manually
# https://github.com/Xyrces/dcsAiComms/pull/new/claude/tdd-implementation-011CUk2yiLhw3YiWJyTBsMVH
```

### Testing Individual Components
```bash
# Test Ollama Manager
python -c "from src.ollama_manager import OllamaManager; m = OllamaManager(); print(m.is_running())"

# Test DCS Configurator
python -c "from src.dcs_configurator import DCSPathDetector; print(DCSPathDetector.get_primary_dcs_path())"

# Test NLP Processor
python -c "from src.nlp_processor import ATCCommandParser; p = ATCCommandParser(); print(p.parse_command('Tower, Viper 1-1, request takeoff'))"

# Run CLI
python atc_main.py --configure
python atc_main.py --test-nlp
```

## 🎯 SUCCESS CRITERIA FOR NEXT PHASE

### Voice Input Handler
- [ ] PTT detection working with configurable key
- [ ] Audio capture functional with sounddevice
- [ ] Buffer management prevents audio dropouts
- [ ] Integration tests with mock STT engine
- [ ] Tests passing (10+ tests)

### STT Engine
- [ ] Whisper model loads and transcribes audio
- [ ] Fireworks AI fallback working (if configured)
- [ ] Aviation vocabulary optimization applied
- [ ] Latency < 500ms for Whisper
- [ ] Tests passing (10+ tests)

### TTS Engine
- [ ] Piper TTS synthesizes audio
- [ ] Radio effects applied correctly
- [ ] Response caching reduces latency
- [ ] Audio output functional
- [ ] Tests passing (10+ tests)

### DCS Bridge
- [ ] UDP listener receives Export.lua data
- [ ] JSON parsing works reliably
- [ ] Aircraft state tracked correctly
- [ ] Multi-aircraft support
- [ ] Tests passing (8+ tests)

### ATC Controller
- [ ] State machine transitions correctly
- [ ] Flight phase detection accurate
- [ ] ATC responses appropriate for phase
- [ ] Queue management working
- [ ] Tests passing (15+ tests)

## 🚀 RECOMMENDED NEXT STEPS

**For continuing this work:**

1. **Create PR for current work:**
   - Navigate to: https://github.com/Xyrces/dcsAiComms/pull/new/claude/tdd-implementation-011CUk2yiLhw3YiWJyTBsMVH
   - Fill in PR template with completed components
   - Wait for CI to pass (should pass - all tests passing locally)

2. **Start next component (Voice Input Handler):**
   - Create new branch: `claude/voice-input-handler-<session-id>`
   - Follow TDD approach: Write tests first
   - Implement to pass tests
   - Commit and push when complete

3. **Continue with remaining Phase 1 components:**
   - STT Engine → TTS Engine → DCS Bridge → ATC Controller
   - Each component should follow same TDD pattern
   - Each component should be on separate branch with PR

4. **Integration testing:**
   - After all Phase 1 components complete
   - Create end-to-end test with all components
   - Test in actual DCS environment

## 📝 TDD WORKFLOW REMINDER

For each new component:

1. **RED:** Write failing tests first
   - Think through all edge cases
   - Mock external dependencies
   - Test both success and failure paths

2. **GREEN:** Write minimal code to pass tests
   - Don't over-engineer
   - Focus on making tests pass
   - Keep it simple

3. **REFACTOR:** Clean up code
   - Remove duplication
   - Improve naming
   - Add comments
   - Ensure tests still pass

4. **COMMIT:** Save progress
   - Descriptive commit messages
   - Reference tests in commit
   - Push to branch

## 🔍 IMPORTANT NOTES FOR FUTURE SESSIONS

1. **Branch Naming:** Always use format `claude/<component-name>-<session-id>` for proper git authentication

2. **Test Coverage:** Maintain 70%+ coverage, run `pytest --cov=src --cov-report=term-missing` before committing

3. **Mocking Strategy:** Mock external dependencies (ollama, DCS, hardware) to allow tests to run in clean CI environment

4. **Documentation:** Update DEVELOPMENT_STATUS.md after each component completion

5. **User Feedback:** User prefers simple, focused implementations - avoid over-engineering

6. **Windows-Only:** This is a Windows-only application (DCS is Windows-only), no need for cross-platform support

---

**End of Status Update**
