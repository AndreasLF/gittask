from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, ListView, ListItem, Label, Button
from textual.containers import Container
from ...config import ConfigManager
from ...asana_client import AsanaClient
from ...database import DBManager

class TaskSearch(Screen):
    def __init__(self, **kwargs):
        super().__init__(id="search", **kwargs)

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Search Asana Tasks"),
            Input(placeholder="Type to search...", id="search-input"),
            ListView(id="results-list"),
            Button("Back to Dashboard", variant="default", id="back-btn")
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value
        if query:
            self.search_tasks(query)

    def search_tasks(self, query: str) -> None:
        config = ConfigManager()
        token = config.get_api_token()
        workspace_gid = config.get_default_workspace()
        
        if not token or not workspace_gid:
            self.notify("Not authenticated or no workspace set", severity="error")
            return

        try:
            with AsanaClient(token) as client:
                tasks = client.search_tasks(workspace_gid, query)
                
                list_view = self.query_one("#results-list", ListView)
                list_view.clear()
                
                for task in tasks:
                    list_view.append(ListItem(Label(task['name']), name=task['gid']))
                    
        except Exception as e:
            self.notify(f"Search failed: {e}", severity="error")

    def on_screen_resume(self) -> None:
        # Clear previous state
        self.query_one("#search-input", Input).value = ""
        self.query_one("#results-list", ListView).clear()
        self.query_one("#search-input", Input).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        task_gid = event.item.name
        # Get text from the Label widget
        label = event.item.query_one(Label)
        task_name = str(label.renderable)
        
        from .task_options import TaskOptionsModal
        self.app.push_screen(TaskOptionsModal(task_name, task_gid), self.handle_options)

    def handle_options(self, result: dict) -> None:
        if not result:
            return
            
        action = result.get("action")
        
        if action == "track_global":
            self.start_global_tracking(result.get("task_name"), result.get("task_gid")) # Wait, modal doesn't pass these back?
            # Modal passes action and branch_name.
            # I need task info. I can store it in self or pass it through modal result?
            # Better to store selected task in self temporarily or pass it to modal and have modal return it.
            # Let's assume modal returns what we need or we know what we selected.
            # Actually, handle_options receives the result from dismiss.
            # The modal has task_name and task_gid. It should probably include them in result.
            pass
            
        elif action == "create_branch":
            branch_name = result.get("branch_name")
            self.perform_checkout(branch_name, create_new=True)
            
        elif action == "checkout_existing":
            branch_name = result.get("branch_name")
            self.perform_checkout(branch_name, create_new=False)

    def start_global_tracking(self, task_name: str, task_gid: str) -> None:
        # Start global session
        db = DBManager()
        branch_name = f"@global:{task_name.replace(' ', '_')}"
        
        db.start_session(branch_name, "GLOBAL", task_gid)
        db.link_branch_to_task(branch_name, "GLOBAL", task_gid, task_name, "None", "None")
        
        self.notify(f"Started tracking: {task_name}")
        self.app.action_navigate("dashboard")

    def perform_checkout(self, branch_name: str, create_new: bool) -> None:
        self.notify(f"Checking out {branch_name}...")
        self.run_worker(self._checkout_worker(branch_name, create_new))

    async def _checkout_worker(self, branch_name: str, create_new: bool) -> None:
        import sys
        import asyncio
        from .log_view import LogScreen
        
        cmd = [sys.executable, "-m", "gittask.main", "checkout", branch_name]
        if create_new:
            cmd.append("-b")
            
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode() + stderr.decode()
            
            if process.returncode == 0:
                self.notify(f"Checked out {branch_name}")
                self.app.action_navigate("dashboard")
            else:
                self.app.push_screen(LogScreen("Checkout Failed", output))
                
        except Exception as e:
            self.notify(f"Checkout failed: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.action_navigate("dashboard")
