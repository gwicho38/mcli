"""
CLI tests for mcli.workflow.registry module
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

# Check if fuzzywuzzy is available
try:
    import fuzzywuzzy
    HAS_FUZZYWUZZY = True
except ImportError:
    HAS_FUZZYWUZZY = False


class TestDockerClient:
    """Test suite for DockerClient class"""

    def test_docker_client_init(self):
        """Test DockerClient initialization"""
        from mcli.workflow.registry.registry import DockerClient

        client = DockerClient("https://registry.example.com")

        assert client.registry_url == "https://registry.example.com"

    @patch('mcli.workflow.registry.registry.requests.get')
    def test_get_catalog_success(self, mock_get):
        """Test getting catalog successfully"""
        from mcli.workflow.registry.registry import DockerClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"repositories": ["repo1", "repo2"]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = DockerClient("https://registry.example.com")
        catalog = client.get_catalog()

        assert catalog == {"repositories": ["repo1", "repo2"]}
        assert len(catalog["repositories"]) == 2

    @patch('mcli.workflow.registry.registry.requests.get')
    def test_get_catalog_error(self, mock_get):
        """Test catalog fetch with error"""
        from mcli.workflow.registry.registry import DockerClient

        mock_get.side_effect = Exception("Connection error")

        client = DockerClient("https://registry.example.com")
        catalog = client.get_catalog()

        assert catalog is None

    @patch('mcli.workflow.registry.registry.requests.get')
    def test_get_tags(self, mock_get):
        """Test getting tags for a repository"""
        from mcli.workflow.registry.registry import DockerClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"tags": ["v1.0", "v1.1", "latest"]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = DockerClient("https://registry.example.com")
        tags = client.get_tags("myrepo")

        assert tags == {"tags": ["v1.0", "v1.1", "latest"]}

    @patch('mcli.workflow.registry.registry.requests.get')
    def test_search_repository(self, mock_get):
        """Test searching for repositories"""
        from mcli.workflow.registry.registry import DockerClient

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "repositories": ["frontend", "backend", "database"]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = DockerClient("https://registry.example.com")
        results = client.search_repository("front")

        assert "frontend" in results
        assert "backend" not in results

    @patch('mcli.workflow.registry.registry.requests.get')
    def test_count_images(self, mock_get):
        """Test counting images in repository"""
        from mcli.workflow.registry.registry import DockerClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"tags": ["v1", "v2", "v3"]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = DockerClient("https://registry.example.com")
        count = client.count_images("myrepo")

        assert count == 3

    @patch('mcli.workflow.registry.registry.requests.get')
    def test_count_images_no_tags(self, mock_get):
        """Test counting images when fetch fails"""
        from mcli.workflow.registry.registry import DockerClient

        mock_get.side_effect = Exception("Error")

        client = DockerClient("https://registry.example.com")
        count = client.count_images("myrepo")

        assert count == 0


class TestRegistryCommands:
    """Test suite for registry CLI commands"""

    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()

    def test_registry_group_exists(self):
        """Test registry command group exists"""
        from mcli.workflow.registry.registry import registry

        assert registry is not None
        assert hasattr(registry, 'commands') or callable(registry)

    def test_registry_group_help(self):
        """Test registry command group help"""
        from mcli.workflow.registry.registry import registry

        result = self.runner.invoke(registry, ['--help'])

        assert result.exit_code == 0
        assert 'registry' in result.output.lower()

    @patch('mcli.workflow.registry.registry.requests.get')
    def test_catalog_command(self, mock_get):
        """Test catalog command"""
        from mcli.workflow.registry.registry import registry

        mock_response = MagicMock()
        mock_response.json.return_value = {"repositories": ["repo1", "repo2"]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = self.runner.invoke(
            registry,
            ['--registry-url', 'https://registry.example.com', 'catalog']
        )

        assert result.exit_code == 0
        assert 'repo1' in result.output or 'Catalog' in result.output

    @patch('mcli.workflow.registry.registry.requests.get')
    def test_tags_command(self, mock_get):
        """Test tags command"""
        from mcli.workflow.registry.registry import registry

        mock_response = MagicMock()
        mock_response.json.return_value = {"tags": ["v1.0", "latest"]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = self.runner.invoke(
            registry,
            ['--registry-url', 'https://registry.example.com', 'tags', 'myrepo']
        )

        assert result.exit_code == 0

    @patch('mcli.workflow.registry.registry.requests.get')
    def test_search_command(self, mock_get):
        """Test search command"""
        from mcli.workflow.registry.registry import registry

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "repositories": ["frontend-app", "backend-app"]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = self.runner.invoke(
            registry,
            ['--registry-url', 'https://registry.example.com', 'search', 'frontend']
        )

        assert result.exit_code == 0

    @patch('mcli.workflow.registry.registry.requests.get')
    def test_count_command(self, mock_get):
        """Test count command"""
        from mcli.workflow.registry.registry import registry

        mock_response = MagicMock()
        mock_response.json.return_value = {"tags": ["v1", "v2"]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = self.runner.invoke(
            registry,
            ['--registry-url', 'https://registry.example.com', 'count', 'myrepo']
        )

        assert result.exit_code == 0
        assert '2' in result.output or 'Number' in result.output

    def test_catalog_help(self):
        """Test catalog command help"""
        from mcli.workflow.registry.registry import registry

        result = self.runner.invoke(registry, ['catalog', '--help'])

        assert result.exit_code == 0

    def test_tags_help(self):
        """Test tags command help"""
        from mcli.workflow.registry.registry import registry

        result = self.runner.invoke(registry, ['tags', '--help'])

        assert result.exit_code == 0

    def test_search_help(self):
        """Test search command help"""
        from mcli.workflow.registry.registry import registry

        result = self.runner.invoke(registry, ['search', '--help'])

        assert result.exit_code == 0
