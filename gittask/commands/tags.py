import typer
from rich.console import Console
from rich.table import Table
from ..config import ConfigManager
from ..database import DBManager
from ..git_handler import GitHandler
from ..asana_client import AsanaClient
from ..utils import select_and_create_tags

app = typer.Typer()
console = Console()
config = ConfigManager()
db = DBManager()
git = GitHandler()

@app.callback(invoke_without_command=True)
def list(ctx: typer.Context):
    """
    List tags for the current task.
    """
    if ctx.invoked_subcommand is not None:
        return

    current_branch = git.get_current_branch()
    task_info = db.get_task_for_branch(current_branch)
    
    if not task_info:
        console.print("[yellow]Current branch is not linked to an Asana task.[/yellow]")
        raise typer.Exit(code=1)

    token = config.get_api_token()
    if not token:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)

    with AsanaClient(token) as client:
        # We need to fetch the task details to get tags
        # AsanaClient doesn't have a get_task method yet, let's add it or use tasks_api directly
        try:
            # We can use the tasks_api directly from the client wrapper if we expose it or add a wrapper method
            # Let's check asana_client.py content again. It exposes tasks_api.
            task = client.tasks_api.get_task(task_info['asana_task_gid'], opts={'opt_fields': 'name,tags.name,tags.color'})
            
            console.print(f"Tags for task: [bold]{task['name']}[/bold]")
            
            if not task['tags']:
                console.print("[dim]No tags.[/dim]")
            else:
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Tag Name")
                table.add_column("Color")
                
                for tag in task['tags']:
                    table.add_row(tag['name'], tag['color'] or "default")
                
                console.print(table)
                
        except Exception as e:
            console.print(f"[red]Failed to fetch task details: {e}[/red]")

@app.command()
def add():
    """
    Add tags to the current task.
    """
    current_branch = git.get_current_branch()
    task_info = db.get_task_for_branch(current_branch)
    
    if not task_info:
        console.print("[yellow]Current branch is not linked to an Asana task.[/yellow]")
        raise typer.Exit(code=1)

    token = config.get_api_token()
    if not token:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)
        
    workspace_gid = config.get_default_workspace()

    with AsanaClient(token) as client:
        tag_gids = select_and_create_tags(client, workspace_gid, db)
        
        if tag_gids:
            console.print(f"Applying {len(tag_gids)} tags...")
            for tag_gid in tag_gids:
                try:
                    client.add_tag_to_task(task_info['asana_task_gid'], tag_gid)
                except Exception as e:
                    console.print(f"[red]Failed to add tag: {e}[/red]")
            console.print("[green]Tags added successfully![/green]")
