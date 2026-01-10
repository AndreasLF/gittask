import pytest
from typer.testing import CliRunner
from gittask.main import app
from unittest.mock import MagicMock

runner = CliRunner()

def test_tags_list_success(mock_db, mock_git, mock_config, mock_asana, mocker):
    """
    Test listing tags for a task.
    """
    mocker.patch("gittask.commands.tags.db", mock_db)
    mocker.patch("gittask.commands.tags.git", mock_git)
    mocker.patch("gittask.commands.tags.config", mock_config)
    mocker.patch("gittask.commands.tags.AsanaClient", return_value=mock_asana)
    
    mock_git.get_current_branch.return_value = "feature-branch"
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={
        'asana_task_gid': 'task123',
        'asana_task_name': 'Feature Task'
    })
    
    # Mock Asana task details
    mock_task = {
        'name': 'Feature Task',
        'tags': [
            {'name': 'Tag1', 'color': 'red'},
            {'name': 'Tag2', 'color': None}
        ]
    }
    mock_asana.__enter__.return_value.tasks_api.get_task.return_value = mock_task
    
    result = runner.invoke(app, ["tags"])
    
    assert result.exit_code == 0
    assert "Tags for task: Feature Task" in result.stdout
    assert "Tag1" in result.stdout
    assert "red" in result.stdout
    assert "Tag2" in result.stdout
    assert "default" in result.stdout

def test_tags_list_no_tags(mock_db, mock_git, mock_config, mock_asana, mocker):
    """
    Test listing tags when task has no tags.
    """
    mocker.patch("gittask.commands.tags.db", mock_db)
    mocker.patch("gittask.commands.tags.git", mock_git)
    mocker.patch("gittask.commands.tags.config", mock_config)
    mocker.patch("gittask.commands.tags.AsanaClient", return_value=mock_asana)
    
    mock_git.get_current_branch.return_value = "feature-branch"
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={
        'asana_task_gid': 'task123'
    })
    
    mock_task = {
        'name': 'Feature Task',
        'tags': []
    }
    mock_asana.__enter__.return_value.tasks_api.get_task.return_value = mock_task
    
    result = runner.invoke(app, ["tags"])
    
    assert result.exit_code == 0
    assert "No tags" in result.stdout

def test_tags_list_not_linked(mock_db, mock_git, mocker):
    """
    Test listing tags when branch is not linked.
    """
    mocker.patch("gittask.commands.tags.db", mock_db)
    mocker.patch("gittask.commands.tags.git", mock_git)
    
    mock_git.get_current_branch.return_value = "feature-branch"
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value=None)
    
    result = runner.invoke(app, ["tags"])
    
    assert result.exit_code == 1
    assert "not linked to an Asana task" in result.stdout

def test_tags_add_success(mock_db, mock_git, mock_config, mock_asana, mocker):
    """
    Test adding tags to a task.
    """
    mocker.patch("gittask.commands.tags.db", mock_db)
    mocker.patch("gittask.commands.tags.git", mock_git)
    mocker.patch("gittask.commands.tags.config", mock_config)
    mocker.patch("gittask.commands.tags.AsanaClient", return_value=mock_asana)
    
    mock_git.get_current_branch.return_value = "feature-branch"
    
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value={
        'asana_task_gid': 'task123'
    })
    
    # Mock select_and_create_tags
    mocker.patch("gittask.commands.tags.select_and_create_tags", return_value=['tag1', 'tag2'])
    
    result = runner.invoke(app, ["tags", "add"])
    
    assert result.exit_code == 0
    assert "Applying 2 tags..." in result.stdout
    assert "Tags added successfully" in result.stdout
    
    mock_asana.__enter__.return_value.add_tag_to_task.assert_has_calls([
        mocker.call('task123', 'tag1'),
        mocker.call('task123', 'tag2')
    ])

def test_tags_add_not_linked(mock_db, mock_git, mocker):
    """
    Test adding tags when branch is not linked.
    """
    mocker.patch("gittask.commands.tags.db", mock_db)
    mocker.patch("gittask.commands.tags.git", mock_git)
    
    mock_git.get_current_branch.return_value = "feature-branch"
    mocker.patch.object(mock_db, 'get_task_for_branch', return_value=None)
    
    result = runner.invoke(app, ["tags", "add"])
    
    assert result.exit_code == 1
    assert "not linked to an Asana task" in result.stdout
