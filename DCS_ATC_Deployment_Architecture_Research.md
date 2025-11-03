# DCS Natural Language ATC: Plug-and-Play Deployment Architecture

## Executive Summary

This research report provides detailed implementation guidance for creating a **one-click deployment system** for the DCS Natural Language ATC plugin with **automatic Ollama integration** and **seamless DCS script injection**. The recommended architecture uses a **Python-based installer wrapped in Inno Setup** that handles all dependencies, launches Ollama automatically, and configures DCS without user intervention.

---

## 1. Ollama Integration Architecture

### Automatic Ollama Launch Strategy

**Best Practice: Embedded Process Management**

```python
import subprocess
import os
import time
import requests
from pathlib import Path

class OllamaManager:
    def __init__(self):
        self.ollama_process = None
        self.ollama_port = 11434
        self.model_name = "llama3.2:3b"  # Smaller model for aviation
        
    def is_ollama_running(self):
        """Check if Ollama server is responding"""
        try:
            response = requests.get(f"http://localhost:{self.ollama_port}/api/tags", 
                                  timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def start_ollama(self):
        """Launch Ollama server as background process"""
        if self.is_ollama_running():
            print("Ollama already running")
            return True
        
        try:
            # Launch Ollama server in background
            self.ollama_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            # Wait for server to be ready (max 30 seconds)
            for i in range(30):
                time.sleep(1)
                if self.is_ollama_running():
                    print("Ollama server started successfully")
                    return True
            
            print("Ollama server failed to start within timeout")
            return False
            
        except FileNotFoundError:
            print("Ollama not found. Please install Ollama first.")
            return False
        except Exception as e:
            print(f"Error starting Ollama: {e}")
            return False
    
    def ensure_model(self):
        """Download model if not present"""
        try:
            import ollama
            
            # Check if model exists
            models = ollama.list()
            if self.model_name not in [m['name'] for m in models['models']]:
                print(f"Downloading {self.model_name}...")
                ollama.pull(self.model_name)
                print("Model downloaded successfully")
            else:
                print(f"Model {self.model_name} already available")
            return True
        except Exception as e:
            print(f"Error ensuring model: {e}")
            return False
    
    def stop_ollama(self):
        """Stop Ollama server"""
        if self.ollama_process:
            self.ollama_process.terminate()
            self.ollama_process.wait(timeout=5)
            print("Ollama server stopped")
```

### Ollama Installation Detection and Auto-Install

```python
import shutil
import urllib.request
import tempfile

class OllamaInstaller:
    @staticmethod
    def is_ollama_installed():
        """Check if ollama command is available"""
        return shutil.which("ollama") is not None
    
    @staticmethod
    def install_ollama_windows():
        """Download and install Ollama on Windows"""
        print("Ollama not found. Installing...")
        
        # Download Ollama installer
        installer_url = "https://ollama.com/download/OllamaSetup.exe"
        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp:
            urllib.request.urlretrieve(installer_url, tmp.name)
            installer_path = tmp.name
        
        # Run installer silently
        subprocess.run([installer_path, "/S"], check=True)
        
        # Cleanup
        os.remove(installer_path)
        print("Ollama installed successfully")
        return True
    
    @staticmethod
    def setup():
        """Ensure Ollama is installed and ready"""
        if not OllamaInstaller.is_ollama_installed():
            if os.name == 'nt':  # Windows
                return OllamaInstaller.install_ollama_windows()
            else:
                print("Please install Ollama manually: https://ollama.com/download")
                return False
        return True
```

### Model Selection for Aviation

**Recommended Models:**
- **Primary: Llama 3.2 3B** - Fast, efficient, good for structured aviation comms
- **Alternative: Phi-3-mini 3.8B** - Microsoft model, excellent instruction following
- **High-end: Llama 3.1 8B** - Better accuracy if user has more VRAM

```python
MODEL_OPTIONS = {
    "fast": {
        "name": "llama3.2:3b",
        "vram": "4GB",
        "latency": "~200ms"
    },
    "balanced": {
        "name": "phi3:3.8b",
        "vram": "6GB", 
        "latency": "~300ms"
    },
    "quality": {
        "name": "llama3.1:8b",
        "vram": "8GB",
        "latency": "~500ms"
    }
}
```

