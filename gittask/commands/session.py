import typer
from rich.console import Console
from ..database import DBManager
from ..git_handler import GitHandler

app = typer.Typer()
console = Console()
db = DBManager()

@app.command()
def stop():
    """
    Stop the current time tracking session (branch or global).
    """
    # 1. Try to stop session for current branch (if in a git repo)
    try:
        git = GitHandler()
        current_branch = git.get_current_branch()
        repo_path = git.get_repo_root()
        
        if current_branch != "DETACHED_HEAD":
            stopped_session = db.stop_current_session(current_branch, repo_path)
            if stopped_session:
                duration_mins = int(stopped_session['duration_seconds'] // 60)
                console.print(f"[yellow]Stopped tracking time for '{current_branch}' ({duration_mins}m).[/yellow]")
                return
    except Exception:
        # Not in a git repo or other git error, ignore and try stopping global session
        pass

    # 2. If no branch session stopped, try to stop any global session
    # Or actually, just stop ANY active session to be safe/consistent with "one session at a time"
    stopped_session = db.stop_any_active_session()
    
    if stopped_session:
        duration_mins = int(stopped_session['duration_seconds'] // 60)
        branch_display = stopped_session['branch']
        if branch_display.startswith("@global:"):
            branch_display = branch_display.replace("@global:", "") + " (Global)"
            
        console.print(f"[yellow]Stopped tracking time for '{branch_display}' ({duration_mins}m).[/yellow]")
    else:
        console.print(f"[yellow]No active session found.[/yellow]")

@app.command()
def start():
    """
    Start time tracking for the current branch.
    """
    try:
        git = GitHandler()
        current_branch = git.get_current_branch()
        repo_path = git.get_repo_root()
    except Exception:
        console.print("[red]Not in a git repository. Use 'gittask track' for global tasks.[/red]")
        raise typer.Exit(code=1)
    
    # Check if branch is linked
    task_info = db.get_task_for_branch(current_branch, repo_path)
    
    if not task_info:
        console.print(f"[red]Branch '{current_branch}' is not linked to an Asana task.[/red]")
        console.print("Run 'gittask checkout <branch>' to link it.")
        raise typer.Exit(code=1)
        
    # Check if already tracking THIS branch
    from tinydb import Query
    Session = Query()
    open_sessions = db.time_sessions.search(
        (Session.branch == current_branch) & 
        (Session.repo_path == repo_path) & 
        (Session.end_time == None)
    )
    
    if open_sessions:
        console.print(f"[yellow]Already tracking time for '{current_branch}'.[/yellow]")
    else:
        # This will auto-stop any other session (global or other repo)
        db.start_session(current_branch, repo_path, task_info['asana_task_gid'])
        console.print(f"[green]Started tracking time for '{current_branch}' -> '{task_info['asana_task_name']}'[/green]")
