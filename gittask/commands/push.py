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
    
    # Determine range to log
    range_str = ""
    if has_upstream:
        range_str = f"{upstream}..HEAD"
    else:
        # If no upstream, compare against origin/main (assuming main is the base)
        # Or just list all commits if we can't determine base?
        # A safe bet is usually to compare against the default branch if it exists locally
        # But let's try to be smart. If we are on a feature branch, we likely branched off main.
        # So we want commits that are reachable from HEAD but not from origin/main.
        range_str = "origin/main..HEAD"

    try:
        log_output = subprocess.check_output(
            ["git", "log", range_str, "--pretty=format:%h|%s"],
            text=True,
            stderr=subprocess.DEVNULL # Suppress error if range is invalid
        ).strip()
        
        if log_output:
            for line in log_output.split('\n'):
                parts = line.split('|', 1)
                if len(parts) == 2:
                    commits.append({"hash": parts[0], "message": parts[1]})
    except subprocess.CalledProcessError:
        # Fallback: if range is invalid (e.g. origin/main doesn't exist), maybe just show last commit?
        # Or just skip summary.
        console.print("[yellow]Could not determine new commits. Skipping summary.[/yellow]")

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
                    remote_url = git.get_remote_url(remote)
                    repo_url = remote_url
                    
                    if remote_url:
                        # Convert SSH to HTTPS if needed
                        if remote_url.startswith("git@"):
                            repo_url = remote_url.replace(":", "/").replace("git@", "https://")
                        
                        # Remove .git suffix
                        if repo_url.endswith(".git"):
                            repo_url = repo_url[:-4]
                    else:
                        # No fallback, raise error
                        raise typer.Exit(code=1)
                    
                    branch_url = f"{repo_url}/tree/{target_branch}"
                    lines = [f"<body><strong>🚀 Pushed to <a href=\"{branch_url}\">{target_branch}</a></strong><ul>"]
                    for c in commits:
                        url = f"{repo_url}/commit/{c['hash']}"
                        lines.append(f"<li><a href=\"{url}\">{c['hash']}</a> - {c['message']}</li>")
                    lines.append("</ul></body>")
                    
                    comment_text = "".join(lines)
                    client.post_comment(task_info['asana_task_gid'], comment_text)
                    console.print(f"[green]Posted push summary to Asana task: {task_info['asana_task_name']}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to post comment to Asana: {e}[/red]")
        else:
            console.print("[yellow]Branch not linked to Asana task. Skipping comment.[/yellow]")