---

## 2. DCS Automatic Configuration

### DCS Installation Path Detection

```python
import winreg
from pathlib import Path

class DCSPathDetector:
    @staticmethod
    def get_saved_games_path():
        """Get Windows Saved Games folder path"""
        # Standard location
        saved_games = Path(os.path.expanduser("~")) / "Saved Games"
        
        # Check if user moved Saved Games folder
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
            value, _ = winreg.QueryValueEx(key, "{4C5C32FF-BB9D-43b0-B5B4-2D72E54EAAA4}")
            winreg.CloseKey(key)
            saved_games = Path(os.path.expandvars(value))
        except:
            pass
        
        return saved_games
    
    @staticmethod
    def detect_dcs_variants():
        """Find all DCS installations (stable, openbeta, custom)"""
        saved_games = DCSPathDetector.get_saved_games_path()
        variants = []
        
        # Check for common variants
        for variant in ["DCS", "DCS.openbeta"]:
            path = saved_games / variant
            if path.exists() and (path / "Scripts").exists():
                variants.append({
                    "name": variant,
                    "path": path,
                    "scripts_path": path / "Scripts"
                })
        
        # Check for custom variants (DCS.customname)
        for item in saved_games.iterdir():
            if item.is_dir() and item.name.startswith("DCS."):
                if item not in [v["path"] for v in variants]:
                    if (item / "Scripts").exists():
                        variants.append({
                            "name": item.name,
                            "path": item,
                            "scripts_path": item / "Scripts"
                        })
        
        return variants
    
    @staticmethod
    def get_primary_dcs_path():
        """Get the most likely DCS installation to use"""
        variants = DCSPathDetector.detect_dcs_variants()
        
        if not variants:
            return None
        
        # Prefer openbeta if available, otherwise use first found
        for variant in variants:
            if "openbeta" in variant["name"].lower():
                return variant
        
        return variants[0]
```

### Safe Export.lua Injection

