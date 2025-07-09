import pytest
import tempfile
import os
import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

# Import webapp functionality
from src.mcli.workflow.webapp.webapp import (
    webapp, get_webapps_dir, ensure_webapps_dir, generate_default_name,
    find_app_by_name, get_latest_app, get_app_info, extract_url_from_main_js,
    auto_fix_electron_installation, generate_webmail_app, generate_vector_store_app,
    generate_my_vector_store_app, install_app
)


class TestWebappUtilities:
    """Test webapp utility functions"""
    
    def test_get_webapps_dir(self):
        """Test getting webapps directory"""
        webapps_dir = get_webapps_dir()
        assert isinstance(webapps_dir, Path)
        assert webapps_dir.name == "webapps"
        assert ".local" in str(webapps_dir)
        assert "mcli" in str(webapps_dir)
    
    def test_ensure_webapps_dir(self):
        """Test ensuring webapps directory exists"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock Path.home to return our temp directory
            with patch('src.mcli.workflow.webapp.webapp.Path.home') as mock_home:
                mock_home.return_value = Path(temp_dir)
                
                webapps_dir = ensure_webapps_dir()
                assert webapps_dir.exists()
                assert webapps_dir.is_dir()
    
    def test_generate_default_name(self):
        """Test default name generation"""
        name = generate_default_name()
        assert isinstance(name, str)
        assert len(name) == 13  # YYYYMMDD.HHMM format
        assert name.count('.') == 1
        assert name[:8].isdigit()  # Date part
        assert name[9:].isdigit()  # Time part
    
    def test_find_app_by_name(self):
        """Test finding app by name"""
        with tempfile.TemporaryDirectory() as temp_dir:
            webapps_dir = Path(temp_dir) / "webapps"
            webapps_dir.mkdir(parents=True)
            
            # Create a test app
            app_dir = webapps_dir / "test-app"
            app_dir.mkdir()
            
            # Create package.json
            package_json = app_dir / "package.json"
            with open(package_json, 'w') as f:
                json.dump({
                    "name": "test-app",
                    "description": "Test app",
                    "version": "1.0.0"
                }, f)
            
            # Test finding by exact name
            found = find_app_by_name("test-app")
            assert found == app_dir
            
            # Test finding by partial name
            found = find_app_by_name("test")
            assert found == app_dir
            
            # Test not found
            found = find_app_by_name("non-existent")
            assert found is None
    
    def test_get_app_info(self):
        """Test getting app info from package.json"""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            
            # Create package.json
            package_json = app_dir / "package.json"
            with open(package_json, 'w') as f:
                json.dump({
                    "name": "test-app",
                    "description": "Test app",
                    "version": "1.0.0"
                }, f)
            
            info = get_app_info(app_dir)
            assert info['name'] == "test-app"
            assert info['description'] == "Test app"
            assert info['version'] == "1.0.0"
            assert 'created' in info
            assert 'modified' in info
    
    def test_extract_url_from_main_js(self):
        """Test extracting URL from main.js"""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            
            # Create main.js with URL
            main_js = app_dir / "main.js"
            with open(main_js, 'w') as f:
                f.write('loadURL("https://example.com")')
            
            url = extract_url_from_main_js(app_dir)
            assert url == "https://example.com"
            
            # Test with no main.js
            shutil.rmtree(app_dir)
            app_dir.mkdir()
            url = extract_url_from_main_js(app_dir)
            assert url == "Unknown"


class TestWebappGeneration:
    """Test webapp generation functionality"""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_generate_webmail_app(self, temp_output_dir):
        """Test generating webmail app"""
        # Mock template manager
        with patch('src.mcli.workflow.webapp.webapp.get_template_manager') as mock_manager:
            mock_template_dir = temp_output_dir / "template"
            mock_template_dir.mkdir()
            
            # Create template files
            (mock_template_dir / "main.js").write_text("loadURL('https://mail.google.com')")
            (mock_template_dir / "package.json").write_text('{"name": "template"}')
            (mock_template_dir / "index.html").write_text("<html></html>")
            
            mock_manager.return_value.get_template_path.return_value = mock_template_dir
            
            # Test generation
            generate_webmail_app(
                url="https://example.com",
                name="Test App",
                safe_name="test-app",
                output_path=temp_output_dir / "output",
                icon=None
            )
            
            output_dir = temp_output_dir / "output"
            assert output_dir.exists()
            assert (output_dir / "main.js").exists()
            assert (output_dir / "package.json").exists()
            assert (output_dir / "index.html").exists()
    
    def test_generate_vector_store_app(self, temp_output_dir):
        """Test generating vector store app"""
        # Mock template manager
        with patch('src.mcli.workflow.webapp.webapp.get_template_manager') as mock_manager:
            mock_template_dir = temp_output_dir / "template"
            mock_template_dir.mkdir()
            
            # Create template files
            (mock_template_dir / "package.json").write_text('{"name": "template"}')
            (mock_template_dir / "python" / "requirements.txt").write_text("numpy")
            (mock_template_dir / "install.sh").write_text("#!/bin/bash")
            
            mock_manager.return_value.get_template_path.return_value = mock_template_dir
            
            # Test generation
            generate_vector_store_app(
                name="Test App",
                safe_name="test-app",
                output_path=temp_output_dir / "output",
                icon=None
            )
            
            output_dir = temp_output_dir / "output"
            assert output_dir.exists()
            assert (output_dir / "package.json").exists()
            assert (output_dir / "python" / "requirements.txt").exists()
            assert (output_dir / "install.sh").exists()
    
    def test_generate_my_vector_store_app(self, temp_output_dir):
        """Test generating my vector store app"""
        # Mock template manager
        with patch('src.mcli.workflow.webapp.webapp.get_template_manager') as mock_manager:
            mock_template_dir = temp_output_dir / "template"
            mock_template_dir.mkdir()
            
            # Create template files
            (mock_template_dir / "package.json").write_text('{"name": "template", "dependencies": {"better-sqlite3": "^9.2.2"}}')
            (mock_template_dir / "python" / "requirements.txt").write_text("numpy")
            (mock_template_dir / "install.sh").write_text("#!/bin/bash")
            
            mock_manager.return_value.get_template_path.return_value = mock_template_dir
            
            # Test generation
            generate_my_vector_store_app(
                name="Test App",
                safe_name="test-app",
                output_path=temp_output_dir / "output",
                icon=None
            )
            
            output_dir = temp_output_dir / "output"
            assert output_dir.exists()
            assert (output_dir / "package.json").exists()
            
            # Check that sqlite3 was added and better-sqlite3 was kept
            with open(output_dir / "package.json") as f:
                package_data = json.load(f)
                assert "sqlite3" in package_data.get("dependencies", {})
                assert "better-sqlite3" in package_data.get("dependencies", {})


class TestElectronAutoFix:
    """Test Electron auto-fix functionality"""
    
    @pytest.fixture
    def temp_app_dir(self):
        """Create temporary app directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            
            # Create package.json
            package_json = app_dir / "package.json"
            with open(package_json, 'w') as f:
                json.dump({
                    "name": "test-app",
                    "scripts": {
                        "dev": "electron ."
                    }
                }, f)
            
            yield app_dir
    
    @patch('src.mcli.workflow.webapp.webapp.subprocess.run')
    def test_auto_fix_electron_installation_success(self, mock_run, temp_app_dir):
        """Test successful Electron auto-fix"""
        mock_run.return_value.returncode = 0
        
        # Create corrupted electron directory
        electron_dir = temp_app_dir / "node_modules" / "electron"
        electron_dir.mkdir(parents=True)
        
        result = auto_fix_electron_installation(temp_app_dir)
        assert result is True
        
        # Verify cleanup and reinstall were called
        assert mock_run.call_count >= 2
    
    @patch('src.mcli.workflow.webapp.webapp.subprocess.run')
    def test_auto_fix_electron_installation_failure(self, mock_run, temp_app_dir):
        """Test failed Electron auto-fix"""
        mock_run.side_effect = Exception("Installation failed")
        
        result = auto_fix_electron_installation(temp_app_dir)
        assert result is False


