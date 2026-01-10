import pytest
from typer.testing import CliRunner
from gittask.main import app
from unittest.mock import MagicMock, call

runner = CliRunner()

def test_finish_full_flow(mock_db, mock_git, mock_config, mock_asana, mocker):
    """
    Test the happy path: linked task, active session, open PR, cleanup.
    """
    # Mocks
    mocker.patch("gittask.commands.finish.db", mock_db)
    mocker.patch("gittask.commands.finish.git", mock_git)
    mocker.patch("gittask.commands.finish.config", mock_config)
    mocker.patch("gittask.commands.finish.AsanaClient", return_value=mock_asana)
    
    # Mock GitHub
    mock_gh_client = MagicMock()
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_pr.number = 1
    mock_pr.title = "Test PR"
    mock_repo.owner.login = "owner"
    mock_repo.get_pulls.return_value = MagicMock(totalCount=1, __getitem__=lambda s, i: mock_pr)
    
    mocker.patch("gittask.commands.finish.get_github_client", return_value=mock_gh_client)
    mocker.patch("gittask.commands.finish.get_github_repo", return_value=mock_repo)
    
    # Mock subprocess
    mock_subprocess = mocker.patch("gittask.commands.finish.subprocess.run")
    
    # Mock questionary
    mock_questionary = mocker.patch("gittask.commands.finish.questionary")
    mock_questionary.confirm.return_value.ask.return_value = True # Say yes to everything
    
    # Setup Data
    mock_git.get_current_branch.return_value = "feature-branch"
    mock_config.get_paid_plan_status.return_value = False
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={
        'asana_task_gid': 'task123',
        'asana_task_name': 'Feature Task'
    })
    mocker.patch.object(mock_db, 'stop_current_session', return_value={'duration_seconds': 3600})
    mocker.patch.object(mock_db, 'get_unsynced_sessions', return_value=[
        {'id': 1, 'task_gid': 'task123', 'duration_seconds': 3600, 'branch': 'feature-branch', 'end_time': 1234567890}
    ])
    mocker.patch.object(mock_db, 'mark_session_synced')
    
    # Run
    result = runner.invoke(app, ["finish"])
    
    assert result.exit_code == 0
    
    # Verifications
    # 1. Stop Timer
    mock_db.stop_current_session.assert_called_once()
    
    # 1.5 Sync Time
    mock_asana.__enter__.return_value.log_time_comment.assert_called() # Default free plan
    mock_db.mark_session_synced.assert_called_with(1)
    
    # 2. Merge PR
    mock_pr.merge.assert_called_once()
    
    # 3. Close Asana Task
    mock_asana.__enter__.return_value.complete_task.assert_called_with('task123')
    
    # 4. Cleanup
    mock_git.checkout_branch.assert_called_with("main")
    mock_subprocess.assert_has_calls([
        call(["git", "pull"], check=True),
        call(["git", "branch", "-d", "feature-branch"], check=True)
    ])

def test_finish_no_task_abort(mock_db, mock_git, mocker):
    """
    Test aborting when no task is linked.
    """
    mocker.patch("gittask.commands.finish.db", mock_db)
    mocker.patch("gittask.commands.finish.git", mock_git)
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value=None)
    mocker.patch.object(mock_db, 'stop_current_session') # Should not be called, but good to mock
    
    mock_questionary = mocker.patch("gittask.commands.finish.questionary")
    mock_questionary.confirm.return_value.ask.return_value = False # Abort
    
    result = runner.invoke(app, ["finish"])
    
    assert result.exit_code == 0 
    assert "Current branch is not linked" in result.stdout
    
    # Verify we didn't proceed to stop timer
    mock_db.stop_current_session.assert_not_called()

def test_finish_no_pr_found(mock_db, mock_git, mock_config, mock_asana, mocker):
    """
    Test flow when no PR is found.
    """
    mocker.patch("gittask.commands.finish.db", mock_db)
    mocker.patch("gittask.commands.finish.git", mock_git)
    mocker.patch("gittask.commands.finish.config", mock_config)
    mocker.patch("gittask.commands.finish.AsanaClient", return_value=mock_asana)
    
    mock_gh_client = MagicMock()
    mock_repo = MagicMock()
    mock_repo.owner.login = "owner"
    mock_repo.get_pulls.return_value = MagicMock(totalCount=0) # No PRs
    
    mocker.patch("gittask.commands.finish.get_github_client", return_value=mock_gh_client)
    mocker.patch("gittask.commands.finish.get_github_repo", return_value=mock_repo)
    
    mock_questionary = mocker.patch("gittask.commands.finish.questionary")
    mock_questionary.confirm.return_value.ask.return_value = True
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={'asana_task_gid': '123', 'asana_task_name': 'Task'})
    mocker.patch.object(mock_db, 'stop_current_session', return_value={'duration_seconds': 100})
    mocker.patch.object(mock_db, 'get_unsynced_sessions', return_value=[])
    
    result = runner.invoke(app, ["finish"])
    
    assert result.exit_code == 0
    assert "No open PR found" in result.stdout

def test_finish_cleanup_failure(mock_db, mock_git, mock_config, mock_asana, mocker):
    """
    Test graceful handling of cleanup failure.
    """
    mocker.patch("gittask.commands.finish.db", mock_db)
    mocker.patch("gittask.commands.finish.git", mock_git)
    mocker.patch("gittask.commands.finish.config", mock_config)
    mocker.patch("gittask.commands.finish.AsanaClient", return_value=mock_asana)
    
    # Mock GitHub to return no PRs to skip that part
    mock_repo = MagicMock()
    mock_repo.get_pulls.return_value = MagicMock(totalCount=0)
    mocker.patch("gittask.commands.finish.get_github_repo", return_value=mock_repo)
    mocker.patch("gittask.commands.finish.get_github_client")

    mock_questionary = mocker.patch("gittask.commands.finish.questionary")
    mock_questionary.confirm.return_value.ask.return_value = True
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={'asana_task_gid': '123', 'asana_task_name': 'Task'})
    mocker.patch.object(mock_db, 'stop_current_session', return_value={'duration_seconds': 100})
    mocker.patch.object(mock_db, 'get_unsynced_sessions', return_value=[])
    
    # Mock subprocess failure during cleanup
    mock_subprocess = mocker.patch("gittask.commands.finish.subprocess.run")
    mock_subprocess.side_effect = Exception("Git error")
    
    result = runner.invoke(app, ["finish"])
    
    assert result.exit_code == 0
    assert "Cleanup failed: Git error" in result.stdout
