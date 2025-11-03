"""
DCS Configurator - Automatic DCS World Integration
Handles DCS path detection, Export.lua injection, and mission script generation
"""

import os
import shutil
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class DCSPathDetector:
    """
    Detects DCS World installation paths across different variants
    (stable, openbeta, custom)
    """

    def __init__(self):
        self.saved_games = self.get_saved_games_path()

    def get_saved_games_path(self) -> Path:
        """
        Get Windows Saved Games folder path

        Returns:
            Path to Saved Games folder
        """
        # Standard location
        saved_games = Path(os.path.expanduser("~")) / "Saved Games"

        # On Windows, check registry for custom Saved Games location
        if os.name == 'nt':
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
                )
                value, _ = winreg.QueryValueEx(key, "{4C5C32FF-BB9D-43b0-B5B4-2D72E54EAAA4}")
                winreg.CloseKey(key)
                saved_games = Path(os.path.expandvars(value))
            except Exception as e:
                logger.debug(f"Could not read registry for Saved Games path: {e}")

        return saved_games

    def detect_dcs_variants(self) -> List[Dict[str, Path]]:
        """
        Find all DCS installations (stable, openbeta, custom)

        Returns:
            List of dictionaries containing variant name, path, and scripts_path
        """
        variants = []

        if not self.saved_games.exists():
            logger.warning(f"Saved Games path does not exist: {self.saved_games}")
            return variants

        # Check for common variants
        for variant in ["DCS", "DCS.openbeta"]:
            path = self.saved_games / variant
            scripts_path = path / "Scripts"

            if path.exists() and scripts_path.exists():
                variants.append({
                    "name": variant,
                    "path": path,
                    "scripts_path": scripts_path
                })
                logger.info(f"Found DCS variant: {variant} at {path}")

        # Check for custom variants (DCS.*)
        try:
            for item in self.saved_games.iterdir():
                if item.is_dir() and item.name.startswith("DCS."):
                    # Skip if already found
                    if not any(v["path"] == item for v in variants):
                        scripts_path = item / "Scripts"
                        if scripts_path.exists():
                            variants.append({
                                "name": item.name,
                                "path": item,
                                "scripts_path": scripts_path
                            })
                            logger.info(f"Found custom DCS variant: {item.name}")
        except Exception as e:
            logger.error(f"Error scanning for custom DCS variants: {e}")

        return variants

    def get_primary_dcs_path(self) -> Optional[Dict[str, Path]]:
        """
        Get the most likely DCS installation to use

        Returns:
            Dictionary with DCS variant info, or None if not found
        """
        variants = self.detect_dcs_variants()

        if not variants:
            logger.warning("No DCS installations found")
            return None

        # Prefer openbeta if available
        for variant in variants:
            if "openbeta" in variant["name"].lower():
                logger.info(f"Using DCS variant: {variant['name']}")
                return variant

        # Otherwise use first found
        logger.info(f"Using DCS variant: {variants[0]['name']}")
        return variants[0]


