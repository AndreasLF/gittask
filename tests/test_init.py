import pytest
from typer.testing import CliRunner
from gittask.commands.init import init
import typer
from unittest.mock import MagicMock

runner = CliRunner()
app = typer.Typer()
app.command()(init)

def test_init_success(mock_config, mock_asana, mocker):
    """
    Test successful initialization.
    """
    mocker.patch("gittask.commands.init.ConfigManager", return_value=mock_config)
    mocker.patch("gittask.commands.init.AsanaClient", return_value=mock_asana)
    
    mock_questionary = mocker.patch("gittask.commands.init.questionary")
    
    # Mock Asana data
    mock_asana.__enter__.return_value.me = {'name': 'Test User'}
    mock_asana.__enter__.return_value.get_workspaces.return_value = [{'gid': 'ws1', 'name': 'Workspace 1'}]
    mock_asana.__enter__.return_value.get_projects.return_value = [{'gid': 'p1', 'name': 'Project 1'}]
    
    # Mock user input
    # 1. Select Workspace
    mock_questionary.select.return_value.ask.side_effect = ['ws1', 'p1'] 
    # 2. Paid plan confirm
    mock_questionary.confirm.return_value.ask.return_value = True
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 0
    assert "Hello, Test User!" in result.stdout
    assert "Configuration saved!" in result.stdout
    
    mock_config.set_default_workspace.assert_called_with('ws1')
    mock_config.set_paid_plan_status.assert_called_with(True)
    mock_config.set_default_project.assert_called_with('p1')

def test_init_not_authenticated(mock_config, mocker):
    """
    Test init fails if not authenticated.
    """
    mocker.patch("gittask.commands.init.ConfigManager", return_value=mock_config)
    mock_config.get_api_token.return_value = None
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 1
    assert "Not authenticated" in result.stdout

def test_init_no_workspaces(mock_config, mock_asana, mocker):
    """
    Test init fails if no workspaces found.
    """
    mocker.patch("gittask.commands.init.ConfigManager", return_value=mock_config)
    mocker.patch("gittask.commands.init.AsanaClient", return_value=mock_asana)
    
    mock_asana.__enter__.return_value.me = {'name': 'Test User'}
    mock_asana.__enter__.return_value.get_workspaces.return_value = []
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 1
    assert "No workspaces found" in result.stdout
