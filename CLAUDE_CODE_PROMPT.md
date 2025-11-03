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
