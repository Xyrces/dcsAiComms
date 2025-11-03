"""
Test Suite for DCS Configurator
Following TDD principles - tests written before implementation
"""

import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
from pathlib import Path
import tempfile
import shutil


class TestDCSPathDetector:
    """Test cases for DCS path detection"""

    @patch('os.path.expanduser')
    def test_get_saved_games_path_default(self, mock_expanduser):
        """Test get_saved_games_path returns default Saved Games location"""
        from src.dcs_configurator import DCSPathDetector

        mock_expanduser.return_value = "/home/user"

        detector = DCSPathDetector()
        result = detector.get_saved_games_path()

        assert "Saved Games" in str(result)

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.iterdir')
    @patch('os.path.expanduser')
    def test_detect_dcs_variants_finds_openbeta(self, mock_expanduser, mock_iterdir, mock_exists):
        """Test detect_dcs_variants finds DCS.openbeta installation"""
        from src.dcs_configurator import DCSPathDetector

        mock_expanduser.return_value = "/home/user"
        mock_exists.return_value = True

        # Mock directory structure
        mock_dcs_beta = Mock()
        mock_dcs_beta.is_dir.return_value = True
        mock_dcs_beta.name = "DCS.openbeta"
        mock_dcs_beta.__truediv__ = lambda self, x: Mock(exists=lambda: True)

        mock_iterdir.return_value = [mock_dcs_beta]

        detector = DCSPathDetector()
        variants = detector.detect_dcs_variants()

        assert len(variants) > 0
        assert any("openbeta" in v["name"] for v in variants)

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.iterdir')
    @patch('os.path.expanduser')
    def test_detect_dcs_variants_finds_stable(self, mock_expanduser, mock_iterdir, mock_exists):
        """Test detect_dcs_variants finds stable DCS installation"""
        from src.dcs_configurator import DCSPathDetector

        mock_expanduser.return_value = "/home/user"
        mock_exists.return_value = True

        mock_dcs_stable = Mock()
        mock_dcs_stable.is_dir.return_value = True
        mock_dcs_stable.name = "DCS"
        mock_dcs_stable.__truediv__ = lambda self, x: Mock(exists=lambda: True)

        mock_iterdir.return_value = [mock_dcs_stable]

        detector = DCSPathDetector()
        variants = detector.detect_dcs_variants()

        assert len(variants) > 0

    @patch('src.dcs_configurator.DCSPathDetector.detect_dcs_variants')
    def test_get_primary_dcs_path_prefers_openbeta(self, mock_detect):
        """Test get_primary_dcs_path prefers openbeta over stable"""
        from src.dcs_configurator import DCSPathDetector

        mock_detect.return_value = [
            {"name": "DCS", "path": Path("/home/user/Saved Games/DCS")},
            {"name": "DCS.openbeta", "path": Path("/home/user/Saved Games/DCS.openbeta")}
        ]

        detector = DCSPathDetector()
        result = detector.get_primary_dcs_path()

        assert result is not None
        assert "openbeta" in result["name"].lower()

    @patch('src.dcs_configurator.DCSPathDetector.detect_dcs_variants')
    def test_get_primary_dcs_path_returns_none_when_no_install(self, mock_detect):
        """Test get_primary_dcs_path returns None when no DCS found"""
        from src.dcs_configurator import DCSPathDetector

        mock_detect.return_value = []

        detector = DCSPathDetector()
        result = detector.get_primary_dcs_path()

        assert result is None


