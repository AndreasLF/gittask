import questionary
from rich.console import Console
from typing import List, Dict

console = Console()

def select_and_create_tags(client, workspace_gid: str, db) -> List[str]:
    """
    Interactive prompt to select existing tags or create new ones.
    Returns a list of selected tag GIDs.
    """
    # Sync tags first as requested
    console.print("Syncing tags from Asana...")
    try:
        cached_tags = client.get_tags(workspace_gid)
        db.cache_tags(cached_tags)
    except Exception as e:
        console.print(f"[red]Failed to fetch tags: {e}[/red]")
        # Fallback to cache if fetch fails
        cached_tags = db.get_cached_tags() or []

    selected_tag_gids = []
    
    # Setup completer for text input
    from prompt_toolkit.completion import WordCompleter
    
    while True:
        # Filter out already selected tags
        available_tags = [t for t in cached_tags if t['gid'] not in selected_tag_gids]
        tag_names = [t['name'] for t in available_tags]
        
        completer = WordCompleter(tag_names, ignore_case=True, match_middle=True)
        
        # Show current selection in prompt
        prompt_msg = "Enter tag name (Leave empty to finish):"
        if selected_tag_gids:
            selected_names = [t['name'] for t in cached_tags if t['gid'] in selected_tag_gids]
            prompt_msg += f" [Selected: {', '.join(selected_names)}]"

        tag_input = questionary.text(
            prompt_msg,
            completer=completer
        ).ask()
        
        if not tag_input:
            break
            
        # Check if tag exists
        existing_tag = next((t for t in cached_tags if t['name'].lower() == tag_input.lower()), None)
        
        if existing_tag:
            if existing_tag['gid'] in selected_tag_gids:
                console.print(f"[yellow]Tag '{existing_tag['name']}' already selected.[/yellow]")
            else:
                selected_tag_gids.append(existing_tag['gid'])
                console.print(f"[green]Selected: {existing_tag['name']}[/green]")
        else:
            # Create new tag
            console.print(f"[cyan]Tag '{tag_input}' not found. Creating new tag...[/cyan]")
            
            # Color selection
            color_choices = [
                "none", "dark-pink", "dark-green", "dark-blue", "dark-red", 
                "dark-teal", "dark-brown", "dark-orange", "dark-purple", 
                "dark-warm-gray", "light-pink", "light-green", "light-blue", 
                "light-red", "light-teal", "light-brown", "light-orange", 
                "light-purple", "light-warm-gray"
            ]
            tag_color = questionary.autocomplete(
                "Tag Color:",
                choices=color_choices,
                default="none"
            ).ask()
            
            if tag_color == "none":
                tag_color = None

            try:
                new_tag = client.create_tag(workspace_gid, tag_input, color=tag_color)
                selected_tag_gids.append(new_tag['gid'])
                # Update cache and local list
                cached_tags.append({'gid': new_tag['gid'], 'name': new_tag['name']})
                db.cache_tags(cached_tags)
                console.print(f"[green]Created and selected tag: {new_tag['name']}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to create tag '{tag_input}': {e}[/red]")
        
    return selected_tag_gids