```python
import shutil
from datetime import datetime

class ExportLuaInjector:
    def __init__(self, dcs_scripts_path):
        self.scripts_path = Path(dcs_scripts_path)
        self.export_lua_path = self.scripts_path / "Export.lua"
        self.backup_path = self.scripts_path / f"Export.lua.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def create_backup(self):
        """Create timestamped backup of Export.lua"""
        if self.export_lua_path.exists():
            shutil.copy2(self.export_lua_path, self.backup_path)
            print(f"Backup created: {self.backup_path}")
            return True
        return False
    
    def inject_atc_code(self):
        """Safely inject ATC export code into Export.lua"""
        atc_export_code = '''
-- ========== DCS Natural Language ATC Plugin ==========
-- Auto-injected by DCS-NL-ATC installer
local atc_socket = nil
local atc_enabled = true

local function atc_init()
    package.path = package.path..";.\\\\LuaSocket\\\\?.lua"
    package.cpath = package.cpath..";.\\\\LuaSocket\\\\?.dll"
    
    local success, socket = pcall(require, "socket")
    if success then
        atc_socket = socket.udp()
        atc_socket:settimeout(0)
        atc_socket:setsockname("*", 0)
        atc_socket:setpeername("127.0.0.1", 10308)
        log.write("DCS-NL-ATC", log.INFO, "ATC export initialized")
    else
        log.write("DCS-NL-ATC", log.ERROR, "Failed to load LuaSocket")
        atc_enabled = false
    end
end

local function atc_export()
    if not atc_enabled or not atc_socket then return end
    
    local data = {}
    data.time = LoGetModelTime()
    data.pilot = LoGetPilotName()
    
    local selfData = LoGetSelfData()
    if selfData then
        data.position = selfData.LatLongAlt
        data.heading = selfData.Heading
        data.speed = selfData.IndicatedAirSpeed
        data.altitude = selfData.Altitude
    end
    
    local radio = LoGetRadioBeaconsStatus()
    if radio and radio[1] then
        data.frequency = radio[1]
    end
    
    -- Send to ATC plugin
    local json_str = "{\\"type\\":\\"export\\",\\"data\\":" .. 
                     require("json").encode(data) .. "}\\n"
    atc_socket:send(json_str)
end

-- Hook into DCS export system
local atc_orig_LuaExportStart = LuaExportStart
function LuaExportStart()
    atc_init()
    if atc_orig_LuaExportStart then
        atc_orig_LuaExportStart()
    end
end

local atc_orig_LuaExportAfterNextFrame = LuaExportAfterNextFrame
function LuaExportAfterNextFrame()
    atc_export()
    if atc_orig_LuaExportAfterNextFrame then
        atc_orig_LuaExportAfterNextFrame()
    end
end

log.write("DCS-NL-ATC", log.INFO, "ATC plugin hooks installed")
-- ========== End DCS Natural Language ATC Plugin ==========
'''
        
        try:
            # Read existing Export.lua or create new
            if self.export_lua_path.exists():
                with open(self.export_lua_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if already injected
                if "DCS Natural Language ATC Plugin" in content:
                    print("ATC code already present in Export.lua")
                    return True
                
                # Create backup
                self.create_backup()
            else:
                content = ""
                self.scripts_path.mkdir(parents=True, exist_ok=True)
            
            # Write with ATC code appended
            with open(self.export_lua_path, 'w', encoding='utf-8') as f:
                f.write(content)
                f.write("\n\n")
                f.write(atc_export_code)
            
            print("ATC export code injected successfully")
            return True
            
        except Exception as e:
            print(f"Error injecting ATC code: {e}")
            # Restore backup if available
            if self.backup_path.exists():
                shutil.copy2(self.backup_path, self.export_lua_path)
                print("Backup restored")
            return False
    
    def remove_atc_code(self):
        """Remove ATC code from Export.lua"""
        if not self.export_lua_path.exists():
            return True
        
        try:
            with open(self.export_lua_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove ATC section
            import re
            pattern = r'\n*-- ========== DCS Natural Language ATC Plugin ==========.*?-- ========== End DCS Natural Language ATC Plugin ==========\n*'
            new_content = re.sub(pattern, '', content, flags=re.DOTALL)
            
            if new_content != content:
                self.create_backup()
                with open(self.export_lua_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print("ATC code removed from Export.lua")
            
            return True
        except Exception as e:
            print(f"Error removing ATC code: {e}")
            return False
```

### Mission Script Template Generation

```python
class MissionScriptGenerator:
    @staticmethod
    def generate_atc_mission_script():
        """Generate Lua mission script for ATC functionality"""
        return '''
-- DCS Natural Language ATC Mission Script
-- Place this in your mission triggers or load via DO SCRIPT FILE

ATCSystem = {}
ATCSystem.players = {}
ATCSystem.airbases = {}

function ATCSystem:init()
    -- Discover all airbases
    for _, side in pairs({coalition.side.BLUE, coalition.side.RED, coalition.side.NEUTRAL}) do
        local bases = coalition.getAirbases(side)
        for _, airbase in pairs(bases) do
            local name = airbase:getName()
            self.airbases[name] = {
                airbase = airbase,
                coalition = side,
                frequency = 251.0  -- Default tower frequency
            }
        end
    end
    
    -- Setup event handler
    world.addEventHandler(self.eventHandler)
    
    trigger.action.outText("Natural Language ATC System Initialized", 10)
end

ATCSystem.eventHandler = {}

function ATCSystem.eventHandler:onEvent(event)
    if event.id == world.event.S_EVENT_PLAYER_ENTER_UNIT then
        ATCSystem:onPlayerEnter(event.initiator)
    elseif event.id == world.event.S_EVENT_BIRTH and event.initiator then
        local unit = event.initiator
        if unit:getPlayerName() then
            ATCSystem:onPlayerEnter(unit)
        end
    end
end

function ATCSystem:onPlayerEnter(unit)
    local playerName = unit:getPlayerName()
    if not playerName then return end
    
    local unitName = unit:getName()
    local groupID = unit:getGroup():getID()
    
    self.players[unitName] = {
        unit = unit,
        playerName = playerName,
        groupID = groupID,
        callsign = unit:getCallsign(),
        state = "STARTUP"
    }
    
    trigger.action.outTextForUnit(unit:getID(), 
        "Natural Language ATC Active - Use your radio for ATC communications", 10)
end

-- Initialize on mission start
ATCSystem:init()
'''
    
    @staticmethod
    def save_mission_template(output_path):
        """Save mission script template to file"""
        template = MissionScriptGenerator.generate_atc_mission_script()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template)
        print(f"Mission script template saved to: {output_path}")
```