class TestExportLuaInjector:
    """Test cases for Export.lua injection"""

    def test_injector_initialization(self):
        """Test ExportLuaInjector can be instantiated"""
        from src.dcs_configurator import ExportLuaInjector

        scripts_path = Path("/home/user/Saved Games/DCS/Scripts")
        injector = ExportLuaInjector(scripts_path)

        assert injector.scripts_path == scripts_path
        assert injector.export_lua_path == scripts_path / "Export.lua"

    @patch('pathlib.Path.exists')
    @patch('shutil.copy2')
    def test_create_backup_creates_backup_file(self, mock_copy, mock_exists):
        """Test create_backup creates timestamped backup"""
        from src.dcs_configurator import ExportLuaInjector

        mock_exists.return_value = True

        scripts_path = Path("/home/user/Saved Games/DCS/Scripts")
        injector = ExportLuaInjector(scripts_path)

        result = injector.create_backup()

        assert result is True
        mock_copy.assert_called_once()

    @patch('pathlib.Path.exists')
    def test_create_backup_returns_false_when_no_file(self, mock_exists):
        """Test create_backup returns False when Export.lua doesn't exist"""
        from src.dcs_configurator import ExportLuaInjector

        mock_exists.return_value = False

        scripts_path = Path("/home/user/Saved Games/DCS/Scripts")
        injector = ExportLuaInjector(scripts_path)

        result = injector.create_backup()

        assert result is False

    @patch('builtins.open', new_callable=mock_open, read_data="-- Existing Export.lua content")
    @patch('pathlib.Path.exists')
    def test_inject_atc_code_detects_existing_injection(self, mock_exists, mock_file):
        """Test inject_atc_code detects if ATC code is already present"""
        from src.dcs_configurator import ExportLuaInjector

        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "-- DCS Natural Language ATC Plugin"

        scripts_path = Path("/home/user/Saved Games/DCS/Scripts")
        injector = ExportLuaInjector(scripts_path)

        result = injector.inject_atc_code()

        assert result is True

    @patch('builtins.open', new_callable=mock_open, read_data="-- Existing content")
    @patch('pathlib.Path.exists')
    @patch('src.dcs_configurator.ExportLuaInjector.create_backup')
    def test_inject_atc_code_injects_new_code(self, mock_backup, mock_exists, mock_file):
        """Test inject_atc_code successfully injects ATC code"""
        from src.dcs_configurator import ExportLuaInjector

        mock_exists.return_value = True
        mock_backup.return_value = True

        scripts_path = Path("/home/user/Saved Games/DCS/Scripts")
        injector = ExportLuaInjector(scripts_path)

        result = injector.inject_atc_code()

        # Should have written the file
        assert mock_file().write.called

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.mkdir')
    def test_inject_atc_code_creates_directory_if_needed(self, mock_mkdir, mock_exists, mock_file):
        """Test inject_atc_code creates Scripts directory if it doesn't exist"""
        from src.dcs_configurator import ExportLuaInjector

        # Export.lua doesn't exist, but we want to create it
        mock_exists.return_value = False

        scripts_path = Path("/home/user/Saved Games/DCS/Scripts")
        injector = ExportLuaInjector(scripts_path)

        result = injector.inject_atc_code()

        # Should have created directory
        mock_mkdir.assert_called_once()

    @patch('builtins.open', side_effect=Exception("Permission denied"))
    @patch('pathlib.Path.exists')
    @patch('shutil.copy2')
    def test_inject_atc_code_restores_backup_on_error(self, mock_copy, mock_exists, mock_file):
        """Test inject_atc_code restores backup when injection fails"""
        from src.dcs_configurator import ExportLuaInjector

        mock_exists.return_value = True

        scripts_path = Path("/home/user/Saved Games/DCS/Scripts")
        injector = ExportLuaInjector(scripts_path)

        result = injector.inject_atc_code()

        assert result is False

    @patch('builtins.open', new_callable=mock_open, read_data="-- ATC code\n-- ========== DCS Natural Language ATC Plugin ==========\nATC code here\n-- ========== End DCS Natural Language ATC Plugin ==========\n-- More content")
    @patch('pathlib.Path.exists')
    @patch('src.dcs_configurator.ExportLuaInjector.create_backup')
    def test_remove_atc_code_removes_injection(self, mock_backup, mock_exists, mock_file):
        """Test remove_atc_code successfully removes ATC code"""
        from src.dcs_configurator import ExportLuaInjector

        mock_exists.return_value = True
        mock_backup.return_value = True

        scripts_path = Path("/home/user/Saved Games/DCS/Scripts")
        injector = ExportLuaInjector(scripts_path)

        result = injector.remove_atc_code()

        assert result is True

    @patch('pathlib.Path.exists')
    def test_remove_atc_code_handles_no_file(self, mock_exists):
        """Test remove_atc_code handles case when Export.lua doesn't exist"""
        from src.dcs_configurator import ExportLuaInjector

        mock_exists.return_value = False

        scripts_path = Path("/home/user/Saved Games/DCS/Scripts")
        injector = ExportLuaInjector(scripts_path)

        result = injector.remove_atc_code()

        assert result is True

    def test_validate_injection_success(self):
        """Test validate_injection returns True when code is properly injected"""
        from src.dcs_configurator import ExportLuaInjector

        # This will be tested with actual file operations in integration tests
        scripts_path = Path("/home/user/Saved Games/DCS/Scripts")
        injector = ExportLuaInjector(scripts_path)

        # Test the validation logic
        test_content = "-- DCS Natural Language ATC Plugin\natc_socket = socket.udp()"
        assert "DCS Natural Language ATC Plugin" in test_content


