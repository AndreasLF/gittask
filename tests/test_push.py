import pytest
from typer.testing import CliRunner
from gittask.main import app
from unittest.mock import MagicMock, call
import subprocess

runner = CliRunner()

def test_push_success_with_upstream(mock_db, mock_git, mock_config, mock_asana, mocker):
    """
    Test successful push when upstream exists.
    """
    mocker.patch("gittask.commands.push.db", mock_db)
    mocker.patch("gittask.commands.push.git", mock_git)
    mocker.patch("gittask.commands.push.config", mock_config)
    mocker.patch("gittask.commands.push.AsanaClient", return_value=mock_asana)
    
    # Mock subprocess
    mock_subprocess = mocker.patch("gittask.commands.push.subprocess")
    mock_subprocess.CalledProcessError = subprocess.CalledProcessError
    mock_subprocess.DEVNULL = subprocess.DEVNULL
    mock_subprocess.CalledProcessError = subprocess.CalledProcessError
    mock_subprocess.DEVNULL = subprocess.DEVNULL
    
    # Mock git behavior
    mock_git.get_current_branch.return_value = "feature-branch"
    mock_git.get_repo_root.return_value = "/tmp/repo"
    mock_git.get_remote_url.return_value = "https://github.com/owner/repo.git"
    
    # Mock upstream check (success)
    mock_subprocess.run.return_value.returncode = 0
    
    # Mock log output
    mock_subprocess.check_output.return_value = "hash1|Commit 1\nhash2|Commit 2"
    
    # Mock DB task
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={
        'asana_task_gid': 'task123',
        'asana_task_name': 'Feature Task'
    })
    
    result = runner.invoke(app, ["push"])
    
    assert result.exit_code == 0
    assert "Pushing to origin/feature-branch" in result.stdout
    assert "Push successful" in result.stdout
    assert "Posted push summary" in result.stdout
    
    # Verify push command
    mock_subprocess.run.assert_any_call(["git", "push", "origin", "feature-branch"], check=True)
    
    # Verify Asana comment
    mock_asana.__enter__.return_value.post_comment.assert_called_once()
    args, _ = mock_asana.__enter__.return_value.post_comment.call_args
    assert args[0] == 'task123'
    assert "Commit 1" in args[1]
    assert "Commit 2" in args[1]

def test_push_success_no_upstream(mock_db, mock_git, mock_config, mock_asana, mocker):
    """
    Test successful push when upstream does not exist (sets upstream).
    """
    mocker.patch("gittask.commands.push.db", mock_db)
    mocker.patch("gittask.commands.push.git", mock_git)
    mocker.patch("gittask.commands.push.config", mock_config)
    mocker.patch("gittask.commands.push.AsanaClient", return_value=mock_asana)
    
    mock_subprocess = mocker.patch("gittask.commands.push.subprocess")
    mock_subprocess.CalledProcessError = subprocess.CalledProcessError
    mock_subprocess.DEVNULL = subprocess.DEVNULL
    
    mock_git.get_current_branch.return_value = "new-branch"
    mock_git.get_repo_root.return_value = "/tmp/repo"
    mock_git.get_remote_url.return_value = "git@github.com:owner/repo.git"
    
    # Mock upstream check failure (no upstream)
    def run_side_effect(cmd, **kwargs):
        if "rev-parse" in cmd:
            raise subprocess.CalledProcessError(1, cmd)
        return MagicMock(returncode=0)
    
    mock_subprocess.run.side_effect = run_side_effect
    
    # Mock log output
    mock_subprocess.check_output.return_value = "hash1|Init"
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={
        'asana_task_gid': 'task123',
        'asana_task_name': 'Task'
    })
    
    result = runner.invoke(app, ["push"])
    
    assert result.exit_code == 0
    
    # Verify push with --set-upstream
    mock_subprocess.run.assert_any_call(["git", "push", "--set-upstream", "origin", "new-branch"], check=True)

def test_push_failure(mock_db, mock_git, mocker):
    """
    Test push failure.
    """
    mocker.patch("gittask.commands.push.db", mock_db)
    mocker.patch("gittask.commands.push.git", mock_git)
    
    mock_subprocess = mocker.patch("gittask.commands.push.subprocess")
    mock_subprocess.CalledProcessError = subprocess.CalledProcessError
    
    mock_git.get_current_branch.return_value = "main"
    
    # Mock push failure
    def run_side_effect(cmd, **kwargs):
        if "git" in cmd and "push" in cmd:
            raise subprocess.CalledProcessError(1, cmd)
        return MagicMock(returncode=0)
        
    mock_subprocess.run.side_effect = run_side_effect
    
    result = runner.invoke(app, ["push"])
    
    assert result.exit_code == 1

def test_push_no_task_linked(mock_db, mock_git, mock_config, mock_asana, mocker):
    """
    Test push when no task is linked (skips comment).
    """
    mocker.patch("gittask.commands.push.db", mock_db)
    mocker.patch("gittask.commands.push.git", mock_git)
    mocker.patch("gittask.commands.push.config", mock_config)
    mocker.patch("gittask.commands.push.AsanaClient", return_value=mock_asana)
    
    mock_subprocess = mocker.patch("gittask.commands.push.subprocess")
    mock_subprocess.check_output.return_value = "hash|msg"
    
    mock_git.get_current_branch.return_value = "branch"
    mock_git.get_repo_root.return_value = "/tmp/repo"
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value=None)
    
    result = runner.invoke(app, ["push"])
    
    assert result.exit_code == 0
    assert "Branch not linked to Asana task" in result.stdout
    
    mock_asana.__enter__.return_value.post_comment.assert_not_called()