---

## 3. One-Click Installer Architecture

### PyInstaller Build Configuration

```python
# build_spec.py - PyInstaller spec file
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['atc_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config/*', 'config'),
        ('models/*', 'models'),
        ('templates/*', 'templates'),
    ],
    hiddenimports=[
        'ollama',
        'pydub',
        'numpy',
        'scipy',
        'sounddevice',
        'pyaudio'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DCS_NL_ATC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/atc_icon.ico'
)
```

### Inno Setup Installer Script

```pascal
; DCS Natural Language ATC Installer
; Auto-generated Inno Setup script

#define MyAppName "DCS Natural Language ATC"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DCS-NL-ATC Project"
#define MyAppURL "https://github.com/your-repo/dcs-nl-atc"
#define MyAppExeName "DCS_NL_ATC.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=DCS_NL_ATC_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
SetupIconFile=assets\atc_icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startup"; Description: "Launch at Windows startup"; GroupDescription: "Additional options:"

[Files]
; Main executable
Source: "dist\DCS_NL_ATC.exe"; DestDir: "{app}"; Flags: ignoreversion
; Configuration files
Source: "config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs
; Mission templates
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs
; Documentation
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autostartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--startup"; Tasks: startup

[Run]
; Run configuration wizard after install
Filename: "{app}\{#MyAppExeName}"; Parameters: "--configure"; Description: "Configure DCS Natural Language ATC"; Flags: postinstall nowait skipifsilent

[Code]
function CheckOllamaInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('ollama', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  
  // Check if Ollama is installed
  if not CheckOllamaInstalled() then
  begin
    if MsgBox('Ollama is not installed. Would you like to install it now?', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      // Download and install Ollama
      // (Implement download logic here)
      MsgBox('Please install Ollama from https://ollama.com/download and run setup again.', 
             mbInformation, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  DCSPath: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Auto-configure DCS integration
    if MsgBox('Would you like to automatically configure DCS World integration?', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec(ExpandConstant('{app}\{#MyAppExeName}'), '--install-dcs-hooks', '', 
           SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;
```

### First-Run Configuration Wizard

