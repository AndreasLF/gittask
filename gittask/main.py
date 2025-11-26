import typer
from .commands import auth, init, checkout, status, sync, commit, push, pr, finish

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

@app.callback()
def main(ctx: typer.Context):
    """
    Git-Asana CLI & Time Tracker
    """
    pass

if __name__ == "__main__":
    app()