class ExportLuaInjector:
    """
    Safely injects ATC export code into DCS Export.lua with backup
    """

    def __init__(self, scripts_path: Path):
        """
        Initialize injector

        Args:
            scripts_path: Path to DCS Scripts directory
        """
        self.scripts_path = Path(scripts_path)
        self.export_lua_path = self.scripts_path / "Export.lua"
        self.backup_suffix = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.backup_path = self.export_lua_path.with_suffix(f".lua.{self.backup_suffix}")

    def create_backup(self) -> bool:
        """
        Create timestamped backup of Export.lua

        Returns:
            True if backup created, False if Export.lua doesn't exist
        """
        if not self.export_lua_path.exists():
            logger.info("Export.lua does not exist, no backup needed")
            return False

        try:
            shutil.copy2(self.export_lua_path, self.backup_path)
            logger.info(f"Backup created: {self.backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise

    def inject_atc_code(self) -> bool:
        """
        Safely inject ATC export code into Export.lua

        Returns:
            True if successful, False otherwise
        """
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
    pcall(function()
        local json_str = "{\\"type\\":\\"export\\",\\"time\\":" .. tostring(data.time) ..
                         ",\\"pilot\\":\\"" .. tostring(data.pilot or "") .. "\\"}\\n"
        atc_socket:send(json_str)
    end)
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
                    logger.info("ATC code already present in Export.lua")
                    return True

                # Create backup
                self.create_backup()
            else:
                content = ""
                # Ensure Scripts directory exists
                self.scripts_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created Scripts directory: {self.scripts_path}")

            # Write with ATC code appended
            with open(self.export_lua_path, 'w', encoding='utf-8') as f:
                f.write(content)
                f.write("\n\n")
                f.write(atc_export_code)

            logger.info("ATC export code injected successfully")
            return True

        except Exception as e:
            logger.error(f"Error injecting ATC code: {e}")

            # Restore backup if available
            if self.backup_path.exists():
                try:
                    shutil.copy2(self.backup_path, self.export_lua_path)
                    logger.info("Backup restored after error")
                except Exception as restore_error:
                    logger.error(f"Failed to restore backup: {restore_error}")

            return False

    def remove_atc_code(self) -> bool:
        """
        Remove ATC code from Export.lua

        Returns:
            True if successful, False otherwise
        """
        if not self.export_lua_path.exists():
            logger.info("Export.lua does not exist, nothing to remove")
            return True

        try:
            with open(self.export_lua_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Remove ATC section using regex
            pattern = r'\n*-- ========== DCS Natural Language ATC Plugin ==========.*?-- ========== End DCS Natural Language ATC Plugin ==========\n*'
            new_content = re.sub(pattern, '', content, flags=re.DOTALL)

            if new_content != content:
                # Create backup before removing
                self.create_backup()

                with open(self.export_lua_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                logger.info("ATC code removed from Export.lua")
            else:
                logger.info("No ATC code found to remove")

            return True

        except Exception as e:
            logger.error(f"Error removing ATC code: {e}")
            return False

    def validate_injection(self) -> bool:
        """
        Validate that ATC code is properly injected

        Returns:
            True if ATC code is present and valid
        """
        if not self.export_lua_path.exists():
            return False

        try:
            with open(self.export_lua_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for key components
            checks = [
                "DCS Natural Language ATC Plugin" in content,
                "atc_socket" in content,
                "atc_init" in content,
                "LuaExportStart" in content,
                "LuaExportAfterNextFrame" in content
            ]

            return all(checks)

        except Exception as e:
            logger.error(f"Error validating injection: {e}")
            return False


class MissionScriptGenerator:
    """
    Generates Lua mission scripts for ATC functionality
    """

    @staticmethod
    def generate_atc_mission_script() -> str:
        """
        Generate Lua mission script for ATC functionality

        Returns:
            Complete Lua script as string
        """
        return '''-- DCS Natural Language ATC Mission Script
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
    def save_mission_template(output_path: Path) -> bool:
        """
        Save mission script template to file

        Args:
            output_path: Path where to save the script

        Returns:
            True if successful, False otherwise
        """
        try:
            template = MissionScriptGenerator.generate_atc_mission_script()
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(template)

            logger.info(f"Mission script template saved to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving mission template: {e}")
            return False


class DCSConfigurator:
    """
    Main configurator that orchestrates DCS integration setup
    """

    def __init__(self):
        """Initialize DCS configurator"""
        self.detector = DCSPathDetector()
        self.dcs_info: Optional[Dict[str, Path]] = None
        self.injector: Optional[ExportLuaInjector] = None

    def detect_dcs(self) -> Optional[Dict[str, Path]]:
        """
        Detect DCS installation

        Returns:
            DCS installation info or None if not found
        """
        self.dcs_info = self.detector.get_primary_dcs_path()
        return self.dcs_info

    def configure(self, dcs_path: Optional[Path] = None) -> bool:
        """
        Perform full DCS configuration

        Args:
            dcs_path: Optional manual DCS path (auto-detect if None)

        Returns:
            True if configuration successful, False otherwise
        """
        # Detect or use provided DCS path
        if dcs_path:
            scripts_path = dcs_path / "Scripts"
            self.dcs_info = {
                "name": "Custom",
                "path": dcs_path,
                "scripts_path": scripts_path
            }
        else:
            if not self.detect_dcs():
                logger.error("Could not detect DCS installation")
                return False

        # Create injector
        self.injector = ExportLuaInjector(self.dcs_info["scripts_path"])

        # Inject ATC code
        if not self.injector.inject_atc_code():
            logger.error("Failed to inject ATC code")
            return False

        # Validate injection
        if not self.injector.validate_injection():
            logger.error("Injection validation failed")
            return False

        logger.info("DCS configuration completed successfully")
        return True

    def unconfigure(self) -> bool:
        """
        Remove ATC integration from DCS

        Returns:
            True if successful, False otherwise
        """
        if not self.injector:
            if not self.detect_dcs():
                logger.error("Could not detect DCS installation")
                return False
            self.injector = ExportLuaInjector(self.dcs_info["scripts_path"])

        return self.injector.remove_atc_code()

    def get_status(self) -> Dict[str, any]:
        """
        Get current configuration status

        Returns:
            Dictionary with configuration status
        """
        status = {
            "dcs_detected": self.dcs_info is not None,
            "dcs_path": str(self.dcs_info["path"]) if self.dcs_info else None,
            "dcs_variant": self.dcs_info["name"] if self.dcs_info else None,
            "atc_configured": False
        }

        if self.dcs_info:
            injector = ExportLuaInjector(self.dcs_info["scripts_path"])
            status["atc_configured"] = injector.validate_injection()

        return status
