from tinydb import TinyDB, Query
import os
from typing import Optional, Dict, List
import time
import uuid

class DBManager:
    def __init__(self, db_path: str = "db.json"):
        self.db = TinyDB(db_path)
        self.branch_map = self.db.table('branch_map')
        self.time_sessions = self.db.table('time_sessions')
        self.config = self.db.table('config')

    # Branch Map Operations
    def get_task_for_branch(self, branch_name: str) -> Optional[Dict]:
        Branch = Query()
        result = self.branch_map.search(Branch.branch_name == branch_name)
        return result[0] if result else None

    def link_branch_to_task(self, branch_name: str, task_gid: str, task_name: str, project_gid: str, workspace_gid: str):
        self.branch_map.upsert({
            'branch_name': branch_name,
            'asana_task_gid': task_gid,
            'asana_task_name': task_name,
            'project_gid': project_gid,
            'workspace_gid': workspace_gid
        }, Query().branch_name == branch_name)

    # Time Session Operations
    def start_session(self, branch_name: str, task_gid: str):
        session_id = str(uuid.uuid4())
        self.time_sessions.insert({
            'id': session_id,
            'branch': branch_name,
            'task_gid': task_gid,
            'start_time': time.time(),
            'end_time': None,
            'duration_seconds': 0,
            'synced_to_asana': False
        })
        return session_id

    def stop_current_session(self, branch_name: str):
        Session = Query()
        # Find open session for this branch
        open_sessions = self.time_sessions.search(
            (Session.branch == branch_name) & (Session.end_time == None)
        )
        
        if open_sessions:
            for session in open_sessions:
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
        return None

    def get_unsynced_sessions(self) -> List[Dict]:
        Session = Query()
        return self.time_sessions.search(Session.synced_to_asana == False)

    def mark_session_synced(self, session_id: str):
        Session = Query()
        self.time_sessions.update({'synced_to_asana': True}, Session.id == session_id)
