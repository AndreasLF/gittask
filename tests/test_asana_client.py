import pytest
from unittest.mock import MagicMock, call
import datetime
from gittask.asana_client import AsanaClient

@pytest.fixture
def mock_asana_lib(mocker):
    return mocker.patch("gittask.asana_client.asana")

@pytest.fixture
def client(mock_asana_lib):
    # Setup default mocks for init
    mock_users_api = MagicMock()
    mock_asana_lib.UsersApi.return_value = mock_users_api
    mock_users_api.get_user.return_value = {'gid': 'user123', 'name': 'Test User'}
    
    return AsanaClient("fake_token")

def test_init(mock_asana_lib):
    mock_users_api = MagicMock()
    mock_asana_lib.UsersApi.return_value = mock_users_api
    mock_users_api.get_user.return_value = {'gid': 'user123', 'name': 'Test User'}
    
    client = AsanaClient("fake_token")
    
    assert client.me == {'gid': 'user123', 'name': 'Test User'}
    mock_asana_lib.Configuration.assert_called()
    mock_asana_lib.ApiClient.assert_called()
    mock_users_api.get_user.assert_called_with("me", opts={})

def test_context_manager(mock_asana_lib):
    mock_users_api = MagicMock()
    mock_asana_lib.UsersApi.return_value = mock_users_api
    mock_users_api.get_user.return_value = {'gid': 'user123'}
    
    # Mock pool on api_client
    mock_api_client = MagicMock()
    mock_asana_lib.ApiClient.return_value = mock_api_client
    mock_pool = MagicMock()
    mock_api_client.pool = mock_pool
    
    with AsanaClient("token") as client:
        assert client.me['gid'] == 'user123'
        
    mock_pool.close.assert_called_once()
    mock_pool.join.assert_called_once()

def test_get_user_gid(client):
    assert client.get_user_gid() == 'user123'

def test_search_tasks(client, mock_asana_lib):
    mock_typeahead = MagicMock()
    mock_asana_lib.TypeaheadApi.return_value = mock_typeahead
    # Re-init to attach mock
    client.typeahead_api = mock_typeahead
    
    mock_typeahead.typeahead_for_workspace.return_value = [{'gid': 't1', 'name': 'Task 1'}]
    
    results = client.search_tasks('ws1', 'query')
    
    assert results == [{'gid': 't1', 'name': 'Task 1'}]
    mock_typeahead.typeahead_for_workspace.assert_called_with(
        'ws1', 'task', {'query': 'query', 'opt_fields': 'name,gid,completed'}
    )

def test_create_task(client, mock_asana_lib):
    mock_tasks = MagicMock()
    mock_asana_lib.TasksApi.return_value = mock_tasks
    client.tasks_api = mock_tasks
    
    mock_tasks.create_task.return_value = {'gid': 'new_task'}
    
    # Test with project
    result = client.create_task('ws1', 'p1', 'New Task')
    
    assert result == {'gid': 'new_task'}
    expected_body = {
        "data": {
            "workspace": "ws1",
            "name": "New Task",
            "assignee": "user123",
            "projects": ["p1"]
        }
    }
    mock_tasks.create_task.assert_called_with(expected_body, opts={})
    
    # Test without project
    client.create_task('ws1', None, 'New Task 2')
    expected_body_no_proj = {
        "data": {
            "workspace": "ws1",
            "name": "New Task 2",
            "assignee": "user123"
        }
    }
    mock_tasks.create_task.assert_called_with(expected_body_no_proj, opts={})

def test_log_time_comment(client, mock_asana_lib):
    mock_stories = MagicMock()
    mock_asana_lib.StoriesApi.return_value = mock_stories
    client.stories_api = mock_stories
    
    # 1h 30m
    client.log_time_comment('t1', 5400, 'feature')
    
    args, kwargs = mock_stories.create_story_for_task.call_args
    body = args[0]
    text = body['data']['html_text']
    
    assert "1h 30m" in text
    assert "feature" in text
    assert "gittask cli tool" in text

def test_log_time_comment_less_than_minute(client, mock_asana_lib):
    mock_stories = MagicMock()
    mock_asana_lib.StoriesApi.return_value = mock_stories
    client.stories_api = mock_stories
    
    client.log_time_comment('t1', 30, 'feature')
    
    args, kwargs = mock_stories.create_story_for_task.call_args
    text = args[0]['data']['html_text']
    assert "&lt; 1m" in text

def test_post_comment(client, mock_asana_lib):
    mock_stories = MagicMock()
    mock_asana_lib.StoriesApi.return_value = mock_stories
    client.stories_api = mock_stories
    
    client.post_comment('t1', 'Hello')
    
    args, kwargs = mock_stories.create_story_for_task.call_args
    text = args[0]['data']['html_text']
    assert "<body>Hello" in text
    assert "gittask cli tool" in text

def test_complete_task(client, mock_asana_lib):
    mock_tasks = MagicMock()
    mock_asana_lib.TasksApi.return_value = mock_tasks
    client.tasks_api = mock_tasks
    
    client.complete_task('t1')
    
    mock_tasks.update_task.assert_called_with(
        {"data": {"completed": True}}, 't1', opts={}
    )

def test_get_workspaces(client, mock_asana_lib):
    mock_ws = MagicMock()
    mock_asana_lib.WorkspacesApi.return_value = mock_ws
    client.workspaces_api = mock_ws
    
    mock_ws.get_workspaces.return_value = [{'gid': 'ws1'}]
    
    assert client.get_workspaces() == [{'gid': 'ws1'}]

