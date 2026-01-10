import typer
from rich.console import Console
from ..config import ConfigManager
from ..database import DBManager
from ..git_handler import GitHandler
from ..asana_client import AsanaClient
from .pr import get_github_client, get_github_repo
import questionary
import subprocess

app = typer.Typer()
console = Console()
config = ConfigManager()
db = DBManager()
git = GitHandler()

@app.command()
def finish():
    """
    Complete the current task: Stop timer, Merge PR, Close Asana Task, Cleanup.
    """
    current_branch = git.get_current_branch()
    repo_path = git.get_repo_root()
    task_info = db.get_task_for_branch(current_branch, repo_path)
    
    if not task_info:
        console.print("[yellow]Current branch is not linked to an Asana task.[/yellow]")
        if not questionary.confirm("Do you want to proceed with cleanup anyway?").ask():
            raise typer.Exit()

    # 1. Stop Timer
    console.print("⏱️  Stopping timer...")
    session = db.stop_current_session(current_branch, repo_path)
    if session:
        console.print(f"[green]Stopped session ({int(session['duration_seconds'] // 60)}m).[/green]")
    else:
        console.print("No active session.")

    # 1.5 Sync Time
    console.print("🔄 Syncing time to Asana...")
    token = config.get_api_token()
    if token:
        try:
            with AsanaClient(token) as client:
                unsynced = db.get_unsynced_sessions()
                # Filter for current branch
                sessions_to_sync = [s for s in unsynced if s['end_time'] is not None and s['branch'] == current_branch]
                
                if sessions_to_sync:
                    for session in sessions_to_sync:
                        if config.get_paid_plan_status():
                            client.add_time_entry(session['task_gid'], session['duration_seconds'])
                        else:
                            client.log_time_comment(session['task_gid'], session['duration_seconds'], session['branch'])
                        db.mark_session_synced(session['id'])
                    console.print(f"[green]Synced {len(sessions_to_sync)} sessions.[/green]")
                else:
                    console.print("No time to sync for this branch.")
        except Exception as e:
             console.print(f"[red]Failed to sync time: {e}[/red]")

    # 2. Check & Merge PR
    console.print("🔍 Checking for open Pull Requests...")
    try:
        g = get_github_client()
        repo = get_github_repo(g)
        pulls = repo.get_pulls(head=f"{repo.owner.login}:{current_branch}", state='open')
        
        if pulls.totalCount > 0:
            pr = pulls[0]
            console.print(f"Found PR #{pr.number}: {pr.title}")
            if questionary.confirm(f"Merge Pull Request #{pr.number}?").ask():
                try:
                    pr.merge()
                    console.print("[green]PR Merged![/green]")
                except Exception as e:
                    console.print(f"[red]Failed to merge PR: {e}[/red]")
        else:
            console.print("No open PR found for this branch.")
    except Exception as e:
        console.print(f"[red]Error checking PRs: {e}[/red]")

    # 3. Close Asana Task
    if task_info:
        if questionary.confirm(f"Mark Asana task '{task_info['asana_task_name']}' as completed?").ask():
            token = config.get_api_token()
            if token:
                try:
                    with AsanaClient(token) as client:
                        client.complete_task(task_info['asana_task_gid'])
                        console.print(f"[green]Asana task completed![/green]")
                except Exception as e:
                    console.print(f"[red]Failed to complete Asana task: {e}[/red]")
            else:
                console.print("[yellow]Not authenticated with Asana.[/yellow]")

    # 4. Cleanup
    if questionary.confirm("Cleanup local branch? (Checkout main & delete)").ask():
        try:
            # Checkout main
            console.print("Switching to main...")
            git.checkout_branch("main")
            
            # Pull latest
            console.print("Pulling latest changes...")
            subprocess.run(["git", "pull"], check=True)
            
            # Delete branch
            console.print(f"Deleting {current_branch}...")
            subprocess.run(["git", "branch", "-d", current_branch], check=True)
            console.print("[green]Cleanup complete![/green]")
            
        except Exception as e:
            console.print(f"[red]Cleanup failed: {e}[/red]")
            console.print("You may need to manually delete the branch if it wasn't fully merged.")
