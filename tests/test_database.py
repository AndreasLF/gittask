import pytest
from gittask.database import DBManager
import time
import os

@pytest.fixture
def db(tmp_path):
    """
    Fixture for a DBManager with a temporary database file.
    """
    db_path = tmp_path / "test_db.json"
    return DBManager(str(db_path))

def test_init_default_path(mocker):
    """
    Test initialization with default path.
    """
    mock_path = mocker.patch("gittask.database.Path")
    mock_home = mock_path.home.return_value
    mock_config_dir = mock_home / ".gittask"
    
    DBManager()
    
    mock_config_dir.mkdir.assert_called_with(parents=True, exist_ok=True)
    # We can't easily assert the TinyDB init path here without mocking TinyDB, 
    # but the directory creation confirms the logic path.

def test_cache_tags(db):
    tags = [{'gid': '1', 'name': 'Tag1'}, {'gid': '2', 'name': 'Tag2'}]
    db.cache_tags(tags)
    
    cached = db.get_cached_tags()
    assert len(cached) == 2
    assert cached == tags
    
    # Test truncate and replace
    new_tags = [{'gid': '3', 'name': 'Tag3'}]
    db.cache_tags(new_tags)
    
    cached = db.get_cached_tags()
    assert len(cached) == 1
    assert cached == new_tags

def test_branch_map_operations(db):
    # Link branch
    db.link_branch_to_task(
        branch_name="feature",
        repo_path="/repo",
        task_gid="t1",
        task_name="Task 1",
        project_gid="p1",
        workspace_gid="w1"
    )
    
    # Get task
    task = db.get_task_for_branch("feature", "/repo")
    assert task is not None
    assert task['asana_task_gid'] == "t1"
    assert task['asana_task_name'] == "Task 1"
    
    # Update link (upsert)
    db.link_branch_to_task(
        branch_name="feature",
        repo_path="/repo",
        task_gid="t2",
        task_name="Task 2",
        project_gid="p1",
        workspace_gid="w1"
    )
    
    task = db.get_task_for_branch("feature", "/repo")
    assert task['asana_task_gid'] == "t2"
    assert task['asana_task_name'] == "Task 2"
    
    # Get non-existent
    assert db.get_task_for_branch("other", "/repo") is None
    assert db.get_task_for_branch("feature", "/other_repo") is None

def test_session_start_stop(db):
    # Start session
    session_id = db.start_session("feature", "/repo", "t1")
    assert session_id is not None
    
    # Verify active
    active = db.get_active_session()
    assert active is not None
    assert active['id'] == session_id
    assert active['branch'] == "feature"
    assert active['end_time'] is None
    
    # Stop session
    stopped = db.stop_current_session("feature", "/repo")
    assert stopped is not None
    assert stopped['id'] == session_id
    assert stopped['end_time'] is not None
    assert stopped['duration_seconds'] >= 0
    
    # Verify no active
    assert db.get_active_session() is None

def test_single_active_session_enforcement(db):
    # Start first session
    id1 = db.start_session("feature1", "/repo", "t1")
    
    # Start second session (should stop first)
    id2 = db.start_session("feature2", "/repo", "t2")
    
    # Verify first is stopped
    sessions = db.time_sessions.all()
    s1 = next(s for s in sessions if s['id'] == id1)
    s2 = next(s for s in sessions if s['id'] == id2)
    
    assert s1['end_time'] is not None
    assert s2['end_time'] is None
    
    # Verify active is s2
    active = db.get_active_session()
    assert active['id'] == id2

def test_stop_any_active_session(db):
    db.start_session("feature", "/repo", "t1")
    
    stopped = db.stop_any_active_session()
    assert stopped is not None
    assert stopped['branch'] == "feature"
    assert stopped['end_time'] is not None
    
    # Test when none active
    assert db.stop_any_active_session() is None

def test_stop_current_session_specific(db):
    # Start session for branch A
    db.start_session("branchA", "/repo", "t1")
    
    # Try to stop branch B (should fail)
    assert db.stop_current_session("branchB", "/repo") is None
    
    # Try to stop branch A in different repo (should fail)
    assert db.stop_current_session("branchA", "/other") is None
    
    # Stop branch A
    assert db.stop_current_session("branchA", "/repo") is not None

def test_unsynced_sessions(db):
    # Create a session and stop it
    db.start_session("feature", "/repo", "t1")
    db.stop_any_active_session()
    
    unsynced = db.get_unsynced_sessions()
    assert len(unsynced) == 1
    assert unsynced[0]['synced_to_asana'] is False
    
    # Mark synced
    db.mark_session_synced(unsynced[0]['id'])
    
    unsynced = db.get_unsynced_sessions()
    assert len(unsynced) == 0