def test_get_workspace_by_gid(client, mock_asana_lib):
    mock_ws = MagicMock()
    mock_asana_lib.WorkspacesApi.return_value = mock_ws
    client.workspaces_api = mock_ws
    
    mock_ws.get_workspace.return_value = {'gid': 'ws1', 'name': 'WS'}
    
    assert client.get_workspace_by_gid('ws1') == {'gid': 'ws1', 'name': 'WS'}

def test_get_projects(client, mock_asana_lib):
    mock_projects = MagicMock()
    mock_asana_lib.ProjectsApi.return_value = mock_projects
    client.projects_api = mock_projects
    
    mock_projects.get_projects_for_workspace.return_value = [{'gid': 'p1'}]
    
    assert client.get_projects('ws1') == [{'gid': 'p1'}]

def test_get_tags(client, mock_asana_lib):
    mock_tags = MagicMock()
    mock_asana_lib.TagsApi.return_value = mock_tags
    client.tags_api = mock_tags
    
    mock_tags.get_tags_for_workspace.return_value = [{'gid': 'tag1'}]
    
    assert client.get_tags('ws1') == [{'gid': 'tag1'}]
    mock_tags.get_tags_for_workspace.assert_called_with('ws1', opts={'opt_fields': 'name,gid'})

def test_create_tag(client, mock_asana_lib):
    mock_tags = MagicMock()
    mock_asana_lib.TagsApi.return_value = mock_tags
    client.tags_api = mock_tags
    
    client.create_tag('ws1', 'Tag Name', 'red')
    
    expected_body = {"data": {"workspace": "ws1", "name": "Tag Name", "color": "red"}}
    mock_tags.create_tag.assert_called_with(expected_body, opts={})

def test_add_tag_to_task(client, mock_asana_lib):
    mock_tasks = MagicMock()
    mock_asana_lib.TasksApi.return_value = mock_tasks
    client.tasks_api = mock_tasks
    
    client.add_tag_to_task('t1', 'tag1')
    
    mock_tasks.add_tag_for_task.assert_called_with({"data": {"tag": "tag1"}}, 't1')

def test_get_project_tasks(client, mock_asana_lib):
    mock_tasks = MagicMock()
    mock_asana_lib.TasksApi.return_value = mock_tasks
    client.tasks_api = mock_tasks
    
    mock_tasks.get_tasks.return_value = [{'gid': 't1'}]
    
    assert client.get_project_tasks('p1') == [{'gid': 't1'}]
    
    args, kwargs = mock_tasks.get_tasks.call_args
    opts = kwargs['opts']
    assert opts['project'] == 'p1'
    assert opts['completed_since'] == 'now'

def test_assign_task(client, mock_asana_lib):
    mock_tasks = MagicMock()
    mock_asana_lib.TasksApi.return_value = mock_tasks
    client.tasks_api = mock_tasks
    
    client.assign_task('t1', 'user2')
    
    mock_tasks.update_task.assert_called_with(
        {"data": {"assignee": "user2"}}, 't1', opts={}
    )

def test_get_custom_fields(client, mock_asana_lib):
    mock_cf = MagicMock()
    mock_asana_lib.CustomFieldsApi.return_value = mock_cf
    client.custom_fields_api = mock_cf
    
    mock_cf.get_custom_fields_for_workspace.return_value = [{'gid': 'cf1'}]
    
    assert client.get_custom_fields('ws1') == [{'gid': 'cf1'}]

def test_get_task_with_fields(client, mock_asana_lib):
    mock_tasks = MagicMock()
    mock_asana_lib.TasksApi.return_value = mock_tasks
    client.tasks_api = mock_tasks
    
    client.get_task_with_fields('t1')
    
    args, kwargs = mock_tasks.get_task.call_args
    assert 'custom_fields' in kwargs['opts']['opt_fields']

def test_get_actual_time(client, mock_asana_lib):
    mock_tasks = MagicMock()
    mock_asana_lib.TasksApi.return_value = mock_tasks
    client.tasks_api = mock_tasks
    
    mock_tasks.get_task.return_value = {'actual_time_minutes': 120}
    
    assert client.get_actual_time('t1') == 120

def test_add_time_entry(client, mock_asana_lib):
    mock_time = MagicMock()
    mock_asana_lib.TimeTrackingEntriesApi.return_value = mock_time
    client.time_tracking_api = mock_time
    
    # Test with default date (today)
    client.add_time_entry('t1', 3600)
    
    args, kwargs = mock_time.create_time_tracking_entry.call_args
    body = args[0]
    assert body['data']['duration_minutes'] == 60
    assert body['data']['entered_on'] == datetime.date.today().isoformat()
    
    # Test with specific date
    date = datetime.date(2023, 1, 1)
    client.add_time_entry('t1', 120, entered_on=date)
    
    args, kwargs = mock_time.create_time_tracking_entry.call_args
    body = args[0]
    assert body['data']['duration_minutes'] == 2 # 120 seconds = 2 mins
    assert body['data']['entered_on'] == '2023-01-01'

def test_add_time_entry_rounding(client, mock_asana_lib):
    mock_time = MagicMock()
    mock_asana_lib.TimeTrackingEntriesApi.return_value = mock_time
    client.time_tracking_api = mock_time
    
    # 30 seconds -> 1 minute
    client.add_time_entry('t1', 30)
    
    args, kwargs = mock_time.create_time_tracking_entry.call_args
    assert args[0]['data']['duration_minutes'] == 1
