import typer
from rich.console import Console
from ..database import DBManager
from ..git_handler import GitHandler

app = typer.Typer()
console = Console()
db = DBManager()
git = GitHandler()

@app.command()
def stop():
    """
    Stop the current time tracking session for the current branch.
    """
    current_branch = git.get_current_branch()
    
    # Check if there is an active session
    session = db.stop_current_session(current_branch)
    
    if session:
        duration_mins = int(session['duration_seconds'] // 60)
        console.print(f"[yellow]Stopped tracking time for '{current_branch}' ({duration_mins}m).[/yellow]")
    else:
        console.print(f"[yellow]No active session found for '{current_branch}'.[/yellow]")

@app.command()
def start():
    """
    Start time tracking for the current branch.
    """
    current_branch = git.get_current_branch()
    
    # Check if branch is linked
    task_info = db.get_task_for_branch(current_branch)
    
    if not task_info:
        console.print(f"[red]Branch '{current_branch}' is not linked to an Asana task.[/red]")
        console.print("Run 'gittask checkout <branch>' to link it.")
        raise typer.Exit(code=1)
        
    # Check if already tracking
    from tinydb import Query
    Session = Query()
    open_sessions = db.time_sessions.search(
        (Session.branch == current_branch) & (Session.end_time == None)
    )
    
    if open_sessions:
        console.print(f"[yellow]Already tracking time for '{current_branch}'.[/yellow]")
    else:
        db.start_session(current_branch, task_info['asana_task_gid'])
        console.print(f"[green]Started tracking time for '{current_branch}' -> '{task_info['asana_task_name']}'[/green]")