```python
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

class ConfigurationWizard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DCS Natural Language ATC - Configuration")
        self.root.geometry("600x500")
        
        self.dcs_path = None
        self.model_choice = "fast"
        self.ptt_key = "RCtrl+RShift"
        
        self.create_widgets()
    
    def create_widgets(self):
        # Welcome page
        tk.Label(self.root, text="Welcome to DCS Natural Language ATC", 
                font=("Arial", 16, "bold")).pack(pady=20)
        
        tk.Label(self.root, text="This wizard will configure your installation.",
                wraplength=500).pack(pady=10)
        
        # DCS Detection
        detect_frame = ttk.LabelFrame(self.root, text="DCS Installation", padding=10)
        detect_frame.pack(fill="x", padx=20, pady=10)
        
        self.dcs_label = tk.Label(detect_frame, text="Detecting DCS...")
        self.dcs_label.pack()
        
        ttk.Button(detect_frame, text="Detect DCS", 
                  command=self.detect_dcs).pack(pady=5)
        
        # Model Selection
        model_frame = ttk.LabelFrame(self.root, text="AI Model Selection", padding=10)
        model_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(model_frame, text="Choose performance profile:").pack()
        
        self.model_var = tk.StringVar(value="fast")
        for key, info in MODEL_OPTIONS.items():
            ttk.Radiobutton(model_frame, 
                          text=f"{key.title()}: {info['name']} ({info['vram']} VRAM, {info['latency']} latency)",
                          variable=self.model_var, 
                          value=key).pack(anchor="w")
        
        # PTT Configuration
        ptt_frame = ttk.LabelFrame(self.root, text="Push-to-Talk", padding=10)
        ptt_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(ptt_frame, text="PTT Key Combination:").pack()
        self.ptt_entry = ttk.Entry(ptt_frame, width=30)
        self.ptt_entry.insert(0, self.ptt_key)
        self.ptt_entry.pack(pady=5)
        
        ttk.Button(ptt_frame, text="Record PTT", 
                  command=self.record_ptt).pack()
        
        # Action buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(side="bottom", pady=20)
        
        ttk.Button(button_frame, text="Cancel", 
                  command=self.root.quit).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Finish", 
                  command=self.finish_setup).pack(side="right", padx=5)
    
    def detect_dcs(self):
        dcs_info = DCSPathDetector.get_primary_dcs_path()
        if dcs_info:
            self.dcs_path = dcs_info["path"]
            self.dcs_label.config(text=f"DCS found: {dcs_info['name']}\n{self.dcs_path}")
        else:
            self.dcs_label.config(text="DCS not found. Please install DCS World first.")
            messagebox.showerror("DCS Not Found", 
                               "Could not detect DCS installation.\nPlease install DCS World before continuing.")
    
    def record_ptt(self):
        # Implement PTT key recording
        messagebox.showinfo("Record PTT", "Press your desired PTT key combination...")
        # TODO: Implement key capture
    
    def finish_setup(self):
        if not self.dcs_path:
            messagebox.showerror("Configuration Incomplete", 
                               "Please detect your DCS installation first.")
            return
        
        # Save configuration
        config = {
            "dcs_path": str(self.dcs_path),
            "model": self.model_var.get(),
            "ptt_key": self.ptt_entry.get()
        }
        
        # Install DCS hooks
        injector = ExportLuaInjector(self.dcs_path / "Scripts")
        if not injector.inject_atc_code():
            messagebox.showerror("Installation Failed", 
                               "Could not inject DCS export code.")
            return
        
        # Download model
        ollama_mgr = OllamaManager()
        ollama_mgr.model_name = MODEL_OPTIONS[self.model_var.get()]["name"]
        if not ollama_mgr.ensure_model():
            messagebox.showwarning("Model Download", 
                                 "Model download will continue in background.")
        
        messagebox.showinfo("Setup Complete", 
                          "DCS Natural Language ATC is configured!\nLaunch the application to begin.")
        self.root.quit()
    
    def run(self):
        self.detect_dcs()  # Auto-detect on start
        self.root.mainloop()
```

---

## 4. Multiplayer Server Architecture (Post-MVP)

### Server-Side Voice Processing

**Architecture Overview:**
```
┌──────────────────────────────────────────────────────┐
│              DCS Multiplayer Server                   │
│                                                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐    │
│  │  Player 1  │  │  Player 2  │  │  Player N  │    │
│  │  (Client)  │  │  (Client)  │  │  (Client)  │    │
│  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘    │
│         │                │                │          │
│         └────────────────┴────────────────┘          │
│                          │                           │
│                          ▼                           │
│              ┌─────────────────────┐                │
│              │   SRS Server        │                │
│              │  (Radio Comms)      │                │
│              └──────────┬──────────┘                │
└─────────────────────────┼───────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  ATC Server Plugin     │
              │  (Centralized Voice)   │
              │                        │
              │  ┌──────────────────┐ │
              │  │ STT (Whisper)    │ │
              │  ├──────────────────┤ │
              │  │ Ollama LLM       │ │
              │  ├──────────────────┤ │
              │  │ TTS (Coqui)      │ │
              │  └──────────────────┘ │
              └───────────┬────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Mission Scripting API │
              └───────────────────────┘
```

### Server Plugin Architecture

