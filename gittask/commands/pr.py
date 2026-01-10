import typer
from rich.console import Console
from rich.table import Table
from ..config import ConfigManager
from ..database import DBManager
from ..git_handler import GitHandler
from ..asana_client import AsanaClient
from github import Github
import subprocess

app = typer.Typer()
console = Console()
config = ConfigManager()
db = DBManager()
git = GitHandler()

def get_github_client():
    token = config.get_github_token()
    if not token:
        console.print("[red]GitHub token not found. Run `gittask auth login --github` first.[/red]")
        raise typer.Exit(code=1)
    return Github(token)

def get_github_repo(g, remote_name="origin"):
    remote_url = git.get_remote_url(remote_name)
    if not remote_url:
        console.print(f"[red]Could not find remote '{remote_name}'.[/red]")
        raise typer.Exit(code=1)
    
    # Extract owner/repo from URL
    # Supports:
    # https://github.com/owner/repo.git
    # git@github.com:owner/repo.git
    
    if remote_url.endswith(".git"):
        remote_url = remote_url[:-4]
        
    if "github.com" not in remote_url:
         console.print("[red]Remote is not a GitHub repository.[/red]")
         raise typer.Exit(code=1)

    if remote_url.startswith("git@"):
        parts = remote_url.split(":")
        if len(parts) != 2:
             console.print("[red]Invalid SSH URL format.[/red]")
             raise typer.Exit(code=1)
        repo_path = parts[1]
    else:
        # HTTPS
        parts = remote_url.split("github.com/")
        if len(parts) != 2:
             console.print("[red]Invalid HTTPS URL format.[/red]")
             raise typer.Exit(code=1)
        repo_path = parts[1]
        
    return g.get_repo(repo_path)

@app.command()
def create(
    base: str = typer.Option("main", help="Base branch for PR"),
    draft: bool = typer.Option(False, help="Create as draft PR")
):
    """
    Push current branch and create a Pull Request linked to the Asana task.
    """
    current_branch = git.get_current_branch()
    repo_path = git.get_repo_root()
    task_info = db.get_task_for_branch(current_branch, repo_path)
    
    if not task_info:
        console.print("[yellow]Branch not linked to Asana task. Using branch name as title.[/yellow]")
        title = current_branch
        body = ""
    else:
        title = task_info['asana_task_name']
        # Asana task URL isn't stored directly, but we can construct it or fetch it.
        # For now, let's just put the task name and GID.
        # Ideally we should store the permalink or fetch it.
        # Let's just use a generic format: https://app.asana.com/0/0/{task_gid}
        body = f"Asana Task: https://app.asana.com/0/0/{task_info['asana_task_gid']}"

    # 1. Push changes
    console.print(f"Pushing {current_branch} to origin...")
    try:
        subprocess.run(["git", "push", "-u", "origin", current_branch], check=True)
    except subprocess.CalledProcessError:
        console.print("[red]Failed to push branch.[/red]")
        raise typer.Exit(code=1)

    # 2. Create PR
    g = get_github_client()
    repo = get_github_repo(g)
    
    try:
        pr = repo.create_pull(
            title=title,
            body=body,
            head=current_branch,
            base=base,
            draft=draft
        )
        console.print(f"[green]PR Created Successfully![/green]")
        console.print(f"URL: {pr.html_url}")
        
        # Post to Asana
        if task_info:
            token = config.get_api_token()
            if token:
                try:
                    with AsanaClient(token) as client:
                        comment_text = f"🔗 <strong>Pull Request Created</strong>\n\n<a href=\"{pr.html_url}\">{pr.title} (#{pr.number})</a>"
                        client.post_comment(task_info['asana_task_gid'], comment_text)
                        console.print(f"[green]Posted PR link to Asana task: {task_info['asana_task_name']}[/green]")
                except Exception as e:
                    console.print(f"[red]Failed to post PR link to Asana: {e}[/red]")
                    
    except Exception as e:
        # Check if PR already exists
        if "A pull request already exists" in str(e):
            console.print("[yellow]A pull request already exists for this branch.[/yellow]")
            # Try to find the existing PR
            pulls = repo.get_pulls(head=f"{repo.owner.login}:{current_branch}")
            if pulls.totalCount > 0:
                pr = pulls[0]
                console.print(f"URL: {pr.html_url}")
            else:
                console.print(f"[red]Could not find existing PR URL.[/red]")
        else:
            console.print(f"[red]Failed to create PR: {e}[/red]")

@app.command(name="list")
def list_prs():
    """
    List open Pull Requests.
    """
    g = get_github_client()
    repo = get_github_repo(g)
    
    table = Table(title=f"Open PRs for {repo.full_name}")
    table.add_column("Number", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Author", style="magenta")
    table.add_column("URL", style="blue")
    
    for pr in repo.get_pulls(state='open'):
        table.add_row(str(pr.number), pr.title, pr.user.login, pr.html_url)
        
    console.print(table)
