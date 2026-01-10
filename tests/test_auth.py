import pytest
from typer.testing import CliRunner
from gittask.main import app
from unittest.mock import MagicMock

runner = CliRunner()

def test_auth_login_asana(mock_config, mocker):
    """
    Test logging in with Asana token.
    """
    mocker.patch("gittask.commands.auth.ConfigManager", return_value=mock_config)
    
    result = runner.invoke(app, ["auth", "login"], input="fake_asana_token\n")
    
    assert result.exit_code == 0
    assert "Successfully logged in to Asana" in result.stdout
    mock_config.set_api_token.assert_called_with("fake_asana_token")

def test_auth_login_github(mock_config, mocker):
    """
    Test logging in with GitHub token.
    """
    mocker.patch("gittask.commands.auth.ConfigManager", return_value=mock_config)
    
    result = runner.invoke(app, ["auth", "login", "--github"], input="fake_github_token\n")
    
    assert result.exit_code == 0
    assert "Successfully logged in to GitHub" in result.stdout
    mock_config.set_github_token.assert_called_with("fake_github_token")

def test_auth_logout(mock_config, mocker):
    """
    Test logging out.
    """
    mocker.patch("gittask.commands.auth.ConfigManager", return_value=mock_config)
    
    result = runner.invoke(app, ["auth", "logout"])
    
    assert result.exit_code == 0
    assert "Logged out" in result.stdout
    mock_config.logout.assert_called()
    mock_config.set_api_token.assert_called_with("")

def test_auth_login_github_preserves_asana_token(mock_config, mocker):
    """
    Test that logging in to GitHub does not prompt for or change Asana token.
    """
    mocker.patch("gittask.commands.auth.ConfigManager", return_value=mock_config)
    
    # Run with --github
    result = runner.invoke(app, ["auth", "login", "--github"], input="new_github_token\n")
    
    assert result.exit_code == 0
    
    # Verify GitHub token set
    mock_config.set_github_token.assert_called_with("new_github_token")
    
    # Verify Asana token NOT set/changed
    mock_config.set_api_token.assert_not_called()
