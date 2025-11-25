import asana
from typing import Optional, List, Dict
import datetime

class AsanaClient:
    def __init__(self, personal_access_token: str):
        configuration = asana.Configuration()
        configuration.access_token = personal_access_token
        self.api_client = asana.ApiClient(configuration)
        
        self.users_api = asana.UsersApi(self.api_client)
        self.tasks_api = asana.TasksApi(self.api_client)
        self.stories_api = asana.StoriesApi(self.api_client)
        self.workspaces_api = asana.WorkspacesApi(self.api_client)
        self.projects_api = asana.ProjectsApi(self.api_client)
        self.typeahead_api = asana.TypeaheadApi(self.api_client)
        
        # Get current user
        # v5 returns a dict directly
        self.me = self.users_api.get_user("me", opts={})

    def close(self):
        if hasattr(self.api_client, 'pool') and self.api_client.pool:
            self.api_client.pool.close()
            self.api_client.pool.join()
            del self.api_client.pool

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_user_gid(self) -> str:
        return self.me['gid']

    def search_tasks(self, workspace_gid: str, query: str) -> List[Dict]:
        """
        Search for tasks in a workspace using Typeahead.
        """
        opts = {
            "query": query,
            "opt_fields": "name,gid,completed"
        }
        result = self.typeahead_api.typeahead_for_workspace(
            workspace_gid,
            "task",
            opts
        )
        # Result is a generator, convert to list
        return list(result)

    def create_task(self, workspace_gid: str, project_gid: Optional[str], name: str) -> Dict:
        data = {
            "workspace": workspace_gid,
            "name": name,
            "assignee": self.me['gid']
        }
        if project_gid:
            data["projects"] = [project_gid]
            
        body = {"data": data}
        result = self.tasks_api.create_task(body, opts={})
        return result

    def log_time_comment(self, task_gid: str, duration_seconds: float, branch_name: str):
        """
        Log time as a comment on the task.
        """
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        
        time_str = []
        if hours > 0:
            time_str.append(f"{hours}h")
        if minutes > 0:
            time_str.append(f"{minutes}m")
            
        if not time_str:
            time_str.append("< 1m")
            
        text = f"⏱️ Worked {' '.join(time_str)} on branch `{branch_name}`."
        self.post_comment(task_gid, text)

    def post_comment(self, task_gid: str, text: str):
        """
        Post a comment to a task.
        """
        body = {"data": {"text": text}}
        self.stories_api.create_story_for_task(body, task_gid, opts={})

    def get_workspaces(self) -> List[Dict]:
        result = self.workspaces_api.get_workspaces(opts={})
        return list(result)

    def get_projects(self, workspace_gid: str) -> List[Dict]:
        result = self.projects_api.get_projects_for_workspace(workspace_gid, opts={})
        return list(result)
