import pytest
from unittest.mock import MagicMock
import os
import tempfile
from pathlib import Path
from gittask.database import DBManager
from gittask.config import ConfigManager

@pytest.fixture
def mock_db(tmp_path):
    """
    Fixture for a temporary database.
    """
    db_path = tmp_path / "db.json"
    db = DBManager(str(db_path))
    return db

@pytest.fixture
def mock_asana(mocker):
    """
    Fixture for mocking AsanaClient.
    """
    mock_client = MagicMock()
    mocker.patch("gittask.commands.track.AsanaClient", return_value=mock_client)
    mocker.patch("gittask.commands.checkout.AsanaClient", return_value=mock_client)
    return mock_client

@pytest.fixture
def mock_git(mocker):
    """
    Fixture for mocking GitHandler.
    """
    mock_git_handler = MagicMock()
    mocker.patch("gittask.commands.checkout.GitHandler", return_value=mock_git_handler)
    mocker.patch("gittask.commands.session.GitHandler", return_value=mock_git_handler)
    
    # Default behavior
    mock_git_handler.get_current_branch.return_value = "main"
    mock_git_handler.get_repo_root.return_value = "/tmp/mock_repo"
    
    return mock_git_handler

@pytest.fixture
def mock_config(mocker, mock_db):
    """
    Fixture for mocking ConfigManager.
    """
    mock_config_manager = MagicMock()
    mocker.patch("gittask.commands.track.ConfigManager", return_value=mock_config_manager)
    mocker.patch("gittask.commands.checkout.ConfigManager", return_value=mock_config_manager)
    
    # Default behavior
    mock_config_manager.get_api_token.return_value = "mock_token"
    mock_config_manager.get_default_workspace.return_value = "mock_workspace_gid"
    mock_config_manager.get_default_project.return_value = "mock_project_gid"
    
    return mock_config_manager
