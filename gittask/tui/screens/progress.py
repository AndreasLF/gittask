from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Button, DataTable
from textual.containers import Container
from ...database import DBManager
import time
from datetime import datetime, timedelta

class ProgressScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(id="progress", **kwargs)

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Progress & Statistics", classes="header"),
            Label("Daily Summary", classes="subheader"),
            DataTable(id="daily-stats"),
            Button("Back to Dashboard", variant="default", id="back-btn")
        )

    def on_mount(self) -> None:
        table = self.query_one("#daily-stats", DataTable)
        table.add_columns("Date", "Total Time", "Tasks Worked On")
        self.update_stats()

    def update_stats(self) -> None:
        db = DBManager()
        sessions = db.time_sessions.all()
        
        # Group by date
        daily_stats = {}
        for s in sessions:
            if not s['start_time']:
                continue
                
            date_str = time.strftime('%Y-%m-%d', time.localtime(s['start_time']))
            
            if date_str not in daily_stats:
                daily_stats[date_str] = {'duration': 0, 'tasks': set()}
            
            duration = s.get('duration_seconds', 0)
            if s['end_time'] is None:
                # Active session, calculate current duration
                duration = time.time() - s['start_time']
                
            daily_stats[date_str]['duration'] += duration
            daily_stats[date_str]['tasks'].add(s['branch'])

        table = self.query_one("#daily-stats", DataTable)
        table.clear()
        
        # Sort by date desc
        sorted_dates = sorted(daily_stats.keys(), reverse=True)
        
        for date in sorted_dates:
            stats = daily_stats[date]
            duration = stats['duration']
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            task_count = len(stats['tasks'])
            
            table.add_row(date, f"{hours}h {minutes}m", str(task_count))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.action_navigate("dashboard")
