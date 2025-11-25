import git
from typing import List, Optional
import os

class GitHandler:
    def __init__(self, repo_path: str = "."):
        try:
            self.repo = git.Repo(repo_path, search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            raise Exception("Not a git repository")

    def get_current_branch(self) -> str:
        try:
            return self.repo.active_branch.name
        except TypeError:
            # Detached HEAD
            return "DETACHED_HEAD"

    def list_branches(self) -> List[str]:
        return [head.name for head in self.repo.heads]

    def checkout_branch(self, branch_name: str, create_new: bool = False):
        if create_new:
            self.repo.git.checkout(b=branch_name)
        else:
            self.repo.git.checkout(branch_name)

    def get_repo_root(self) -> str:
        return self.repo.working_dir

    def get_remote_url(self, remote_name: str = "origin") -> Optional[str]:
        try:
            return self.repo.remote(remote_name).url
        except ValueError:
            return None
