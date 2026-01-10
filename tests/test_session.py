import pytest
from typer.testing import CliRunner
from gittask.main import app
from unittest.mock import MagicMock

runner = CliRunner()

def test_session_stop_branch(mock_db, mock_git, mocker):
    """
    Test stopping a branch session.
    """
    mocker.patch("gittask.commands.session.db", mock_db)
    mocker.patch("gittask.commands.session.GitHandler", return_value=mock_git)
    
    mock_git.get_current_branch.return_value = "feature-branch"
    mock_git.get_repo_root.return_value = "/tmp/repo"
    
    mocker.patch.object(mock_db, 'stop_current_session', return_value={'duration_seconds': 120, 'branch': 'feature-branch'})
    
    result = runner.invoke(app, ["stop"])
    
    assert result.exit_code == 0
    assert "Stopped tracking time for 'feature-branch' (2m)" in result.stdout
    mock_db.stop_current_session.assert_called_with("feature-branch", "/tmp/repo")

def test_session_stop_global(mock_db, mock_git, mocker):
    """
    Test stopping a global session (when not in git or no branch session).
    """
    mocker.patch("gittask.commands.session.db", mock_db)
    mocker.patch("gittask.commands.session.GitHandler", return_value=mock_git)
    
    # Simulate not in git repo
    mock_git.get_current_branch.side_effect = Exception("Not a git repo")
    
    mocker.patch.object(mock_db, 'stop_any_active_session', return_value={'duration_seconds': 300, 'branch': '@global:Task'})
    
    result = runner.invoke(app, ["stop"])
    
    assert result.exit_code == 0
    assert "Stopped tracking time for 'Task (Global)' (5m)" in result.stdout
    mock_db.stop_any_active_session.assert_called_once()

def test_session_stop_no_active(mock_db, mock_git, mocker):
    """
    Test stopping when no session is active.
    """
    mocker.patch("gittask.commands.session.db", mock_db)
    mocker.patch("gittask.commands.session.GitHandler", return_value=mock_git)
    
    mock_git.get_current_branch.return_value = "main"
    mock_git.get_repo_root.return_value = "/tmp/repo"
    
    mocker.patch.object(mock_db, 'stop_current_session', return_value=None)
    mocker.patch.object(mock_db, 'stop_any_active_session', return_value=None)
    
    result = runner.invoke(app, ["stop"])
    
    assert result.exit_code == 0
    assert "No active session found" in result.stdout

def test_session_start_success(mock_db, mock_git, mocker):
    """
    Test starting a session for a linked branch.
    """
    mocker.patch("gittask.commands.session.db", mock_db)
    mocker.patch("gittask.commands.session.GitHandler", return_value=mock_git)
    
    mock_git.get_current_branch.return_value = "feature-branch"
    mock_git.get_repo_root.return_value = "/tmp/repo"
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={
        'asana_task_gid': 'task123',
        'asana_task_name': 'Feature Task'
    })
    
    # Ensure no open sessions (real DB is empty by default)
    # mock_db.time_sessions.search.return_value = [] # REMOVED
    
    mocker.patch.object(mock_db, 'start_session')
    
    result = runner.invoke(app, ["start"])
    
    assert result.exit_code == 0
    assert "Started tracking time for 'feature-branch'" in result.stdout
    mock_db.start_session.assert_called_with("feature-branch", "/tmp/repo", "task123")

def test_session_start_not_linked(mock_db, mock_git, mocker):
    """
    Test starting a session for an unlinked branch.
    """
    mocker.patch("gittask.commands.session.db", mock_db)
    mocker.patch("gittask.commands.session.GitHandler", return_value=mock_git)
    
    mock_git.get_current_branch.return_value = "feature-branch"
    mock_git.get_repo_root.return_value = "/tmp/repo"
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value=None)
    
    result = runner.invoke(app, ["start"])
    
    assert result.exit_code == 1
    assert "not linked to an Asana task" in result.stdout

def test_session_start_already_tracking(mock_db, mock_git, mocker):
    """
    Test starting a session when already tracking the same branch.
    """
    mocker.patch("gittask.commands.session.db", mock_db)
    mocker.patch("gittask.commands.session.GitHandler", return_value=mock_git)
    
    mock_git.get_current_branch.return_value = "feature-branch"
    mock_git.get_repo_root.return_value = "/tmp/repo"
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={
        'asana_task_gid': 'task123',
        'asana_task_name': 'Feature Task'
    })
    
    # Insert existing session into real DB
    mock_db.time_sessions.insert({
        'branch': 'feature-branch',
        'repo_path': '/tmp/repo',
        'end_time': None,
        'start_time': '2023-01-01T00:00:00'
    })
    
    mocker.patch.object(mock_db, 'start_session')
    
    result = runner.invoke(app, ["start"])
    
    assert result.exit_code == 0
    assert "Already tracking time for 'feature-branch'" in result.stdout
    mock_db.start_session.assert_not_called()

def test_session_start_not_git(mock_db, mock_git, mocker):
    """
    Test starting a session when not in a git repo.
    """
    mocker.patch("gittask.commands.session.db", mock_db)
    mocker.patch("gittask.commands.session.GitHandler", return_value=mock_git)
    
    mock_git.get_current_branch.side_effect = Exception("Not a git repo")
    
    result = runner.invoke(app, ["start"])
    
    assert result.exit_code == 1
    assert "Not in a git repository" in result.stdout
