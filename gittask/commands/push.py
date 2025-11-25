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

def push(
    remote: str = typer.Argument("origin", help="Remote name"),
    branch: str = typer.Argument(None, help="Branch name"),
):
    """
    Push changes to remote and post a summary of commits to the linked Asana task.
    """
    current_branch = git.get_current_branch()
    target_branch = branch or current_branch
    
    # 1. Identify commits to be pushed
    # We need to find the upstream branch to compare against
    upstream = f"{remote}/{target_branch}"
    
    # Check if upstream exists
    try:
        subprocess.run(["git", "rev-parse", "--verify", upstream], check=True, capture_output=True)
        has_upstream = True
    except subprocess.CalledProcessError:
        has_upstream = False
        
    commits = []
    if has_upstream:
        # Get log of commits that are in HEAD but not in upstream
        try:
            log_output = subprocess.check_output(
                ["git", "log", f"{upstream}..HEAD", "--pretty=format:%h|%s"],
                text=True
            ).strip()
            
            if log_output:
                for line in log_output.split('\n'):
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        commits.append({"hash": parts[0], "message": parts[1]})
        except subprocess.CalledProcessError:
            console.print("[yellow]Could not determine unpushed commits.[/yellow]")
    else:
        # If no upstream, all commits on this branch are "new" to the remote (conceptually)
        # But for simplicity, maybe we just push and don't try to list everything?
        # Or we list everything from main?
        # Let's try to list everything from main..HEAD if possible, or just skip.
        console.print("[yellow]First push for this branch. Skipping commit summary.[/yellow]")

    # 2. Push
    console.print(f"Pushing to {remote}/{target_branch}...")
    try:
        # We use simple git push. If it's a new branch, we might need --set-upstream
        # The user might have passed arguments, but we are wrapping it.
        # If the user didn't specify branch, we push current.
        
        cmd = ["git", "push"]
        if not has_upstream:
            cmd.extend(["--set-upstream", remote, target_branch])
        else:
            cmd.extend([remote, target_branch])
            
        subprocess.run(cmd, check=True)
        console.print("[green]Push successful.[/green]")
    except subprocess.CalledProcessError:
        raise typer.Exit(code=1)

    # 3. Post to Asana
    if commits:
        task_info = db.get_task_for_branch(current_branch)
        if task_info:
            token = config.get_api_token()
            if not token:
                console.print("[yellow]Not authenticated with Asana. Skipping comment.[/yellow]")
                return

            try:
                with AsanaClient(token) as client:
                    # Build comment
                    # Get repo URL for links
                    repo_url = "https://github.com/AndreasLF/gittask" # TODO: Get this dynamically if possible
                    
                    lines = [f"🚀 **Pushed to `{target_branch}`**"]
                    for c in commits:
                        url = f"{repo_url}/commit/{c['hash']}"
                        lines.append(f"• [`{c['hash']}`]({url}) - {c['message']}")
                    
                    comment_text = "\n".join(lines)
                    client.post_comment(task_info['asana_task_gid'], comment_text)
                    console.print(f"[green]Posted push summary to Asana task: {task_info['asana_task_name']}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to post comment to Asana: {e}[/red]")
        else:
            console.print("[yellow]Branch not linked to Asana task. Skipping comment.[/yellow]")
