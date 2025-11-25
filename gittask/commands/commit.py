import typer
from rich.console import Console
from ..config import ConfigManager
from ..database import DBManager
from ..git_handler import GitHandler
from ..asana_client import AsanaClient
import subprocess

console = Console()
config = ConfigManager()
db = DBManager()
git = GitHandler()

def commit(
    message: str = typer.Option(..., "-m", "--message", help="Commit message"),
    all_files: bool = typer.Option(False, "-a", "--all", help="Stage all modified files"),
):
    """
    Commit changes and post the message to the linked Asana task.
    """
    current_branch = git.get_current_branch()
    task_info = db.get_task_for_branch(current_branch)
    
    # 1. Perform the git commit
    cmd = ["git", "commit", "-m", message]
    if all_files:
        cmd.insert(2, "-a")
        
    try:
        subprocess.run(cmd, check=True)
        console.print("[green]Commit successful.[/green]")
    except subprocess.CalledProcessError:
        # Git commit failed (e.g., nothing to commit)
        raise typer.Exit(code=1)
        
    try:
        subprocess.run(cmd, check=True)
        console.print("[green]Commit successful.[/green]")
    except subprocess.CalledProcessError:
        # Git commit failed (e.g., nothing to commit)
        raise typer.Exit(code=1)
        
    # Asana posting moved to 'push' command
