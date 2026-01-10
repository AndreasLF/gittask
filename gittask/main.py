import typer
from .commands import auth, init, checkout, status, sync, commit, push, pr, finish, tags, session, track

app = typer.Typer(
    name="gittask",
    help="Git-Asana CLI & Time Tracker",
    add_completion=False,
)

app.add_typer(auth.app, name="auth", help="Authentication commands")
app.command(name="init", help="Configuration commands")(init.init)
app.command(name="checkout", help="Checkout branch and track time")(checkout.checkout)
app.command(name="status", help="Show status")(status.status)
app.command(name="sync", help="Sync time to Asana")(sync.sync)
app.command(name="commit")(commit.commit)
app.command(name="push")(push.push)
app.add_typer(pr.app, name="pr", help="Pull Request commands")
app.command(name="finish")(finish.finish)
app.add_typer(tags.app, name="tags", help="Tag commands")
app.command(name="stop", help="Stop time tracking")(session.stop)
app.command(name="start", help="Start time tracking")(session.start)
app.command(name="track", help="Track time on a global task")(track.track)

@app.command(name="gui", help="Launch the Graphical User Interface (TUI)")
def gui():
    from .tui.app import GitTaskApp
    from .config import ConfigManager
    from .asana_client import AsanaClient
    
    # Warm up AsanaClient to initialize multiprocessing pool before Textual starts
    # This prevents "bad value(s) in fds_to_keep" error on macOS
    try:
        config = ConfigManager()
        token = config.get_api_token()
        if token:
            client = AsanaClient(token)
            client.close()
    except Exception:
        # Ignore errors here, let the app handle them or fail later
        pass

    app = GitTaskApp()
    app.run()

@app.callback()
def main(ctx: typer.Context):
    """
    Git-Asana CLI & Time Tracker
    """
    pass

if __name__ == "__main__":
    app()
