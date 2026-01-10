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
        
        # Start global session
        db = DBManager()
        # For global tasks, we use a special branch name format
        branch_name = f"@global:{task_name.replace(' ', '_')}"
        
        db.start_session(branch_name, "GLOBAL", task_gid)
        
        # Also need to link it in branch_map if we want to persist the name mapping?
        # Actually start_session just takes task_gid. 
        # But get_task_for_branch needs an entry in branch_map to return task details.
        # So we should link it.
        db.link_branch_to_task(branch_name, "GLOBAL", task_gid, task_name, "None", "None")
        
        self.notify(f"Started tracking: {task_name}")
        self.app.action_navigate("dashboard")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.action_navigate("dashboard")
