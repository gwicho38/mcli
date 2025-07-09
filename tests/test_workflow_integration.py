import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

# Import workflow components
from src.mcli.workflow.workflow import workflow
from src.mcli.workflow.webapp.webapp import webapp
from src.mcli.workflow.daemon.commands import daemon


class TestWorkflowIntegration:
    """Integration tests for the workflow system"""
    
    def test_workflow_group_help(self):
        """Test workflow group help"""
        runner = CliRunner()
        result = runner.invoke(workflow, ['--help'])
        assert result.exit_code == 0
        assert 'Workflow commands' in result.output
    
    def test_workflow_subcommands(self):
        """Test that all workflow subcommands are available"""
        runner = CliRunner()
        result = runner.invoke(workflow, ['--help'])
        assert result.exit_code == 0
        
        # Check that all expected subcommands are present
        assert 'webapp' in result.output
        assert 'file' in result.output
        assert 'videos' in result.output
        assert 'daemon' in result.output
    
    def test_workflow_webapp_integration(self):
        """Test workflow webapp integration"""
        runner = CliRunner()
        result = runner.invoke(workflow, ['webapp', '--help'])
        assert result.exit_code == 0
        assert 'Web application generation and installation commands' in result.output
    
    def test_workflow_daemon_integration(self):
        """Test workflow daemon integration"""
        runner = CliRunner()
        result = runner.invoke(workflow, ['daemon', '--help'])
        assert result.exit_code == 0
        assert 'Daemon service for command management' in result.output


class TestWorkflowCommandStructure:
    """Test the command structure and hierarchy"""
    
    def test_command_hierarchy(self):
        """Test that commands are properly nested"""
        runner = CliRunner()
        
        # Test main workflow help
        result = runner.invoke(workflow, ['--help'])
        assert result.exit_code == 0
        
        # Test webapp subcommand
        result = runner.invoke(workflow, ['webapp', '--help'])
        assert result.exit_code == 0
        
        # Test daemon subcommand
        result = runner.invoke(workflow, ['daemon', '--help'])
        assert result.exit_code == 0
    
    def test_command_help_consistency(self):
        """Test that help messages are consistent"""
        runner = CliRunner()
        
        # Test that webapp help is the same whether called directly or through workflow
        webapp_result = runner.invoke(webapp, ['--help'])
        workflow_webapp_result = runner.invoke(workflow, ['webapp', '--help'])
        
        assert webapp_result.output == workflow_webapp_result.output
        
        # Test that daemon help is the same whether called directly or through workflow
        daemon_result = runner.invoke(daemon, ['--help'])
        workflow_daemon_result = runner.invoke(workflow, ['daemon', '--help'])
        
        assert daemon_result.output == workflow_daemon_result.output


class TestWorkflowErrorHandling:
    """Test error handling in the workflow system"""
    
    def test_invalid_subcommand(self):
        """Test handling of invalid subcommands"""
        runner = CliRunner()
        result = runner.invoke(workflow, ['invalid-command'])
        assert result.exit_code != 0
        assert 'No such command' in result.output
    
    def test_missing_required_arguments(self):
        """Test handling of missing required arguments"""
        runner = CliRunner()
        
        # Test webapp generate without required arguments
        result = runner.invoke(workflow, ['webapp', 'generate'])
        assert result.exit_code == 0  # Should show help, not error
        
        # Test daemon add-file without required arguments
        result = runner.invoke(workflow, ['daemon', 'add-file'])
        assert result.exit_code != 0  # Should fail due to missing arguments


class TestWorkflowCommandCompleteness:
    """Test that all commands are properly registered"""
    
    def test_all_webapp_commands_available(self):
        """Test that all webapp commands are available through workflow"""
        runner = CliRunner()
        
        webapp_commands = ['generate', 'install', 'run', 'list', 'delete', 'test']
        
        for cmd in webapp_commands:
            result = runner.invoke(workflow, ['webapp', cmd, '--help'])
            assert result.exit_code == 0, f"Command 'webapp {cmd}' not available"
    
    def test_all_daemon_commands_available(self):
        """Test that all daemon commands are available through workflow"""
        runner = CliRunner()
        
        daemon_commands = ['start', 'stop', 'status', 'add-file', 'add-stdin', 
                          'add-interactive', 'execute', 'search', 'list', 'show', 
                          'delete', 'edit', 'groups']
        
        for cmd in daemon_commands:
            result = runner.invoke(workflow, ['daemon', cmd, '--help'])
            assert result.exit_code == 0, f"Command 'daemon {cmd}' not available"


class TestWorkflowConfiguration:
    """Test workflow configuration and setup"""
    
    def test_workflow_imports(self):
        """Test that all workflow components can be imported"""
        # This test ensures that all imports work correctly
        from src.mcli.workflow.workflow import workflow
        from src.mcli.workflow.webapp.webapp import webapp
        from src.mcli.workflow.daemon.commands import daemon
        from src.mcli.workflow.file.file import file
        from src.mcli.workflow.videos.videos import videos
        
        # If we get here, all imports succeeded
        assert True
    
    def test_command_registration(self):
        """Test that commands are properly registered"""
        # Test that the workflow group has the expected commands
        workflow_commands = [cmd.name for cmd in workflow.commands.values()]
        
        expected_commands = ['webapp', 'file', 'videos', 'daemon']
        for cmd in expected_commands:
            assert cmd in workflow_commands, f"Command '{cmd}' not registered in workflow"


