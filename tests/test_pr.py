import pytest
from typer.testing import CliRunner
from gittask.main import app
from unittest.mock import MagicMock
import subprocess

runner = CliRunner()

def test_pr_create_success(mock_db, mock_git, mock_config, mock_asana, mocker):
    """
    Test successful PR creation.
    """
    mocker.patch("gittask.commands.pr.db", mock_db)
    mocker.patch("gittask.commands.pr.git", mock_git)
    mocker.patch("gittask.commands.pr.config", mock_config)
    mocker.patch("gittask.commands.pr.AsanaClient", return_value=mock_asana)
    
    # Mock GitHub
    mock_gh_client = MagicMock()
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_pr.html_url = "http://github.com/owner/repo/pull/1"
    mock_pr.title = "PR Title"
    mock_pr.number = 1
    
    mock_repo.create_pull.return_value = mock_pr
    
    mocker.patch("gittask.commands.pr.get_github_client", return_value=mock_gh_client)
    mocker.patch("gittask.commands.pr.get_github_repo", return_value=mock_repo)
    
    # Mock subprocess (push)
    mock_subprocess = mocker.patch("gittask.commands.pr.subprocess")
    mock_subprocess.run.return_value.returncode = 0
    
    mock_git.get_current_branch.return_value = "feature-branch"
    mock_git.get_repo_root.return_value = "/tmp/repo"
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={
        'asana_task_gid': 'task123',
        'asana_task_name': 'Feature Task'
    })
    
    result = runner.invoke(app, ["pr", "create"])
    
    assert result.exit_code == 0
    assert "PR Created Successfully" in result.stdout
    assert "Posted PR link" in result.stdout
    
    mock_repo.create_pull.assert_called_once()
    mock_asana.__enter__.return_value.post_comment.assert_called_once()

def test_pr_create_already_exists(mock_db, mock_git, mock_config, mock_asana, mocker):
    """
    Test PR creation when it already exists.
    """
    mocker.patch("gittask.commands.pr.db", mock_db)
    mocker.patch("gittask.commands.pr.git", mock_git)
    mocker.patch("gittask.commands.pr.config", mock_config)
    mocker.patch("gittask.commands.pr.AsanaClient", return_value=mock_asana)
    
    mock_gh_client = MagicMock()
    mock_repo = MagicMock()
    mock_repo.owner.login = "owner"
    
    # Simulate exception on create
    mock_repo.create_pull.side_effect = Exception("A pull request already exists")
    
    # Simulate finding existing PR
    existing_pr = MagicMock()
    existing_pr.html_url = "http://github.com/owner/repo/pull/1"
    mock_repo.get_pulls.return_value = MagicMock(totalCount=1, __getitem__=lambda s, i: existing_pr)
    
    mocker.patch("gittask.commands.pr.get_github_client", return_value=mock_gh_client)
    mocker.patch("gittask.commands.pr.get_github_repo", return_value=mock_repo)
    
    mock_subprocess = mocker.patch("gittask.commands.pr.subprocess")
    
    mock_git.get_current_branch.return_value = "feature-branch"
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={
        'asana_task_gid': 'task123',
        'asana_task_name': 'Feature Task'
    })
    
    result = runner.invoke(app, ["pr", "create"])
    
    assert result.exit_code == 0
    assert "A pull request already exists" in result.stdout
    assert "http://github.com/owner/repo/pull/1" in result.stdout

def test_pr_list(mock_git, mocker):
    """
    Test listing PRs.
    """
    mocker.patch("gittask.commands.pr.git", mock_git)
    
    mock_gh_client = MagicMock()
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    
    pr1 = MagicMock()
    pr1.number = 1
    pr1.title = "PR 1"
    pr1.user.login = "user1"
    pr1.html_url = "url1"
    
    mock_repo.get_pulls.return_value = [pr1]
    
    mocker.patch("gittask.commands.pr.get_github_client", return_value=mock_gh_client)
    mocker.patch("gittask.commands.pr.get_github_repo", return_value=mock_repo)
    
    result = runner.invoke(app, ["pr", "list"])
    
    assert result.exit_code == 0
    assert "Open PRs for owner/repo" in result.stdout
    assert "PR 1" in result.stdout