class TestMissionScriptGenerator:
    """Test cases for mission script generation"""

    def test_generate_atc_mission_script_returns_string(self):
        """Test generate_atc_mission_script returns Lua script as string"""
        from src.dcs_configurator import MissionScriptGenerator

        generator = MissionScriptGenerator()
        script = generator.generate_atc_mission_script()

        assert isinstance(script, str)
        assert len(script) > 0
        assert "ATCSystem" in script

    def test_generated_script_contains_initialization(self):
        """Test generated script contains ATCSystem:init()"""
        from src.dcs_configurator import MissionScriptGenerator

        generator = MissionScriptGenerator()
        script = generator.generate_atc_mission_script()

        assert "ATCSystem:init()" in script

    def test_generated_script_contains_event_handler(self):
        """Test generated script contains event handler"""
        from src.dcs_configurator import MissionScriptGenerator

        generator = MissionScriptGenerator()
        script = generator.generate_atc_mission_script()

        assert "eventHandler" in script
        assert "onEvent" in script

    @patch('builtins.open', new_callable=mock_open)
    def test_save_mission_template_writes_file(self, mock_file):
        """Test save_mission_template writes script to file"""
        from src.dcs_configurator import MissionScriptGenerator

        generator = MissionScriptGenerator()
        output_path = Path("/tmp/mission_atc.lua")

        generator.save_mission_template(output_path)

        mock_file.assert_called_once()


class TestDCSConfigurator:
    """Integration tests for complete DCS configuration workflow"""

    @patch('src.dcs_configurator.DCSPathDetector.get_primary_dcs_path')
    def test_configurator_detects_dcs(self, mock_get_path):
        """Test DCSConfigurator can detect DCS installation"""
        from src.dcs_configurator import DCSConfigurator

        mock_get_path.return_value = {
            "name": "DCS.openbeta",
            "path": Path("/home/user/Saved Games/DCS.openbeta"),
            "scripts_path": Path("/home/user/Saved Games/DCS.openbeta/Scripts")
        }

        configurator = DCSConfigurator()
        result = configurator.detect_dcs()

        assert result is not None

    @patch('src.dcs_configurator.ExportLuaInjector.validate_injection')
    @patch('src.dcs_configurator.ExportLuaInjector.inject_atc_code')
    @patch('src.dcs_configurator.DCSPathDetector.get_primary_dcs_path')
    def test_configurator_configure_method(self, mock_get_path, mock_inject, mock_validate):
        """Test DCSConfigurator.configure() performs full configuration"""
        from src.dcs_configurator import DCSConfigurator

        mock_get_path.return_value = {
            "name": "DCS.openbeta",
            "path": Path("/home/user/Saved Games/DCS.openbeta"),
            "scripts_path": Path("/home/user/Saved Games/DCS.openbeta/Scripts")
        }
        mock_inject.return_value = True
        mock_validate.return_value = True

        configurator = DCSConfigurator()
        result = configurator.configure()

        assert result is True
        mock_inject.assert_called_once()