```python
class ATCServerPlugin:
    """Centralized ATC processing for multiplayer servers"""
    
    def __init__(self, srs_host, srs_port=5002):
        self.srs_host = srs_host
        self.srs_port = srs_port
        self.active_players = {}
        self.frequency_map = {}  # freq -> [player_ids]
        
        # Initialize voice processing
        self.stt_engine = WhisperSTT()
        self.ollama = OllamaManager()
        self.tts_engine = CoquiTTS()
        
    def start(self):
        """Start server plugin"""
        # Connect to SRS server
        self.srs_client = SRSClient(self.srs_host, self.srs_port)
        self.srs_client.on_transmission = self.handle_transmission
        self.srs_client.connect()
        
        # Start Ollama
        self.ollama.start_ollama()
        self.ollama.ensure_model()
        
        print("ATC Server Plugin started")
    
    def handle_transmission(self, transmission):
        """Process incoming radio transmission from player"""
        player_id = transmission['player_id']
        frequency = transmission['frequency']
        audio_data = transmission['audio']
        
        # Check if this is a player (not AI)
        if not self.is_player_controlled(player_id):
            return  # Ignore AI transmissions
        
        # Speech-to-text
        text = self.stt_engine.transcribe(audio_data)
        
        if not text:
            return
        
        print(f"Player {player_id} on {frequency}: {text}")
        
        # Get player context
        context = self.get_player_context(player_id)
        
        # Process with Ollama
        response_text = self.process_atc_request(text, context, frequency)
        
        if response_text:
            # Generate TTS
            audio_response = self.tts_engine.synthesize(response_text)
            
            # Transmit on frequency
            self.srs_client.transmit(
                frequency=frequency,
                audio=audio_response,
                sender="ATC"
            )
    
    def is_player_controlled(self, unit_id):
        """Check if unit is player-controlled vs AI"""
        # Query DCS export data or mission scripting
        return unit_id in self.active_players
    
    def process_atc_request(self, text, context, frequency):
        """Use Ollama to generate appropriate ATC response"""
        import ollama
        
        prompt = f"""You are an Air Traffic Controller. 
Player callsign: {context['callsign']}
Aircraft type: {context['aircraft']}
Position: {context['position']}
Frequency: {frequency}

Player transmission: "{text}"

Respond with correct US military ATC phraseology. Be concise."""
        
        response = ollama.chat(
            model=self.ollama.model_name,
            messages=[{'role': 'user', 'content': prompt}]
        )
        
        return response['message']['content']
```

### Frequency-Based Processing

```python
class FrequencyManager:
    """Manage which players are on which frequencies"""
    
    def __init__(self):
        self.frequencies = {}  # freq -> {player_id: last_seen}
        self.atc_frequencies = {
            "251.0": "Tower",
            "249.5": "Ground",
            "253.0": "Approach"
        }
    
    def update_player_frequency(self, player_id, frequency):
        """Track which frequency player is tuned to"""
        # Remove from old frequencies
        for freq in list(self.frequencies.keys()):
            if player_id in self.frequencies[freq]:
                del self.frequencies[freq][player_id]
        
        # Add to new frequency
        if frequency not in self.frequencies:
            self.frequencies[frequency] = {}
        
        self.frequencies[frequency][player_id] = time.time()
    
    def get_players_on_frequency(self, frequency):
        """Get all players currently on a frequency"""
        if frequency not in self.frequencies:
            return []
        
        # Clean up stale entries (>30 seconds)
        now = time.time()
        stale = [pid for pid, last_seen in self.frequencies[frequency].items() 
                 if now - last_seen > 30]
        for pid in stale:
            del self.frequencies[frequency][pid]
        
        return list(self.frequencies[frequency].keys())
```

---

## 5. Complete Deployment Workflow

### Build and Package Process

```bash
# build.sh - Complete build script

#!/bin/bash

echo "Building DCS Natural Language ATC..."

# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 2. Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# 3. Build executable with PyInstaller
pyinstaller build_spec.py --clean

# 4. Copy additional files
cp -r config dist/
cp -r templates dist/
cp README.md dist/
cp LICENSE dist/

# 5. Create Inno Setup installer (Windows only)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
fi

echo "Build complete! Installer: dist/DCS_NL_ATC_Setup.exe"
```

### Installation Workflow

