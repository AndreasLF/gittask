import keyring
import typer
from typing import Optional
from .database import DBManager
from tinydb import Query

APP_NAME = "gittask"
KEYRING_SERVICE = "gittask_asana_pat"
KEYRING_USERNAME = "user" # Simple single user for now

class ConfigManager:
    def __init__(self):
        self.db = DBManager()
        self.SERVICE_NAME = KEYRING_SERVICE

    def get_api_token(self) -> Optional[str]:
        return keyring.get_password(self.SERVICE_NAME, "api_token")

    def set_api_token(self, token: str):
        keyring.set_password(self.SERVICE_NAME, "api_token", token)

    def get_github_token(self) -> Optional[str]:
        return keyring.get_password(self.SERVICE_NAME, "github_token")

    def set_github_token(self, token: str):
        keyring.set_password(self.SERVICE_NAME, "github_token", token)

    def logout(self):
        try:
            keyring.delete_password(self.SERVICE_NAME, "api_token")
        except keyring.errors.PasswordDeleteError:
            pass
        try:
            keyring.delete_password(self.SERVICE_NAME, "github_token")
        except keyring.errors.PasswordDeleteError:
            pass

    def set_default_workspace(self, workspace_gid: str):
        self.db.config.upsert({'key': 'default_workspace', 'value': workspace_gid}, Query().key == 'default_workspace')

    def get_default_workspace(self) -> Optional[str]:
        res = self.db.config.search(Query().key == 'default_workspace')
        return res[0]['value'] if res else None

    def set_default_project(self, project_gid: str):
        from tinydb import Query
        self.db.config.upsert({'key': 'default_project', 'value': project_gid}, Query().key == 'default_project')

    def get_default_project(self) -> Optional[str]:
        from tinydb import Query
        res = self.db.config.search(Query().key == 'default_project')
        return res[0]['value'] if res else None
