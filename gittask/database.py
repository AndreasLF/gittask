from tinydb import TinyDB, Query
import os
from typing import Optional, Dict, List
import time
import uuid
from pathlib import Path
from .utils import get_git_root

class DBManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use global config directory
            home = Path.home()
            config_dir = home / ".gittask"
            config_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(config_dir / "db.json")
            
        self.db = TinyDB(db_path)
        self.branch_map = self.db.table('branch_map')
        self.time_sessions = self.db.table('time_sessions')
        self.config = self.db.table('config')
        self.tags = self.db.table('tags')

    # Tag Operations
    def cache_tags(self, tags: List[Dict]):
        """
        Cache a list of tags. Each tag should have 'gid' and 'name'.
        """
        # Clear existing cache or upsert? Upsert is better but clearing might be safer for sync.
        # Let's truncate and replace for simplicity to handle deletions/renames on Asana side.
        self.tags.truncate()
        self.tags.insert_multiple(tags)

    def get_cached_tags(self) -> List[Dict]:
        return self.tags.all()

    # Branch Map Operations
    def get_task_for_branch(self, branch_name: str, repo_path: str) -> Optional[Dict]:
        Branch = Query()
        result = self.branch_map.search(
            (Branch.branch_name == branch_name) & (Branch.repo_path == repo_path)
        )
        return result[0] if result else None

    def link_branch_to_task(self, branch_name: str, repo_path: str, task_gid: str, task_name: str, project_gid: str, workspace_gid: str):
        Branch = Query()
        self.branch_map.upsert({
            'branch_name': branch_name,
            'repo_path': repo_path,
            'asana_task_gid': task_gid,
            'asana_task_name': task_name,
            'project_gid': project_gid,
            'workspace_gid': workspace_gid
        }, (Branch.branch_name == branch_name) & (Branch.repo_path == repo_path))

    def remove_branch_link(self, branch_name: str, repo_path: str):
        Branch = Query()
        self.branch_map.remove(
            (Branch.branch_name == branch_name) & (Branch.repo_path == repo_path)
        )

    # Time Session Operations
    def start_session(self, branch_name: str, repo_path: str, task_gid: str):
        # Enforce single active session: Stop ANY other active session first
        self.stop_any_active_session()

        session_id = str(uuid.uuid4())
        self.time_sessions.insert({
            'id': session_id,
            'branch': branch_name,
            'repo_path': repo_path,
            'task_gid': task_gid,
            'start_time': time.time(),
            'end_time': None,
            'duration_seconds': 0,
            'synced_to_asana': False
        })
        return session_id

    def stop_current_session(self, branch_name: str, repo_path: str):
        Session = Query()
        # Find open session for this branch and repo
        open_sessions = self.time_sessions.search(
            (Session.branch == branch_name) & 
            (Session.repo_path == repo_path) & 
            (Session.end_time == None)
        )
        
        if open_sessions:
            for session in open_sessions:
                return self._close_session(session)
        return None

    def stop_any_active_session(self):
        """
        Stop any currently active session, regardless of branch or repo.
        Returns the closed session if one was found, else None.
        """
        Session = Query()
        open_sessions = self.time_sessions.search(Session.end_time == None)
        
        if open_sessions:
            # Should theoretically only be one, but let's close all just in case
            last_closed = None
            for session in open_sessions:
                last_closed = self._close_session(session)
            return last_closed
        return None

    def _close_session(self, session):
        end_time = time.time()
        start_time = session['start_time']
        duration = end_time - start_time
        self.time_sessions.update({
            'end_time': end_time,
            'duration_seconds': duration
        }, doc_ids=[session.doc_id])
        
        # Return the updated session data
        session['end_time'] = end_time
        session['duration_seconds'] = duration
        return session

    def get_active_session(self) -> Optional[Dict]:
        Session = Query()
        open_sessions = self.time_sessions.search(Session.end_time == None)
        return open_sessions[0] if open_sessions else None

    def get_unsynced_sessions(self) -> List[Dict]:
        Session = Query()
        return self.time_sessions.search(Session.synced_to_asana == False)

    def mark_session_synced(self, session_id: str):
        Session = Query()
        self.time_sessions.update({'synced_to_asana': True}, Session.id == session_id)