**User Experience:**
1. Download `DCS_NL_ATC_Setup.exe`
2. Run installer (requires admin)
3. Installer checks for Ollama, offers to install if missing
4. Configuration wizard auto-detects DCS
5. User selects AI model performance level
6. User configures PTT key
7. Installer injects Export.lua hooks
8. Model downloads in background
9. Desktop shortcut created
10. User launches application

**First Launch:**
1. Application checks Ollama status
2. Starts Ollama server if not running
3. Ensures model is downloaded
4. Connects to DCS via Export.lua
5. Displays system tray icon
6. Ready for use

---

## 6. Implementation Checklist

### MVP Phase (Single-Player)
- [ ] Ollama auto-launch and management
- [ ] DCS path detection and Export.lua injection
- [ ] Local STT (Whisper or cloud service)
- [ ] Ollama-based NLP for intent parsing
- [ ] Local TTS with radio effects (Piper/Coqui)
- [ ] Mission script template generation
- [ ] Configuration wizard GUI
- [ ] PyInstaller executable creation
- [ ] Inno Setup installer
- [ ] Documentation and README

### Post-MVP Phase (Multiplayer)
- [ ] SRS server integration
- [ ] Centralized server plugin architecture
- [ ] Multi-player frequency management
- [ ] Player vs AI detection
- [ ] Server-side voice processing
- [ ] Distributed ATC state management
- [ ] Admin web interface for servers
- [ ] Docker containerization for servers

---

## 7. Key Implementation Notes

### Performance Considerations

**Ollama Model Loading:**
- First inference takes 2-5 seconds (model load)
- Subsequent inferences: 200-500ms
- Keep Ollama running as background service
- Pre-warm model on application start

**Memory Requirements:**
- 3B model: ~4GB VRAM + 2GB RAM
- 8B model: ~8GB VRAM + 4GB RAM
- DCS + Ollama simultaneously = 16GB RAM recommended

### Error Handling

```python
class RobustOllamaManager(OllamaManager):
    def safe_chat(self, prompt, max_retries=3):
        """Chat with automatic retry and fallback"""
        for attempt in range(max_retries):
            try:
                import ollama
                response = ollama.chat(
                    model=self.model_name,
                    messages=[{'role': 'user', 'content': prompt}],
                    options={'timeout': 10}
                )
                return response['message']['content']
            except Exception as e:
                print(f"Ollama error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    # Fallback to rule-based response
                    return self.fallback_response(prompt)
        
    def fallback_response(self, prompt):
        """Simple rule-based fallback when Ollama fails"""
        if "takeoff" in prompt.lower():
            return "Cleared for takeoff"
        elif "land" in prompt.lower():
            return "Cleared to land"
        else:
            return "Roger"
```

---

## 8. Recommended Technology Stack Summary

**Core Application:**
- **Language:** Python 3.11+
- **LLM:** Ollama (Llama 3.2 3B or Phi-3)
- **STT:** OpenAI Whisper (local or Fireworks AI cloud)
- **TTS:** Piper TTS or Coqui XTTS (local)
- **GUI:** tkinter (built-in) or PyQt6
- **Packaging:** PyInstaller + Inno Setup

**DCS Integration:**
- **Export:** Export.lua with LuaSocket
- **Radio:** SRS (Simple Radio Standalone)
- **Mission Scripts:** Lua with MOOSE framework helpers

**Infrastructure:**
- **Config:** YAML or JSON
- **Logging:** Python logging module
- **Updates:** GitHub Releases with auto-update check

---

## Conclusion

This deployment architecture provides a **truly plug-and-play experience** where users:
1. Download one installer
2. Run it with admin privileges
3. Follow a 3-step wizard
4. Launch and fly

The system handles all complexity automatically:
- Ollama installation and model management
- DCS script injection with safe backups
- Automatic configuration and path detection
- Background service management

For multiplayer, the architecture naturally extends to a centralized server-based model where one ATC server instance handles all players on a server, providing consistent, realistic ATC interactions for the entire community.

The combination of **Ollama for NLP**, **local TTS**, and **automatic installation** creates a cost-effective, privacy-respecting, performant solution that delivers authentic military aviation communications to DCS World.