class TestWebappCLI:
    """Test webapp CLI commands"""
    
    def test_webapp_group_help(self):
        """Test webapp group help"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['--help'])
        assert result.exit_code == 0
        assert 'Web application generation and installation commands' in result.output
    
    def test_generate_help(self):
        """Test generate command help"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['generate', '--help'])
        assert result.exit_code == 0
        assert 'Generate a template web application' in result.output
    
    def test_generate_missing_url_for_webmail(self):
        """Test generate command with missing URL for webmail template"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['generate', '--template', 'webmail'])
        assert result.exit_code != 0
        assert 'Error: URL is required for webmail template' in result.output
    
    def test_install_help(self):
        """Test install command help"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['install', '--help'])
        assert result.exit_code == 0
        assert 'Install a generated web application' in result.output
    
    def test_run_help(self):
        """Test run command help"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['run', '--help'])
        assert result.exit_code == 0
        assert 'Run a generated web application' in result.output
    
    def test_list_help(self):
        """Test list command help"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['list', '--help'])
        assert result.exit_code == 0
        assert 'List all generated web applications' in result.output
    
    def test_delete_help(self):
        """Test delete command help"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['delete', '--help'])
        assert result.exit_code == 0
        assert 'Delete a generated web application' in result.output
    
    def test_test_help(self):
        """Test test command help"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['test', '--help'])
        assert result.exit_code == 0
        assert 'Run Puppeteer tests' in result.output
    
    def test_install_native_deps_help(self):
        """Test install-native-deps command help"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['install-native-deps', '--help'])
        assert result.exit_code == 0
        assert 'Install native dependencies' in result.output
    
    def test_fix_sqlite3_help(self):
        """Test fix-sqlite3 command help"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['fix-sqlite3', '--help'])
        assert result.exit_code == 0
        assert 'Fix SQLite3 native binding issues' in result.output
    
    def test_fix_electron_help(self):
        """Test fix-electron command help"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['fix-electron', '--help'])
        assert result.exit_code == 0
        assert 'Automatically fix Electron installation issues' in result.output
    
    def test_hard_reinstall_help(self):
        """Test hard-reinstall command help"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['hard-reinstall', '--help'])
        assert result.exit_code == 0
        assert 'Hard reinstall a generated web application' in result.output
    
    def test_fresh_app_help(self):
        """Test fresh-app command help"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['fresh-app', '--help'])
        assert result.exit_code == 0
        assert 'Generate a fresh web application' in result.output


class TestWebappIntegration:
    """Integration tests for webapp functionality"""
    
    @pytest.fixture
    def temp_webapps_dir(self):
        """Create temporary webapps directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            webapps_dir = Path(temp_dir) / "webapps"
            webapps_dir.mkdir(parents=True)
            yield webapps_dir
    
    @patch('src.mcli.workflow.webapp.webapp.get_webapps_dir')
    def test_list_apps_empty(self, mock_get_webapps_dir, temp_webapps_dir):
        """Test listing apps when directory is empty"""
        mock_get_webapps_dir.return_value = temp_webapps_dir
        
        runner = CliRunner()
        result = runner.invoke(webapp, ['list'])
        assert result.exit_code == 0
        assert 'No web applications found' in result.output
    
    @patch('src.mcli.workflow.webapp.webapp.get_webapps_dir')
    def test_list_apps_with_apps(self, mock_get_webapps_dir, temp_webapps_dir):
        """Test listing apps when apps exist"""
        mock_get_webapps_dir.return_value = temp_webapps_dir
        
        # Create a test app
        app_dir = temp_webapps_dir / "test-app"
        app_dir.mkdir()
        
        # Create package.json
        package_json = app_dir / "package.json"
        with open(package_json, 'w') as f:
            json.dump({
                "name": "test-app",
                "description": "Test app",
                "version": "1.0.0"
            }, f)
        
        # Create main.js
        main_js = app_dir / "main.js"
        with open(main_js, 'w') as f:
            main_js.write_text('loadURL("https://example.com")')
        
        runner = CliRunner()
        result = runner.invoke(webapp, ['list'])
        assert result.exit_code == 0
        assert 'test-app' in result.output
        assert 'Test app' in result.output
    
    @patch('src.mcli.workflow.webapp.webapp.get_webapps_dir')
    def test_delete_app_confirmation(self, mock_get_webapps_dir, temp_webapps_dir):
        """Test deleting an app with confirmation"""
        mock_get_webapps_dir.return_value = temp_webapps_dir
        
        # Create a test app
        app_dir = temp_webapps_dir / "test-app"
        app_dir.mkdir()
        
        # Create package.json
        package_json = app_dir / "package.json"
        with open(package_json, 'w') as f:
            json.dump({
                "name": "test-app",
                "description": "Test app",
                "version": "1.0.0"
            }, f)
        
        runner = CliRunner()
        result = runner.invoke(webapp, ['delete', 'test-app'], input='n\n')
        assert result.exit_code == 0
        assert 'Deletion cancelled' in result.output
        assert app_dir.exists()  # App should still exist


