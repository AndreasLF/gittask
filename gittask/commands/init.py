import typer
from ..config import ConfigManager
from ..asana_client import AsanaClient
import questionary

def init():
    """
    Initialize gittask configuration (Workspace & Project).
    """
    config = ConfigManager()
    token = config.get_api_token()
    
    if not token:
        typer.echo("❌ Not authenticated. Please run 'gittask auth login' first.")
        raise typer.Exit(code=1)

    try:
        with AsanaClient(token) as client:
            user = client.me
            typer.echo(f"👋 Hello, {user['name']}!")
            
            # Select Workspace
            workspaces = client.get_workspaces()
            workspace_choices = [
                questionary.Choice(ws['name'], value=ws['gid']) for ws in workspaces
            ]
            
            if not workspace_choices:
                typer.echo("❌ No workspaces found.")
                raise typer.Exit(code=1)

            workspace_gid = questionary.select(
                "Select your default Asana Workspace:",
                choices=workspace_choices
            ).ask()


            # ask user if paid plan
            paid_plan = questionary.confirm(
                "Is this Asana workspace on a paid plan?",
                default=True
            ).ask()
            config.set_paid_plan_status(paid_plan)
            
            config.set_default_workspace(workspace_gid)
            
            # Select Project (Optional)
            projects = client.get_projects(workspace_gid)
            project_choices = [
                questionary.Choice(p['name'], value=p['gid']) for p in projects
            ]
            
            # Add a "None" option
            project_choices.insert(0, questionary.Choice("None (I'll select per task)", value=None))
            
            project_gid = questionary.select(
                "Select a default Project (optional):",
                choices=project_choices
            ).ask()
            
            if project_gid:
                config.set_default_project(project_gid)
            
            typer.echo("✅ Configuration saved!")
        
    except Exception as e:
        typer.echo(f"❌ Error: {str(e)}")
        raise typer.Exit(code=1)
