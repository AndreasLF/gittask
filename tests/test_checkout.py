import pytest
from typer.testing import CliRunner
from gittask.main import app
from unittest.mock import MagicMock

runner = CliRunner()

def test_checkout_new_branch_create_task(mock_db, mock_asana, mock_config, mock_git, mocker):
    """
    Test checking out a new branch and creating a new Asana task.
    """
    mocker.patch("gittask.commands.checkout.DBManager", return_value=mock_db)
    mocker.patch("gittask.commands.checkout.GitHandler", return_value=mock_git)
    
    # Mock git behavior
    mock_git.get_current_branch.return_value = "main"
    
    # Mock Asana behavior
    mock_asana.__enter__.return_value.get_project_tasks.return_value = []
    mock_asana.__enter__.return_value.create_task.return_value = {'gid': 'new_task_gid', 'name': 'feature-branch'}
    
    # Mock user input
    mock_questionary = mocker.patch("gittask.commands.checkout.questionary")
    mock_questionary.text.return_value.ask.return_value = "feature-branch" # Task name input
    mock_questionary.confirm.return_value.ask.return_value = True # Create task? Yes
    
    # Mock tag selection
    mocker.patch("gittask.commands.checkout.select_and_create_tags", return_value=[])
    
    result = runner.invoke(app, ["checkout", "-b", "feature-branch"])
    
    assert result.exit_code == 0
    
    # Verify git checkout called
    mock_git.checkout_branch.assert_called_with("feature-branch", create_new=True)
    
    # Verify task created
    mock_asana.__enter__.return_value.create_task.assert_called()
    
    # Verify DB link
    task_info = mock_db.get_task_for_branch("feature-branch", "/tmp/mock_repo")
    assert task_info is not None
    assert task_info['asana_task_gid'] == 'new_task_gid'
    
    # Verify session started
    sessions = mock_db.time_sessions.all()
    assert len(sessions) == 1
    assert sessions[0]['branch'] == "feature-branch"

def test_checkout_existing_branch_already_linked(mock_db, mock_asana, mock_config, mock_git, mocker):
    """
    Test checking out an existing branch that is already linked.
    """
    mocker.patch("gittask.commands.checkout.DBManager", return_value=mock_db)
    mocker.patch("gittask.commands.checkout.GitHandler", return_value=mock_git)
    
    # Pre-link the branch
    mock_db.link_branch_to_task("existing-branch", "/tmp/mock_repo", "task_gid", "Task Name", "proj", "work")
    
    mock_git.get_current_branch.return_value = "main"
    
    result = runner.invoke(app, ["checkout", "existing-branch"])
    
    assert result.exit_code == 0
    assert "Switched to branch existing-branch" in result.stdout
    assert "Started tracking time" in result.stdout
    
    # Verify session started
    sessions = mock_db.time_sessions.all()
    assert len(sessions) == 1
    assert sessions[0]['branch'] == "existing-branch"

def test_checkout_main_skipped(mock_db, mock_asana, mock_config, mock_git, mocker):
    """
    Test that checking out main skips Asana linking.
    """
    mocker.patch("gittask.commands.checkout.DBManager", return_value=mock_db)
    mocker.patch("gittask.commands.checkout.GitHandler", return_value=mock_git)
    
    mock_git.get_current_branch.return_value = "feature"
    
    result = runner.invoke(app, ["checkout", "main"])
    
    assert result.exit_code == 0
    assert "skipped for Asana linking" in result.stdout
    
    # Verify NO session started
    sessions = mock_db.time_sessions.all()
    assert len(sessions) == 0

def test_checkout_stops_current_session(mock_db, mock_asana, mock_config, mock_git, mocker):
    """
    Test that checkout stops the current session before switching.
    """
    mocker.patch("gittask.commands.checkout.DBManager", return_value=mock_db)
    mocker.patch("gittask.commands.checkout.GitHandler", return_value=mock_git)
    
    # Start a session for current branch
    mock_db.start_session("current-branch", "/tmp/mock_repo", "gid")
    
    mock_git.get_current_branch.return_value = "current-branch"
    
    # Pre-link target branch
    mock_db.link_branch_to_task("target-branch", "/tmp/mock_repo", "gid2", "Task 2", "proj", "work")
    
    result = runner.invoke(app, ["checkout", "target-branch"])
    
    assert result.exit_code == 0
    
    # Verify old session stopped
    old_session = mock_db.time_sessions.get(doc_id=1)
    assert old_session['end_time'] is not None
    
    # Verify new session started
    new_session = mock_db.time_sessions.get(doc_id=2)
    assert new_session['branch'] == "target-branch"
    assert new_session['end_time'] is None
