import typer
from ..git_handler import GitHandler
from ..database import DBManager
from ..config import ConfigManager
from ..asana_client import AsanaClient
import questionary
import time
from rich.console import Console

console = Console()

def checkout(
    branch_name: str = typer.Argument(..., help="Branch to checkout"),
    new_branch: bool = typer.Option(False, "-b", "--new-branch", help="Create a new branch"),
):
    """
    Checkout a branch and track time.
    """
    git = GitHandler()
    db = DBManager()
    config = ConfigManager()
    
    # 1. Stop current session
    current_branch = git.get_current_branch()
    
    if current_branch == branch_name:
        console.print(f"[yellow]Already on branch {branch_name}[/yellow]")
        # We still want to ensure tracking is active, so we proceed to step 3
    else:
        if current_branch != "DETACHED_HEAD":
            db.stop_current_session(current_branch)
            console.print(f"[yellow]Stopped tracking time for {current_branch}[/yellow]")

        # 2. Checkout new branch
        try:
            git.checkout_branch(branch_name, create_new=new_branch)
            console.print(f"[green]Switched to branch {branch_name}[/green]")
        except Exception as e:
            console.print(f"[red]Error checking out branch: {e}[/red]")
            raise typer.Exit(code=1)

    # 3. Check if linked to Asana
    task_info = db.get_task_for_branch(branch_name)
    
    if not task_info:
        # Not linked, prompt to link
        console.print(f"[bold blue]Branch '{branch_name}' is not linked to an Asana task.[/bold blue]")
        
        token = config.get_api_token()
        if not token:
            console.print("[red]Not authenticated. Cannot link to Asana. Run 'gittask auth login'.[/red]")
            # We still allow checkout, just no tracking linked to a task
            return

        client = AsanaClient(token)
        workspace_gid = config.get_default_workspace()
        
        if not workspace_gid:
             console.print("[red]No default workspace set. Run 'gittask init'.[/red]")
             return

        with AsanaClient(token) as client:
            action = questionary.select(
                "What would you like to do?",
                choices=[
                    "Search for an existing task",
                    "Create a new task",
                    "Don't link (No tracking)"
                ]
            ).ask()
            
            task_gid = None
            task_name = None
            
            # Helper for tag selection
            def select_and_create_tags(client, workspace_gid, db):
                console.print("Fetching tags...")
                cached_tags = db.get_cached_tags()
                if not cached_tags:
                    try:
                        cached_tags = client.get_tags(workspace_gid)
                        db.cache_tags(cached_tags)
                    except Exception as e:
                        console.print(f"[red]Failed to fetch tags: {e}[/red]")
                        cached_tags = []
                
                tag_choices = [t['name'] for t in cached_tags]
                tag_choices.append("Create new tag")
                
                selected_tag_names = questionary.checkbox(
                    "Select tags:",
                    choices=tag_choices
                ).ask()
                
                selected_tag_gids = []
                if selected_tag_names:
                    for tag_name in selected_tag_names:
                        if tag_name == "Create new tag":
                            new_tag_name = questionary.text("New Tag Name:").ask()
                            if new_tag_name:
                                try:
                                    new_tag = client.create_tag(workspace_gid, new_tag_name)
                                    selected_tag_gids.append(new_tag['gid'])
                                    # Update cache
                                    cached_tags.append({'gid': new_tag['gid'], 'name': new_tag['name']})
                                    db.cache_tags(cached_tags)
                                except Exception as e:
                                    console.print(f"[red]Failed to create tag '{new_tag_name}': {e}[/red]")
                        else:
                            # Find gid
                            tag = next((t for t in cached_tags if t['name'] == tag_name), None)
                            if tag:
                                selected_tag_gids.append(tag['gid'])
                return selected_tag_gids

            if action == "Search for an existing task":
                query = questionary.text("Search query:").ask()
                tasks = client.search_tasks(workspace_gid, query)
                
                if not tasks:
                    console.print("[yellow]No tasks found.[/yellow]")
                else:
                    task_choices = [
                        questionary.Choice(t['name'], value=t) for t in tasks
                    ]
                    selected_task = questionary.select("Select task:", choices=task_choices).ask()
                    task_gid = selected_task['gid']
                    task_name = selected_task['name']
                    
                    # Optional: Add tags to existing task
                    if questionary.confirm("Add tags to this task?").ask():
                        tag_gids = select_and_create_tags(client, workspace_gid, db)
                        if tag_gids:
                            console.print(f"Applying {len(tag_gids)} tags...")
                            for tag_gid in tag_gids:
                                try:
                                    client.add_tag_to_task(task_gid, tag_gid)
                                except Exception as e:
                                    console.print(f"[red]Failed to add tag: {e}[/red]")
                    
            elif action == "Create a new task":
                task_name = questionary.text("Task Name:", default=branch_name).ask()
                project_gid = config.get_default_project()
                
                # Tag Selection
                tag_gids = select_and_create_tags(client, workspace_gid, db)

                # Create Task
                new_task = client.create_task(workspace_gid, project_gid, task_name)
                task_gid = new_task['gid']
                task_name = new_task['name']
                console.print(f"[green]Created task: {task_name}[/green]")
                
                # Apply Tags
                if tag_gids:
                    console.print(f"Applying {len(tag_gids)} tags...")
                    for tag_gid in tag_gids:
                        try:
                            client.add_tag_to_task(task_gid, tag_gid)
                        except Exception as e:
                            console.print(f"[red]Failed to add tag: {e}[/red]")

        if task_gid:
            # Link it
            db.link_branch_to_task(
                branch_name, 
                task_gid, 
                task_name, 
                project_gid=config.get_default_project() or "", 
                workspace_gid=workspace_gid
            )
            task_info = {'asana_task_gid': task_gid, 'asana_task_name': task_name}

    # 4. Start new session
    if task_info:
        # Check if we are already tracking this task
        # We can check if there's an open session for this branch
        # Actually, we stopped the session in step 1 if we switched branches.
        # But if we were "Already on branch", we didn't stop it.
        
        # Let's check if there is an open session for this branch
        from tinydb import Query
        Session = Query()
        open_sessions = db.time_sessions.search(
            (Session.branch == branch_name) & (Session.end_time == None)
        )
        
        if open_sessions:
             console.print(f"[yellow]Already tracking time for '{branch_name}'[/yellow]")
        else:
            db.start_session(branch_name, task_info['asana_task_gid'])
            console.print(f"[bold green]Started tracking time for '{branch_name}' -> '{task_info['asana_task_name']}'[/bold green]")
            
    else:
        console.print("[yellow]Time tracking disabled for this branch (not linked).[/yellow]")

    # Warn if unborn
    if not git.repo.head.is_valid():
        console.print("\n[bold red]⚠️  Warning: This branch is unborn (no commits yet).[/bold red]")
        console.print("   It will not be visible in 'git branch' until you make a commit.")
        console.print("   Run: [green]git add . && git commit -m 'Initial commit'[/green]")
