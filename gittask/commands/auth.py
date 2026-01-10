import typer
from ..config import ConfigManager
import questionary
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command()
def login(
    token: str = typer.Option(None, help="Asana Personal Access Token"),
    github: bool = typer.Option(False, "--github", help="Login with GitHub Token")
):
    """
    Login to Asana (default) or GitHub.
    """
    config = ConfigManager()
    if github:
        github_token = typer.prompt("GitHub Personal Access Token", hide_input=True)
        config.set_github_token(github_token)
        console.print("[green]Successfully logged in to GitHub![/green]")
    else:
        if not token:
            token = typer.prompt("Asana Personal Access Token", hide_input=True)
        config.set_api_token(token)
        console.print("[green]Successfully logged in to Asana![/green]")

@app.command()
def logout():
    """
    Remove stored credentials.
    """
    config = ConfigManager()
    config.logout()
    console.print("[green]Logged out.[/green]")
    config.set_api_token("") # Keyring doesn't easily support delete in all backends, setting to empty is safer
    typer.echo("✅ Token removed.")
