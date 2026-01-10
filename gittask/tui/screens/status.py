from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Button, DataTable, Static
from textual.containers import Container, VerticalScroll, Horizontal
from ...database import DBManager
import time
from datetime import datetime

class StatusScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(id="status", **kwargs)

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Status Overview", classes="page-title"),
            VerticalScroll(
                Container(
                    Label("Current Session", classes="section-title"),
                    Static(id="current-status-info", classes="status-card"),
                    classes="status-section"
                ),
                Container(
                    Label("Unsynced Sessions", classes="section-title"),
                    DataTable(id="unsynced-table"),
                    classes="status-section"
                ),
                classes="content-scroll"
            ),
            Horizontal(
                Button("Back to Dashboard", variant="default", id="back-btn"),
                classes="bottom-bar"
            ),
            classes="screen-container"
        )

    def on_mount(self) -> None:
        table = self.query_one("#unsynced-table", DataTable)
        table.add_columns("Branch", "Duration", "Date")
        self.update_status()

    def on_screen_resume(self) -> None:
        self.update_status()

    def update_status(self) -> None:
        db = DBManager()
        
        # Current Session
        active = db.get_active_session()
        status_info = self.query_one("#current-status-info", Static)
        
        if active:
            start_time = active['start_time']
            duration = time.time() - start_time
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            
            branch = active['branch']
            if branch.startswith("@global:"):
                branch = branch.replace("@global:", "") + " (Global)"
                
            task_info = db.get_task_for_branch(active['branch'], active.get('repo_path'))
            task_name = task_info['asana_task_name'] if task_info else "Unknown Task"
            
            status_text = (
                f"[bold green]Currently Tracking[/bold green]\n\n"
                f"[bold]Branch:[/bold] {branch}\n"
                f"[bold]Task:[/bold] {task_name}\n"
                f"[bold]Duration:[/bold] {hours}h {minutes}m"
            )
            status_info.update(status_text)
            status_info.add_class("active")
        else:
            status_info.update("[yellow]No active time tracking session.[/yellow]")
            status_info.remove_class("active")

        # Unsynced Sessions
        unsynced = db.get_unsynced_sessions()
        table = self.query_one("#unsynced-table", DataTable)
        table.clear()
        
        for s in unsynced:
            if s['end_time']:
                duration = s['duration_seconds']
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                date_str = datetime.fromtimestamp(s['start_time']).strftime('%Y-%m-%d %H:%M')
                table.add_row(s['branch'], f"{hours}h {minutes}m", date_str)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.action_navigate("dashboard")
