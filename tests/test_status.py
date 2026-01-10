import pytest
from typer.testing import CliRunner
from gittask.commands.status import status
import typer
from unittest.mock import MagicMock
import time

runner = CliRunner()
app = typer.Typer()
app.command()(status)

def test_status_active_branch_session(mock_db, mocker):
    """
    Test status with an active branch session.
    """
    mocker.patch("gittask.commands.status.DBManager", return_value=mock_db)
    
    # Mock active session
    start_time = time.time() - 3665 # 1h 1m 5s ago
    mock_session = {
        'branch': 'feature-branch',
        'start_time': start_time,
        'end_time': None,
        'repo_path': '/tmp/repo'
    }
    # Use real DB insert instead of mocking search
    mock_db.time_sessions.insert(mock_session)
    
    # Mock task info
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={
        'asana_task_name': 'Feature Task'
    })
    
    # Mock unsynced
    mocker.patch.object(mock_db, 'get_unsynced_sessions', return_value=[])
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 0
    assert "Currently tracking: feature-branch" in result.stdout
    assert "Task: Feature Task" in result.stdout
    assert "Duration: 1h 1m" in result.stdout
    assert "All sessions synced!" in result.stdout

def test_status_active_global_session(mock_db, mocker):
    """
    Test status with an active global session.
    """
    mocker.patch("gittask.commands.status.DBManager", return_value=mock_db)
    
    # Mock active session
    start_time = time.time() - 120 # 2m ago
    mock_session = {
        'branch': '@global:Global Task',
        'start_time': start_time,
        'end_time': None,
        'repo_path': 'GLOBAL'
    }
    mock_db.time_sessions.insert(mock_session)
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={
        'asana_task_name': 'Global Task'
    })
    
    mocker.patch.object(mock_db, 'get_unsynced_sessions', return_value=[])
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 0
    assert "Currently tracking: Global Task (Global)" in result.stdout
    assert "Duration: 0h 2m" in result.stdout

def test_status_no_active_session(mock_db, mocker):
    """
    Test status with no active session.
    """
    mocker.patch("gittask.commands.status.DBManager", return_value=mock_db)
    
    # No insert needed, DB is empty
    mocker.patch.object(mock_db, 'get_unsynced_sessions', return_value=[])
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 0
    assert "No active time tracking session" in result.stdout

def test_status_unsynced_sessions(mock_db, mocker):
    """
    Test status with unsynced sessions.
    """
    mocker.patch("gittask.commands.status.DBManager", return_value=mock_db)
    
    # No active session
    
    unsynced = [
        {
            'branch': 'branch-1',
            'duration_seconds': 3600,
            'start_time': 1672531200, # 2023-01-01 00:00:00
            'end_time': 1672534800
        }
    ]
    mocker.patch.object(mock_db, 'get_unsynced_sessions', return_value=unsynced)
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 0
    assert "Unsynced Sessions" in result.stdout
    assert "branch-1" in result.stdout
    assert "1h 0m" in result.stdout