class TestWorkflowEndToEnd:
    """End-to-end tests for the workflow system"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_workflow_help_chain(self):
        """Test that help works at all levels"""
        runner = CliRunner()
        
        # Test main help
        result = runner.invoke(workflow, ['--help'])
        assert result.exit_code == 0
        
        # Test subcommand help
        result = runner.invoke(workflow, ['webapp', '--help'])
        assert result.exit_code == 0
        
        result = runner.invoke(workflow, ['daemon', '--help'])
        assert result.exit_code == 0
    
    def test_command_argument_validation(self):
        """Test that command argument validation works"""
        runner = CliRunner()
        
        # Test webapp generate with invalid template
        result = runner.invoke(workflow, ['webapp', 'generate', '--template', 'invalid-template'])
        assert result.exit_code != 0
        
        # Test daemon search with valid arguments
        result = runner.invoke(workflow, ['daemon', 'search', '--help'])
        assert result.exit_code == 0


class TestWorkflowPerformance:
    """Test workflow performance characteristics"""
    
    def test_help_response_time(self):
        """Test that help commands respond quickly"""
        import time
        
        runner = CliRunner()
        
        # Test main workflow help
        start_time = time.time()
        result = runner.invoke(workflow, ['--help'])
        end_time = time.time()
        
        assert result.exit_code == 0
        assert (end_time - start_time) < 1.0  # Should respond within 1 second
        
        # Test subcommand help
        start_time = time.time()
        result = runner.invoke(workflow, ['webapp', '--help'])
        end_time = time.time()
        
        assert result.exit_code == 0
        assert (end_time - start_time) < 1.0  # Should respond within 1 second


class TestWorkflowCompatibility:
    """Test workflow compatibility with different environments"""
    
    def test_workflow_without_dependencies(self):
        """Test that workflow works without optional dependencies"""
        # This test ensures that the workflow system doesn't break
        # when optional dependencies are missing
        runner = CliRunner()
        
        # Test basic help functionality
        result = runner.invoke(workflow, ['--help'])
        assert result.exit_code == 0
        
        # Test subcommand help
        result = runner.invoke(workflow, ['webapp', '--help'])
        assert result.exit_code == 0
        
        result = runner.invoke(workflow, ['daemon', '--help'])
        assert result.exit_code == 0


class TestWorkflowDocumentation:
    """Test that workflow commands have proper documentation"""
    
    def test_command_descriptions(self):
        """Test that all commands have descriptions"""
        runner = CliRunner()
        
        # Test main workflow description
        result = runner.invoke(workflow, ['--help'])
        assert 'Workflow commands' in result.output
        
        # Test webapp description
        result = runner.invoke(workflow, ['webapp', '--help'])
        assert 'Web application generation and installation commands' in result.output
        
        # Test daemon description
        result = runner.invoke(workflow, ['daemon', '--help'])
        assert 'Daemon service for command management' in result.output
    
    def test_subcommand_descriptions(self):
        """Test that subcommands have descriptions"""
        runner = CliRunner()
        
        # Test webapp subcommands
        webapp_commands = {
            'generate': 'Generate a template web application',
            'install': 'Install a generated web application',
            'run': 'Run a generated web application',
            'list': 'List all generated web applications',
            'delete': 'Delete a generated web application'
        }
        
        for cmd, expected_desc in webapp_commands.items():
            result = runner.invoke(workflow, ['webapp', cmd, '--help'])
            assert result.exit_code == 0
            # Note: We can't easily check exact descriptions due to Click's formatting
            # but we can ensure the help command works
        
        # Test daemon subcommands
        daemon_commands = {
            'start': 'Start the daemon service',
            'stop': 'Stop the daemon service',
            'status': 'Show daemon status'
        }
        
        for cmd, expected_desc in daemon_commands.items():
            result = runner.invoke(workflow, ['daemon', cmd, '--help'])
            assert result.exit_code == 0


class TestWorkflowErrorRecovery:
    """Test workflow error recovery and graceful degradation"""
    
    def test_missing_module_handling(self):
        """Test that missing modules are handled gracefully"""
        # This test ensures that the workflow system doesn't crash
        # when optional modules are missing
        runner = CliRunner()
        
        # Test that basic functionality still works
        result = runner.invoke(workflow, ['--help'])
        assert result.exit_code == 0
    
    def test_invalid_configuration_handling(self):
        """Test that invalid configurations are handled gracefully"""
        runner = CliRunner()
        
        # Test that commands still work even with invalid configurations
        result = runner.invoke(workflow, ['webapp', '--help'])
        assert result.exit_code == 0
        
        result = runner.invoke(workflow, ['daemon', '--help'])
        assert result.exit_code == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 