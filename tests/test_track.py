import pytest
from typer.testing import CliRunner
from gittask.main import app
from gittask.database import DBManager
from unittest.mock import MagicMock

runner = CliRunner()

def test_track_creates_global_session(mock_db, mock_asana, mock_config, mocker):
    """
    Test that 'gittask track' creates a global session.
    """
    mocker.patch("gittask.commands.track.DBManager", return_value=mock_db)
    
    # Mock Asana search to return a task
    mock_asana.__enter__.return_value.search_tasks.return_value = [
        {'gid': '123', 'name': 'Planning'}
    ]
    
    result = runner.invoke(app, ["track", "Planning"])
    
    assert result.exit_code == 0
    assert "Started tracking time for 'Planning' (Global)" in result.stdout
    
    # Verify session in DB
    sessions = mock_db.time_sessions.all()
    assert len(sessions) == 1
    assert sessions[0]['branch'] == "@global:Planning"
    assert sessions[0]['repo_path'] == "GLOBAL"
    assert sessions[0]['task_gid'] == '123'

def test_track_stops_existing_session(mock_db, mock_asana, mock_config, mocker):
    """
    Test that 'gittask track' stops an existing session.
    """
    mocker.patch("gittask.commands.track.DBManager", return_value=mock_db)
    
    # Start an existing session
    mock_db.start_session("feature-branch", "/tmp/repo", "old_task_gid")
    
    # Mock Asana search
    mock_asana.__enter__.return_value.search_tasks.return_value = [
        {'gid': '456', 'name': 'Meeting'}
    ]
    
    result = runner.invoke(app, ["track", "Meeting"])
    
    assert result.exit_code == 0
    
    # Verify old session stopped
    old_session = mock_db.time_sessions.get(doc_id=1)
    assert old_session['end_time'] is not None
    
    # Verify new session started
    new_session = mock_db.time_sessions.get(doc_id=2)
    assert new_session['branch'] == "@global:Meeting"
    assert new_session['end_time'] is None

def test_track_no_auth(mock_db, mock_asana, mock_config, mocker):
    """
    Test that 'gittask track' fails if not authenticated.
    """
    mock_config.get_api_token.return_value = None
    result = runner.invoke(app, ["track", "Task"])
    assert result.exit_code == 1
    assert "Not authenticated" in result.stdout

def test_track_no_workspace(mock_db, mock_asana, mock_config, mocker):
    """
    Test that 'gittask track' fails if no default workspace is set.
    """
    mock_config.get_default_workspace.return_value = None
    result = runner.invoke(app, ["track", "Task"])
    assert result.exit_code == 1
    assert "No default workspace" in result.stdout

def test_track_task_not_found_create(mock_db, mock_asana, mock_config, mocker):
    """
    Test creating a new task when search returns no results.
    """
    mocker.patch("gittask.commands.track.DBManager", return_value=mock_db)
    mock_asana.__enter__.return_value.search_tasks.return_value = []
    
    # Mock questionary
    mock_questionary = mocker.patch("gittask.commands.track.questionary")
    mock_questionary.confirm.return_value.ask.return_value = True # Create? Yes
    
    mock_asana.__enter__.return_value.create_task.return_value = {'gid': 'new_gid', 'name': 'New Task'}
    
    result = runner.invoke(app, ["track", "New Task"])
    
    assert result.exit_code == 0
    assert "Started tracking time for 'New Task' (Global)" in result.stdout
    
    sessions = mock_db.time_sessions.all()
    assert len(sessions) == 1
    assert sessions[0]['task_gid'] == 'new_gid'

def test_track_task_not_found_cancel(mock_db, mock_asana, mock_config, mocker):
    """
    Test cancelling when task is not found.
    """
    mocker.patch("gittask.commands.track.DBManager", return_value=mock_db)
    mock_asana.__enter__.return_value.search_tasks.return_value = []
    
    mock_questionary = mocker.patch("gittask.commands.track.questionary")
    mock_questionary.confirm.return_value.ask.return_value = False # Create? No
    
    result = runner.invoke(app, ["track", "New Task"])
    
    assert result.exit_code == 0
    assert "Tracking cancelled" in result.stdout
    assert len(mock_db.time_sessions.all()) == 0

def test_track_multiple_matches(mock_db, mock_asana, mock_config, mocker):
    """
    Test selecting from multiple matching tasks.
    """
    mocker.patch("gittask.commands.track.DBManager", return_value=mock_db)
    mock_asana.__enter__.return_value.search_tasks.return_value = [
        {'gid': '1', 'name': 'Task A'},
        {'gid': '2', 'name': 'Task B'}
    ]
    
    mock_questionary = mocker.patch("gittask.commands.track.questionary")
    mock_questionary.select.return_value.ask.return_value = 'Task B'
    
    result = runner.invoke(app, ["track", "Task"])
    
    assert result.exit_code == 0
    assert "Started tracking time for 'Task B' (Global)" in result.stdout
    
    sessions = mock_db.time_sessions.all()
    assert len(sessions) == 1
    assert sessions[0]['task_gid'] == '2'

def test_track_interactive_create(mock_db, mock_asana, mock_config, mocker):
    """
    Test interactive mode (no arg) where user creates a new task.
    """
    mocker.patch("gittask.commands.track.DBManager", return_value=mock_db)
    
    # Mock project tasks fetch
    mock_asana.__enter__.return_value.get_project_tasks.return_value = []
    
    mock_questionary = mocker.patch("gittask.commands.track.questionary")
    mock_questionary.text.return_value.ask.return_value = "Interactive Task"
    mock_questionary.confirm.return_value.ask.return_value = True # Create? Yes
    
    # Mock select_and_create_tags to return empty list
    mocker.patch("gittask.commands.track.select_and_create_tags", return_value=[])
    
    mock_asana.__enter__.return_value.create_task.return_value = {'gid': 'int_gid', 'name': 'Interactive Task'}
    
    result = runner.invoke(app, ["track"]) # No args
    
    assert result.exit_code == 0
    assert "Started tracking time for 'Interactive Task' (Global)" in result.stdout
    
    sessions = mock_db.time_sessions.all()
    assert len(sessions) == 1
    assert sessions[0]['task_gid'] == 'int_gid'