class TestWebappTemplates:
    """Test webapp template functionality"""
    
    def test_template_choices(self):
        """Test that template choices are valid"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['generate', '--help'])
        assert result.exit_code == 0
        
        # Check that all template choices are mentioned
        assert 'webmail' in result.output
        assert 'vector-store' in result.output
        assert 'my-vector-store' in result.output
    
    def test_template_default(self):
        """Test that vector-store is the default template"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['generate', '--help'])
        assert result.exit_code == 0
        assert 'default=\'vector-store\'' in result.output


class TestWebappErrorHandling:
    """Test webapp error handling"""
    
    def test_generate_invalid_url(self):
        """Test generating with invalid URL"""
        runner = CliRunner()
        result = runner.invoke(webapp, [
            'generate', 
            '--template', 'webmail',
            '--url', 'invalid-url'
        ])
        assert result.exit_code != 0
        assert 'URL must start with http:// or https://' in result.output
    
    def test_run_nonexistent_app(self):
        """Test running a non-existent app"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['run', 'nonexistent-app'])
        assert result.exit_code != 0
        assert 'not found' in result.output
    
    def test_delete_nonexistent_app(self):
        """Test deleting a non-existent app"""
        runner = CliRunner()
        result = runner.invoke(webapp, ['delete', 'nonexistent-app'])
        assert result.exit_code != 0
        assert 'not found' in result.output


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 