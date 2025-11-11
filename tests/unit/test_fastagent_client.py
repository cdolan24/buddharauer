"""
Unit tests for FastAgent client wrapper.

Tests the utility functions for initializing FastAgent, creating agents,
and verifying Ollama models.

Test Coverage:
    - FastAgent initialization
    - Agent factory functions
    - Model verification
    - Configuration loading
    - Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import os

# Import module under test
from src.utils import fastagent_client


class TestFastAgentInitialization:
    """Tests for FastAgent environment initialization."""

    @patch('src.utils.fastagent_client.FASTAGENT_AVAILABLE', True)
    @patch('httpx.get')
    def test_initialize_fastagent_success(self, mock_get):
        """Test successful FastAgent initialization with Ollama."""
        # Mock successful Ollama connection
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Initialize
        fastagent_client.initialize_fastagent()

        # Verify environment variables set
        assert os.environ["GENERIC_API_KEY"] == "ollama"
        assert os.environ["GENERIC_BASE_URL"] == "http://localhost:11434/v1"

        # Verify Ollama connection checked
        mock_get.assert_called_once()

    @patch('src.utils.fastagent_client.FASTAGENT_AVAILABLE', True)
    @patch('httpx.get')
    def test_initialize_fastagent_custom_url(self, mock_get):
        """Test initialization with custom Ollama URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Initialize with custom URL
        custom_url = "http://192.168.1.100:11434/v1"
        fastagent_client.initialize_fastagent(base_url=custom_url)

        # Verify custom URL set
        assert os.environ["GENERIC_BASE_URL"] == custom_url

    @patch('src.utils.fastagent_client.FASTAGENT_AVAILABLE', True)
    @patch('httpx.get')
    def test_initialize_fastagent_connection_failure(self, mock_get):
        """Test initialization fails when Ollama not accessible."""
        # Mock failed Ollama connection
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        # Should raise FastAgentError
        with pytest.raises(fastagent_client.FastAgentError):
            fastagent_client.initialize_fastagent(verify_connection=True)

    @patch('src.utils.fastagent_client.FASTAGENT_AVAILABLE', False)
    def test_initialize_fastagent_not_installed(self):
        """Test initialization fails when FastAgent not installed."""
        with pytest.raises(fastagent_client.FastAgentError, match="not installed"):
            fastagent_client.initialize_fastagent()


class TestAgentFactories:
    """Tests for agent factory functions."""

    @patch('src.utils.fastagent_client.FASTAGENT_AVAILABLE', True)
    @patch('src.utils.fastagent_client.Agent')
    @patch('src.utils.fastagent_client.initialize_fastagent')
    def test_create_orchestrator_agent(self, mock_init, mock_agent_class):
        """Test creating orchestrator agent."""
        # Mock Agent instance
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Create agent
        agent = fastagent_client.create_orchestrator_agent()

        # Verify initialization called
        mock_init.assert_called_once()

        # Verify Agent created with correct parameters
        mock_agent_class.assert_called_once()
        call_kwargs = mock_agent_class.call_args.kwargs
        assert call_kwargs["name"] == "orchestrator"
        assert call_kwargs["model"] == "generic.llama3.2:latest"
        assert call_kwargs["temperature"] == 0.7
        assert "system_prompt" in call_kwargs
        assert isinstance(call_kwargs["tools"], list)

        # Verify returns agent
        assert agent == mock_agent

    @patch('src.utils.fastagent_client.FASTAGENT_AVAILABLE', True)
    @patch('src.utils.fastagent_client.Agent')
    @patch('src.utils.fastagent_client.initialize_fastagent')
    def test_create_retrieval_agent(self, mock_init, mock_agent_class):
        """Test creating retrieval agent."""
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Create agent with custom model
        agent = fastagent_client.create_retrieval_agent(
            model="generic.qwen2.5:latest",
            temperature=0.5
        )

        # Verify Agent created with correct parameters
        call_kwargs = mock_agent_class.call_args.kwargs
        assert call_kwargs["name"] == "retrieval"
        assert call_kwargs["model"] == "generic.qwen2.5:latest"
        assert call_kwargs["temperature"] == 0.5

    @patch('src.utils.fastagent_client.FASTAGENT_AVAILABLE', True)
    @patch('src.utils.fastagent_client.Agent')
    @patch('src.utils.fastagent_client.initialize_fastagent')
    def test_create_analyst_agent(self, mock_init, mock_agent_class):
        """Test creating analyst agent."""
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        agent = fastagent_client.create_analyst_agent()

        call_kwargs = mock_agent_class.call_args.kwargs
        assert call_kwargs["name"] == "analyst"
        assert call_kwargs["model"] == "generic.llama3.2:latest"

    @patch('src.utils.fastagent_client.FASTAGENT_AVAILABLE', True)
    @patch('src.utils.fastagent_client.Agent')
    @patch('src.utils.fastagent_client.initialize_fastagent')
    def test_create_websearch_agent(self, mock_init, mock_agent_class):
        """Test creating websearch agent."""
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        agent = fastagent_client.create_websearch_agent()

        call_kwargs = mock_agent_class.call_args.kwargs
        assert call_kwargs["name"] == "websearch"
        assert call_kwargs["model"] == "generic.mistral:7b"
        assert call_kwargs["temperature"] == 0.3

    @patch('src.utils.fastagent_client.FASTAGENT_AVAILABLE', False)
    def test_create_agent_not_available(self):
        """Test agent creation fails when FastAgent not available."""
        with pytest.raises(fastagent_client.FastAgentError):
            fastagent_client.create_orchestrator_agent()


