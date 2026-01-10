import pytest
from typer.testing import CliRunner
from gittask.commands.sync import sync
import typer
from unittest.mock import MagicMock, call

runner = CliRunner()
app = typer.Typer()
app.command()(sync)

def test_sync_success_paid_plan(mock_db, mock_config, mock_asana, mocker):
    """
    Test successful sync with paid plan (add_time_entry).
    """
    mocker.patch("gittask.commands.sync.DBManager", return_value=mock_db)
    mocker.patch("gittask.commands.sync.ConfigManager", return_value=mock_config)
    mocker.patch("gittask.commands.sync.AsanaClient", return_value=mock_asana)
    
    # Mock unsynced sessions
    sessions = [
        {'id': 1, 'task_gid': 't1', 'duration_seconds': 3600, 'end_time': 123, 'branch': 'b1'},
        {'id': 2, 'task_gid': 't2', 'duration_seconds': 1800, 'end_time': 456, 'branch': 'b2'}
    ]
    mocker.patch.object(mock_db, 'get_unsynced_sessions', return_value=sessions)
    mocker.patch.object(mock_db, 'mark_session_synced')
    
    # Mock paid plan
    mock_config.get_paid_plan_status.return_value = True
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 0
    assert "Syncing 2 sessions..." in result.stdout
    assert "Sync complete!" in result.stdout
    
    # Verify Asana calls
    mock_asana.__enter__.return_value.add_time_entry.assert_has_calls([
        call('t1', 3600),
        call('t2', 1800)
    ])
    
    # Verify DB calls
    mock_db.mark_session_synced.assert_has_calls([
        call(1),
        call(2)
    ])

def test_sync_success_free_plan(mock_db, mock_config, mock_asana, mocker):
    """
    Test successful sync with free plan (log_time_comment).
    """
    mocker.patch("gittask.commands.sync.DBManager", return_value=mock_db)
    mocker.patch("gittask.commands.sync.ConfigManager", return_value=mock_config)
    mocker.patch("gittask.commands.sync.AsanaClient", return_value=mock_asana)
    
    sessions = [
        {'id': 1, 'task_gid': 't1', 'duration_seconds': 3600, 'end_time': 123, 'branch': 'b1'}
    ]
    mocker.patch.object(mock_db, 'get_unsynced_sessions', return_value=sessions)
    mocker.patch.object(mock_db, 'mark_session_synced')
    
    mock_config.get_paid_plan_status.return_value = False
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 0
    assert "Sync complete!" in result.stdout
    
    mock_asana.__enter__.return_value.log_time_comment.assert_called_with('t1', 3600, 'b1')
    mock_db.mark_session_synced.assert_called_with(1)

def test_sync_no_token(mock_config, mocker):
    """
    Test sync fails if not authenticated.
    """
    mocker.patch("gittask.commands.sync.ConfigManager", return_value=mock_config)
    mock_config.get_api_token.return_value = None
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 1
    assert "Not authenticated" in result.stdout

def test_sync_nothing_to_sync(mock_db, mock_config, mock_asana, mocker):
    """
    Test sync when there are no unsynced sessions.
    """
    mocker.patch("gittask.commands.sync.DBManager", return_value=mock_db)
    mocker.patch("gittask.commands.sync.ConfigManager", return_value=mock_config)
    mocker.patch("gittask.commands.sync.AsanaClient", return_value=mock_asana)
    
    mocker.patch.object(mock_db, 'get_unsynced_sessions', return_value=[])
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 0
    assert "Nothing to sync" in result.stdout

def test_sync_only_active_sessions(mock_db, mock_config, mock_asana, mocker):
    """
    Test sync when only active sessions exist (no end_time).
    """
    mocker.patch("gittask.commands.sync.DBManager", return_value=mock_db)
    mocker.patch("gittask.commands.sync.ConfigManager", return_value=mock_config)
    mocker.patch("gittask.commands.sync.AsanaClient", return_value=mock_asana)
    
    sessions = [
        {'id': 1, 'end_time': None}
    ]
    mocker.patch.object(mock_db, 'get_unsynced_sessions', return_value=sessions)
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 0
    assert "Only active sessions found" in result.stdout

def test_sync_failure(mock_db, mock_config, mock_asana, mocker):
    """
    Test sync handles individual session failures gracefully.
    """
    mocker.patch("gittask.commands.sync.DBManager", return_value=mock_db)
    mocker.patch("gittask.commands.sync.ConfigManager", return_value=mock_config)
    mocker.patch("gittask.commands.sync.AsanaClient", return_value=mock_asana)
    
    sessions = [
        {'id': 1, 'task_gid': 't1', 'duration_seconds': 3600, 'end_time': 123, 'branch': 'b1'},
        {'id': 2, 'task_gid': 't2', 'duration_seconds': 1800, 'end_time': 456, 'branch': 'b2'}
    ]
    mocker.patch.object(mock_db, 'get_unsynced_sessions', return_value=sessions)
    mocker.patch.object(mock_db, 'mark_session_synced')
    
    mock_config.get_paid_plan_status.return_value = True
    
    # Fail first, succeed second
    mock_asana.__enter__.return_value.add_time_entry.side_effect = [Exception("API Error"), None]
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 0
    assert "Failed to sync session 1: API Error" in result.stdout
    assert "Sync complete!" in result.stdout
    
    # Verify only second session marked synced
    mock_db.mark_session_synced.assert_called_once_with(2)
