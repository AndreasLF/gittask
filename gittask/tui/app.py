from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from .screens.dashboard import Dashboard
from .screens.task_search import TaskSearch
from .screens.progress import ProgressScreen
from .screens.status import StatusScreen

class GitTaskApp(App):
    """A Textual app for GitTask."""

    CSS_PATH = "css/styles.tcss"
    BINDINGS = [
        ("d", "navigate('dashboard')", "Dashboard"),
        ("s", "navigate('search')", "Search Tasks"),
        ("p", "navigate('progress')", "Progress"),
        ("ctrl+c", "request_quit", "Quit"),
    ]

    SCREENS = {
        "dashboard": Dashboard,
        "search": TaskSearch,
        "progress": ProgressScreen,
        "status": StatusScreen,
    }

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen("dashboard")
        self.last_quit_request = 0

    def action_navigate(self, screen: str) -> None:
        self.switch_screen(screen)

    def action_request_quit(self) -> None:
        import time
        now = time.time()
        if now - self.last_quit_request < 1.0:
            self.exit()
        else:
            self.last_quit_request = now
            self.notify("Press Ctrl+C again to quit")

if __name__ == "__main__":
    app = GitTaskApp()
    app.run()