class TestModelVerification:
    """Tests for Ollama model verification."""

    @patch('src.utils.fastagent_client.httpx.get')
    def test_verify_ollama_models_all_available(self, mock_get):
        """Test model verification when all models available."""
        # Mock Ollama response with all models
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2:latest"},
                {"name": "qwen2.5:latest"},
                {"name": "mistral:7b"},
                {"name": "nomic-embed-text"}
            ]
        }
        mock_get.return_value = mock_response

        # Verify models
        result = fastagent_client.verify_ollama_models()

        # All should be available
        assert result["llama3.2:latest"] is True
        assert result["qwen2.5:latest"] is True
        assert result["mistral:7b"] is True
        assert result["nomic-embed-text"] is True

    @patch('src.utils.fastagent_client.httpx.get')
    def test_verify_ollama_models_some_missing(self, mock_get):
        """Test model verification with some models missing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2:latest"},
                {"name": "nomic-embed-text"}
            ]
        }
        mock_get.return_value = mock_response

        result = fastagent_client.verify_ollama_models()

        # Some available, some not
        assert result["llama3.2:latest"] is True
        assert result["nomic-embed-text"] is True
        assert result["qwen2.5:latest"] is False
        assert result["mistral:7b"] is False

    @patch('src.utils.fastagent_client.httpx.get')
    def test_verify_ollama_models_connection_error(self, mock_get):
        """Test model verification when Ollama not accessible."""
        mock_get.side_effect = Exception("Connection refused")

        result = fastagent_client.verify_ollama_models()

        # All should be False on error
        assert all(not v for v in result.values())

    @patch('src.utils.fastagent_client.httpx.get')
    def test_verify_custom_models(self, mock_get):
        """Test verification of custom model list."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "custom-model:latest"}]
        }
        mock_get.return_value = mock_response

        # Verify custom model list
        result = fastagent_client.verify_ollama_models(
            required_models=["custom-model:latest", "missing-model"]
        )

        assert result["custom-model:latest"] is True
        assert result["missing-model"] is False


class TestAgentConfiguration:
    """Tests for agent configuration loading."""

    @patch('src.utils.fastagent_client.load_config')
    def test_get_agent_config_orchestrator(self, mock_load_config):
        """Test getting orchestrator configuration."""
        mock_load_config.return_value = {}

        config = fastagent_client.get_agent_config("orchestrator")

        assert config["model"] == "generic.llama3.2:latest"
        assert config["temperature"] == 0.7

    @patch('src.utils.fastagent_client.load_config')
    def test_get_agent_config_retrieval(self, mock_load_config):
        """Test getting retrieval agent configuration."""
        mock_load_config.return_value = {}

        config = fastagent_client.get_agent_config("retrieval")

        assert config["model"] == "generic.qwen2.5:latest"
        assert config["temperature"] == 0.5

    @patch('src.utils.fastagent_client.load_config')
    def test_get_agent_config_with_overrides(self, mock_load_config):
        """Test configuration with custom overrides from file."""
        # Mock config with custom settings
        mock_load_config.return_value = {
            "agents": {
                "orchestrator": {
                    "model": "generic.custom:latest",
                    "temperature": 0.9
                }
            }
        }

        config = fastagent_client.get_agent_config("orchestrator")

        # Should use custom values
        assert config["model"] == "generic.custom:latest"
        assert config["temperature"] == 0.9

    def test_get_agent_config_invalid_type(self):
        """Test getting configuration for unknown agent type."""
        with pytest.raises(fastagent_client.FastAgentError, match="Unknown agent type"):
            fastagent_client.get_agent_config("invalid_agent")


class TestSetupFastAgent:
    """Tests for complete FastAgent setup function."""

    @patch('src.utils.fastagent_client.verify_ollama_models')
    @patch('src.utils.fastagent_client.initialize_fastagent')
    def test_setup_fastagent_success(self, mock_init, mock_verify):
        """Test successful complete setup."""
        # Mock all models available
        mock_verify.return_value = {
            "llama3.2:latest": True,
            "qwen2.5:latest": True,
            "mistral:7b": True,
            "nomic-embed-text": True
        }

        result = fastagent_client.setup_fastagent(verify_models=True)

        assert result is True
        mock_init.assert_called_once_with(verify_connection=True)
        mock_verify.assert_called_once()

    @patch('src.utils.fastagent_client.verify_ollama_models')
    @patch('src.utils.fastagent_client.initialize_fastagent')
    def test_setup_fastagent_missing_models(self, mock_init, mock_verify):
        """Test setup with missing models."""
        # Mock some models missing
        mock_verify.return_value = {
            "llama3.2:latest": True,
            "qwen2.5:latest": False,
            "mistral:7b": False,
            "nomic-embed-text": True
        }

        result = fastagent_client.setup_fastagent(verify_models=True)

        # Should return False due to missing models
        assert result is False

    @patch('src.utils.fastagent_client.initialize_fastagent')
    def test_setup_fastagent_init_failure(self, mock_init):
        """Test setup when initialization fails."""
        mock_init.side_effect = Exception("Connection error")

        result = fastagent_client.setup_fastagent(verify_models=False)

        assert result is False

    @patch('src.utils.fastagent_client.initialize_fastagent')
    def test_setup_fastagent_skip_model_verification(self, mock_init):
        """Test setup without model verification."""
        result = fastagent_client.setup_fastagent(verify_models=False)

        assert result is True
        mock_init.assert_called_once()


# Cleanup environment after tests
@pytest.fixture(autouse=True)
def cleanup_environment():
    """Clean up environment variables after each test."""
    yield
    # Remove test environment variables
    for key in ["GENERIC_API_KEY", "GENERIC_BASE_URL"]:
        if key in os.environ:
            del os.environ[key]
