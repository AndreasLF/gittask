import typer
from ..database import DBManager
from rich.console import Console
from rich.table import Table
import time
import datetime

console = Console()

def status():
    """
    Show current time tracking status and recent sessions.
    """
    db = DBManager()
    
    # Current Session
    # We can find it by looking for open sessions
    # Actually DBManager doesn't have a direct "get_open_session" but we can query.
    # Let's add a helper or just search.
    from tinydb import Query
    Session = Query()
    open_sessions = db.time_sessions.search(Session.end_time == None)
    
    if open_sessions:
        session = open_sessions[0]
        start_time = session['start_time']
        duration = time.time() - start_time
        
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        
        branch_display = session['branch']
        if branch_display.startswith("@global:"):
            branch_display = branch_display.replace("@global:", "") + " (Global)"
            
        console.print(f"\n[bold green]🟢 Currently tracking:[/bold green] {branch_display}")
        
        repo_path = session.get('repo_path')
        # If it's an old session without repo_path, we might fail to find the task link if we enforce it.
        # But we just migrated, so let's assume new sessions have it.
        # For global sessions, repo_path is "GLOBAL".
        
        task_info = db.get_task_for_branch(session['branch'], repo_path)
        if task_info:
            console.print(f"   Task: {task_info['asana_task_name']}")
        else:
             console.print(f"   Task: [red]Unknown (Link broken)[/red]")
             
        console.print(f"   Duration: {hours}h {minutes}m\n")
    else:
        console.print("\n[yellow]⚪ No active time tracking session.[/yellow]\n")

    # Recent Sessions (Unsynced)
    unsynced = db.get_unsynced_sessions()
    
    if unsynced:
        table = Table(title="Unsynced Sessions")
        table.add_column("Branch", style="cyan")
        table.add_column("Duration", style="magenta")
        table.add_column("Date", style="green")
        
        for s in unsynced:
            if s['end_time']:
                duration = s['duration_seconds']
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                date_str = datetime.datetime.fromtimestamp(s['start_time']).strftime('%Y-%m-%d %H:%M')
                table.add_row(s['branch'], f"{hours}h {minutes}m", date_str)
            
        console.print(table)
    else:
        console.print("[green]All sessions synced![/green]")
