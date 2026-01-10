import typer
from rich.console import Console
from ..database import DBManager
from ..config import ConfigManager
from ..asana_client import AsanaClient
import questionary
from ..utils import select_and_create_tags

app = typer.Typer()
console = Console()

@app.command(name="track")
def track(
    task_name: str = typer.Argument(None, help="Task name to track (optional, will prompt if empty)"),
):
    """
    Track time on a global task (not linked to a git branch).
    """
    db = DBManager()
    config = ConfigManager()
    
    # 1. Check authentication
    token = config.get_api_token()
    if not token:
        console.print("[red]Not authenticated. Run 'gittask auth login'.[/red]")
        raise typer.Exit(code=1)

    workspace_gid = config.get_default_workspace()
    if not workspace_gid:
        console.print("[red]No default workspace set. Run 'gittask init'.[/red]")
        raise typer.Exit(code=1)

    with AsanaClient(token) as client:
        # 2. Select Task
        task_gid = None
        asana_task_name = None
        
        if task_name:
            # Search for task by name
            console.print(f"Searching for task '{task_name}'...")
            tasks = client.search_tasks(workspace_gid, task_name)
            
            if not tasks:
                 if questionary.confirm(f"Task '{task_name}' not found. Create it?").ask():
                     # Create new task
                     project_gid = config.get_default_project()
                     new_task = client.create_task(workspace_gid, project_gid, task_name)
                     task_gid = new_task['gid']
                     asana_task_name = new_task['name']
                 else:
                     console.print("[yellow]Tracking cancelled.[/yellow]")
                     return
            elif len(tasks) == 1:
                task_gid = tasks[0]['gid']
                asana_task_name = tasks[0]['name']
            else:
                # Multiple matches
                choices = [t['name'] for t in tasks]
                selected_name = questionary.select("Multiple tasks found. Select one:", choices=choices).ask()
                selected_task = next(t for t in tasks if t['name'] == selected_name)
                task_gid = selected_task['gid']
                asana_task_name = selected_task['name']
        else:
            # Interactive selection (similar to checkout)
            project_gid = config.get_default_project()
            console.print("Fetching project tasks...")
            try:
                project_tasks = client.get_project_tasks(project_gid)
            except Exception as e:
                console.print(f"[red]Failed to fetch project tasks: {e}[/red]")
                project_tasks = []
            
            task_names = [t['name'] for t in project_tasks]
            from prompt_toolkit.completion import WordCompleter
            completer = WordCompleter(task_names, ignore_case=True, match_middle=True)
            
            task_input = questionary.text(
                "Select task (Type to search or enter new name):",
                completer=completer
            ).ask()
            
            if not task_input:
                console.print("[yellow]No task selected. Tracking cancelled.[/yellow]")
                return

            existing_task = next((t for t in project_tasks if t['name'].lower() == task_input.lower()), None)
            
            if existing_task:
                task_gid = existing_task['gid']
                asana_task_name = existing_task['name']
            else:
                if questionary.confirm(f"Create new task '{task_input}'?").ask():
                    asana_task_name = task_input
                    # Tag Selection
                    tag_gids = select_and_create_tags(client, workspace_gid, db)
                    try:
                        new_task = client.create_task(workspace_gid, project_gid, asana_task_name)
                        task_gid = new_task['gid']
                        asana_task_name = new_task['name']
                        
                        if tag_gids:
                             for tag_gid in tag_gids:
                                 client.add_tag_to_task(task_gid, tag_gid)
                    except Exception as e:
                        console.print(f"[red]Failed to create task: {e}[/red]")
                        return
                else:
                    return

        # 3. Start Session
        if task_gid:
            # Stop any existing session first (handled by start_session)
            # Use special branch name and repo path for global tasks
            branch_name = f"@global:{asana_task_name}"
            repo_path = "GLOBAL"
            
            db.start_session(branch_name, repo_path, task_gid)
            console.print(f"[bold green]Started tracking time for '{asana_task_name}' (Global)[/bold green]")
