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
        
    # 2. Post to Asana if linked
    if task_info:
        token = config.get_api_token()
        if not token:
            console.print("[yellow]Not authenticated with Asana. Skipping comment.[/yellow]")
            return

        try:
            with AsanaClient(token) as client:
                comment_text = f"💻 **Commit on `{current_branch}`**\n\n{message}"
                client.post_comment(task_info['asana_task_gid'], comment_text)
                console.print(f"[green]Posted commit message to Asana task: {task_info['asana_task_name']}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to post comment to Asana: {e}[/red]")
    else:
        console.print("[yellow]Branch not linked to Asana task. Skipping comment.[/yellow]")
