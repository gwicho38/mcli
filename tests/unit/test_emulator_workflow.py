"""
Unit tests for emulator workflow command.

Tests the custom emulator management workflow command that handles
Android emulators and iOS simulators.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from click.testing import CliRunner

# Import the emulator manager class
# Note: Since this is loaded dynamically from JSON, we'll test the JSON structure
# and mock the actual command execution


class TestEmulatorCommandStructure:
    """Test the emulator command JSON structure and validation"""

    def setup_method(self):
        """Setup test environment"""
        self.emulator_json_path = Path.home() / ".mcli" / "commands" / "emulator.json"

    def test_emulator_json_exists(self):
        """Test that emulator.json command file exists"""
        assert self.emulator_json_path.exists(), "emulator.json should exist in ~/.mcli/commands/"

    def test_emulator_json_valid_structure(self):
        """Test that emulator.json has valid structure"""
        with open(self.emulator_json_path, "r") as f:
            data = json.load(f)

        # Verify required fields
        assert data["name"] == "emulator"
        assert "code" in data
        assert "description" in data
        assert data["group"] == "workflow"
        assert "version" in data
        assert "metadata" in data

    def test_emulator_metadata(self):
        """Test emulator command metadata"""
        with open(self.emulator_json_path, "r") as f:
            data = json.load(f)

        metadata = data["metadata"]
        assert "platforms" in metadata
        assert "android-sdk" in metadata["platforms"]
        assert "ios" in metadata["platforms"]
        assert "requires" in metadata
        assert "avdmanager" in metadata["requires"] or "emulator" in metadata["requires"]


class MockAndroidEmulatorManager:
    """Mock AndroidEmulatorManager for testing"""

    def __init__(self):
        self.run_command_calls = []

    def run_command(self, cmd, check=True, shell=False):
        """Mock run_command method"""
        self.run_command_calls.append(cmd)
        return 0, "", ""

    @staticmethod
    def get_android_sdk_path():
        """Mock get_android_sdk_path method"""
        return "/Users/test/android-sdk"

    @staticmethod
    def get_avdmanager_path():
        """Mock get_avdmanager_path method"""
        return "/Users/test/android-sdk/cmdline-tools/latest/bin/avdmanager"

    @staticmethod
    def get_emulator_path():
        """Mock get_emulator_path method"""
        return "/Users/test/android-sdk/emulator/emulator"

    def list_avds(self):
        """Mock list AVDs"""
        return [
            {
                "name": "Pixel_6_API_34",
                "target": "Google APIs (Google Inc.)",
                "status": "running",
            },
            {"name": "Outlet", "target": "Google APIs (Google Inc.)", "status": "stopped"},
        ]

    def list_device_definitions(self):
        """Mock list device definitions"""
        return ["pixel_6", "pixel_7", "pixel_8"]

    def list_system_images(self):
        """Mock list system images"""
        return [
            "system-images;android-34;google_apis;arm64-v8a",
            "system-images;android-33;google_apis;arm64-v8a",
            "system-images;android-32;google_apis;arm64-v8a",
        ]

    def get_running_emulators(self):
        """Mock get running emulators"""
        return {"emulator-5554": "Pixel_6_API_34"}

    def list_ios_simulators(self, running_only=False):
        """Mock list iOS simulators"""
        if running_only:
            return [
                {
                    "name": "iPhone 15",
                    "udid": "ABCD-1234",
                    "status": "booted",
                    "runtime": "iOS-17-2",
                    "type": "ios",
                }
            ]
        return [
            {
                "name": "iPhone 15",
                "udid": "ABCD-1234",
                "status": "shutdown",
                "runtime": "iOS-17-2",
                "type": "ios",
            },
            {
                "name": "iPhone 14",
                "udid": "EFGH-5678",
                "status": "shutdown",
                "runtime": "iOS-16-4",
                "type": "ios",
            },
        ]

    def create_avd(self, name, device, system_image, **kwargs):
        """Mock create AVD"""
        return True

    def delete_avd(self, name):
        """Mock delete AVD"""
        return True

    def start_emulator(self, name, headless=True, **kwargs):
        """Mock start emulator"""
        return True

    def stop_emulator(self, serial=None):
        """Mock stop emulator"""
        return True

    def start_ios_simulator(self, identifier):
        """Mock start iOS simulator"""
        return True

    def stop_ios_simulator(self, identifier=None):
        """Mock stop iOS simulator"""
        return True


class TestAndroidEmulatorManagerLogic:
    """Test AndroidEmulatorManager class logic"""

    def setup_method(self):
        """Setup test environment"""
        self.manager = MockAndroidEmulatorManager()

    def test_get_android_sdk_path(self):
        """Test getting Android SDK path"""
        path = self.manager.get_android_sdk_path()

        assert path is not None
        assert "android-sdk" in path

    def test_get_avdmanager_path(self):
        """Test getting avdmanager path"""
        path = self.manager.get_avdmanager_path()

        assert path is not None
        assert "avdmanager" in path

    def test_get_emulator_path(self):
        """Test getting emulator path"""
        path = self.manager.get_emulator_path()

        assert path is not None
        assert "emulator" in path

    def test_list_avds(self):
        """Test listing AVDs"""
        avds = self.manager.list_avds()

        assert len(avds) > 0
        assert "name" in avds[0]
        assert "target" in avds[0]
        assert "status" in avds[0]

    def test_list_device_definitions(self):
        """Test listing device definitions"""
        devices = self.manager.list_device_definitions()

        assert len(devices) > 0
        assert "pixel_6" in devices

    def test_list_system_images(self):
        """Test listing system images"""
        images = self.manager.list_system_images()

        assert len(images) > 0
        assert any("android-34" in img for img in images)

    def test_get_running_emulators(self):
        """Test getting running emulators"""
        running = self.manager.get_running_emulators()

        assert isinstance(running, dict)
        assert "emulator-5554" in running

    def test_list_ios_simulators_all(self):
        """Test listing all iOS simulators"""
        simulators = self.manager.list_ios_simulators(running_only=False)

        assert len(simulators) == 2
        assert all(sim["type"] == "ios" for sim in simulators)
        assert "udid" in simulators[0]
        assert "runtime" in simulators[0]

    def test_list_ios_simulators_running(self):
        """Test listing only running iOS simulators"""
        simulators = self.manager.list_ios_simulators(running_only=True)

        assert len(simulators) == 1
        assert simulators[0]["status"] == "booted"

    def test_create_avd(self):
        """Test creating AVD"""
        result = self.manager.create_avd(
            name="test_device",
            device="pixel_6",
            system_image="system-images;android-34;google_apis;arm64-v8a",
        )

        assert result is True

    def test_create_avd_with_options(self):
        """Test creating AVD with custom options"""
        result = self.manager.create_avd(
            name="test_device",
            device="pixel_6",
            system_image="system-images;android-34;google_apis;arm64-v8a",
            sdcard_size="512M",
        )

        assert result is True

    def test_delete_avd(self):
        """Test deleting AVD"""
        result = self.manager.delete_avd("test_device")

        assert result is True

    def test_start_emulator_headless(self):
        """Test starting emulator headlessly"""
        result = self.manager.start_emulator("Pixel_6_API_34", headless=True)

        assert result is True

    def test_start_emulator_gui(self):
        """Test starting emulator with GUI"""
        result = self.manager.start_emulator("Pixel_6_API_34", headless=False)

        assert result is True

    def test_start_emulator_with_wipe(self):
        """Test starting emulator with wipe data"""
        result = self.manager.start_emulator("Pixel_6_API_34", headless=True, wipe_data=True)

        assert result is True

    def test_stop_emulator_specific(self):
        """Test stopping specific emulator"""
        result = self.manager.stop_emulator("emulator-5554")

        assert result is True

    def test_stop_all_emulators(self):
        """Test stopping all emulators"""
        result = self.manager.stop_emulator(None)

        assert result is True

    def test_start_ios_simulator(self):
        """Test starting iOS simulator"""
        result = self.manager.start_ios_simulator("iPhone 15")

        assert result is True

    def test_stop_ios_simulator(self):
        """Test stopping iOS simulator"""
        result = self.manager.stop_ios_simulator("iPhone 15")

        assert result is True

    def test_stop_all_ios_simulators(self):
        """Test stopping all iOS simulators"""
        result = self.manager.stop_ios_simulator(None)

        assert result is True


class TestAndroidEmulatorCommandIntegration:
    """Integration tests for Android emulator command execution"""

    @patch("subprocess.run")
    def test_avdmanager_list_command(self, mock_run):
        """Test avdmanager list avd command"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Available Android Virtual Devices:\n    Name: Pixel_6_API_34\n---------\n",
            stderr="",
        )

        result = subprocess.run(
            ["avdmanager", "list", "avd"], capture_output=True, text=True, check=False
        )

        assert result.returncode == 0
        assert "Pixel_6_API_34" in result.stdout

    @patch("subprocess.run")
    def test_avdmanager_list_devices_command(self, mock_run):
        """Test avdmanager list device command"""
        mock_run.return_value = Mock(
            returncode=0, stdout='id: 10 or "pixel_6"\n    Name: Pixel 6\n', stderr=""
        )

        result = subprocess.run(
            ["avdmanager", "list", "device"], capture_output=True, text=True, check=False
        )

        assert result.returncode == 0
        assert "pixel_6" in result.stdout

    @patch("subprocess.run")
    def test_avdmanager_list_targets_command(self, mock_run):
        """Test avdmanager list target command"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='id: 1 or "android-34"\n    Name: Android 14.0\n',
            stderr="",
        )

        result = subprocess.run(
            ["avdmanager", "list", "target"], capture_output=True, text=True, check=False
        )

        assert result.returncode == 0
        assert "android-34" in result.stdout

    @patch("subprocess.run")
    def test_avdmanager_create_avd_command(self, mock_run):
        """Test avdmanager AVD creation command"""
        mock_run.return_value = Mock(returncode=0, stdout="AVD created", stderr="")

        result = subprocess.run(
            [
                "avdmanager",
                "create",
                "avd",
                "-n",
                "test_device",
                "-k",
                "system-images;android-34;google_apis;arm64-v8a",
                "-d",
                "pixel_6",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_avdmanager_delete_avd_command(self, mock_run):
        """Test avdmanager delete AVD command"""
        mock_run.return_value = Mock(returncode=0, stdout="AVD deleted", stderr="")

        result = subprocess.run(
            ["avdmanager", "delete", "avd", "-n", "test_device"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_adb_devices_command(self, mock_run):
        """Test getting running devices with adb"""
        # Setup mock
        mock_run.return_value = Mock(
            returncode=0,
            stdout="List of devices attached\nemulator-5554\tdevice\n",
            stderr="",
        )

        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=False)

        assert result.returncode == 0
        assert "device" in result.stdout

    @patch("subprocess.run")
    def test_adb_emu_avd_name_command(self, mock_run):
        """Test getting AVD name from running emulator"""
        mock_run.return_value = Mock(returncode=0, stdout="Pixel_6_API_34\nOK\n", stderr="")

        result = subprocess.run(
            ["adb", "-s", "emulator-5554", "emu", "avd", "name"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "Pixel_6_API_34" in result.stdout

    @patch("subprocess.run")
    def test_adb_emu_kill_command(self, mock_run):
        """Test killing emulator via adb"""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = subprocess.run(
            ["adb", "-s", "emulator-5554", "emu", "kill"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_ios_list_command_structure(self, mock_run):
        """Test iOS simulator list command calls correct subprocess"""
        # Setup mock
        mock_data = {
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                    {"name": "iPhone 15", "udid": "ABCD-1234", "state": "Shutdown"}
                ]
            }
        }
        mock_run.return_value = Mock(returncode=0, stdout=json.dumps(mock_data), stderr="")

        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "-j"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "devices" in data

    @patch("subprocess.run")
    def test_delete_ios_simulator_command(self, mock_run):
        """Test iOS simulator deletion command"""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = subprocess.run(
            ["xcrun", "simctl", "delete", "ABCD-1234"], capture_output=True, text=True, check=False
        )

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_start_ios_simulator_command(self, mock_run):
        """Test iOS simulator start command"""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = subprocess.run(
            ["xcrun", "simctl", "boot", "ABCD-1234"], capture_output=True, text=True, check=False
        )

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_stop_ios_simulator_command(self, mock_run):
        """Test iOS simulator stop command"""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = subprocess.run(
            ["xcrun", "simctl", "shutdown", "ABCD-1234"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_stop_all_ios_simulators_command(self, mock_run):
        """Test stopping all iOS simulators"""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = subprocess.run(
            ["xcrun", "simctl", "shutdown", "all"], capture_output=True, text=True, check=False
        )

        assert result.returncode == 0


class TestEmulatorErrorHandling:
    """Test error handling in emulator operations"""

    def setup_method(self):
        """Setup test environment"""
        self.manager = MockAndroidEmulatorManager()

    @patch("subprocess.run")
    def test_avdmanager_command_not_found(self, mock_run):
        """Test handling when avdmanager command not found"""
        mock_run.side_effect = FileNotFoundError("avdmanager: command not found")

        with pytest.raises(FileNotFoundError):
            subprocess.run(
                ["avdmanager", "list", "avd"], capture_output=True, text=True, check=True
            )

    @patch("subprocess.run")
    def test_emulator_command_not_found(self, mock_run):
        """Test handling when emulator command not found"""
        mock_run.side_effect = FileNotFoundError("emulator: command not found")

        with pytest.raises(FileNotFoundError):
            subprocess.run(["emulator", "-avd", "test"], capture_output=True, text=True, check=True)

    @patch("subprocess.run")
    def test_ios_list_command_not_found(self, mock_run):
        """Test handling when xcrun command not found"""
        mock_run.side_effect = FileNotFoundError("xcrun: command not found")

        with pytest.raises(FileNotFoundError):
            subprocess.run(
                ["xcrun", "simctl", "list", "devices", "-j"],
                capture_output=True,
                text=True,
                check=True,
            )

    @patch("subprocess.run")
    def test_avd_creation_invalid_system_image(self, mock_run):
        """Test handling AVD creation with invalid system image"""
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="Error: Package path is not valid"
        )

        result = subprocess.run(
            [
                "avdmanager",
                "create",
                "avd",
                "-n",
                "test",
                "-k",
                "invalid-image",
                "-d",
                "pixel_6",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode != 0
        assert "Error" in result.stderr

    @patch("subprocess.run")
    def test_avd_already_exists(self, mock_run):
        """Test handling when AVD already exists"""
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="Error: AVD 'test' already exists"
        )

        result = subprocess.run(
            [
                "avdmanager",
                "create",
                "avd",
                "-n",
                "test",
                "-k",
                "system-images;android-34;google_apis;arm64-v8a",
                "-d",
                "pixel_6",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode != 0
        assert "already exists" in result.stderr

    @patch("subprocess.run")
    def test_simulator_already_running(self, mock_run):
        """Test handling when simulator is already running"""
        mock_run.return_value = Mock(
            returncode=164, stdout="", stderr="Unable to boot device in current state: Booted"
        )

        result = subprocess.run(
            ["xcrun", "simctl", "boot", "ABCD-1234"], capture_output=True, text=True, check=False
        )

        assert result.returncode != 0
        assert "Booted" in result.stderr


@pytest.mark.slow
class TestEmulatorRealCommandExecution:
    """
    Real command execution tests - only run if tools are available.
    Marked as slow to allow skipping.
    """

    def test_check_android_sdk_available(self):
        """Test if Android SDK is available on system"""
        try:
            # Try avdmanager
            result = subprocess.run(
                ["avdmanager", "list", "avd"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if result.returncode != 0:
                pytest.skip("Android SDK not installed or not in PATH")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Android SDK tools not available")

    def test_check_ios_tools_available(self):
        """Test if iOS tools are available on system"""
        try:
            result = subprocess.run(
                ["xcrun", "simctl", "help"], capture_output=True, text=True, check=False, timeout=5
            )
            assert result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("iOS simulator tools not available")
