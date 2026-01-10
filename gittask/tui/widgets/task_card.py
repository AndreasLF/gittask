from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static, Button, Label
from textual.reactive import reactive
from textual.message import Message
from ...database import DBManager
import time

class TaskCard(Static):
    """A card widget representing a task."""
    
    is_active = reactive(False)
    duration = reactive(0.0)

    def __init__(self, task_data: dict, current_branch: str = None, **kwargs):
        super().__init__(**kwargs)
        self.task_data = task_data
        self.branch_name = task_data.get('branch')
        self.task_name = task_data.get('asana_task_name', 'Unknown Task')
        self.task_gid = task_data.get('asana_task_gid')
        self.current_branch = current_branch
        
        # Check if active
        db = DBManager()
        active_session = db.get_active_session()
        if active_session and active_session['branch'] == self.branch_name:
            self.is_active = True
            self.start_time = active_session['start_time']
        else:
            self.is_active = False
            self.start_time = None

    def compose(self) -> ComposeResult:
        yield Label(self.task_name, classes="task-name")
        yield Label(self.branch_name, classes="branch-name")
        yield Label("00:00:00", classes="timer", id=f"timer-{self.id}")
        
        with Horizontal(classes="card-actions"):
            if self.is_active:
                yield Button("Stop", variant="error", id="stop-btn")
            else:
                yield Button("Start", variant="success", id="start-btn")
            
            if self.branch_name and not self.branch_name.startswith("@global:"):
                # Only show checkout if not already on this branch
                if self.branch_name != self.current_branch:
                    yield Button("Checkout", variant="primary", id="checkout-btn")
                else:
                    yield Button("Push", variant="default", id="push-btn")

    def on_mount(self) -> None:
        self.set_interval(1, self.update_timer)
        if self.is_active:
            self.add_class("active")

    def update_timer(self) -> None:
        if self.is_active and self.start_time:
            self.duration = time.time() - self.start_time
            hours = int(self.duration // 3600)
            minutes = int((self.duration % 3600) // 60)
            seconds = int(self.duration % 60)
            self.query_one(f"#timer-{self.id}", Label).update(f"{hours:02}:{minutes:02}:{seconds:02}")
        else:
            # Maybe show total time for this task?
            # For now just show 0 or last duration
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        button_id = event.button.id
        db = DBManager()
        
        if button_id == "start-btn":
            # Start session
            # If another session is active, stop it first (DBManager handles this usually or we should)
            db.stop_any_active_session()
            
            repo_path = self.task_data.get('repo_path')
            if not repo_path:
                # Fallback if not in task_data (shouldn't happen for branch tasks)
                if self.branch_name.startswith("@global:"):
                    repo_path = "GLOBAL"
                else:
                    from ...git_handler import GitHandler
                    import os
                    try:
                        repo_path = GitHandler().get_repo_root()
                    except:
                        # Fallback to current working directory if git fails
                        repo_path = os.getcwd()

            db.start_session(self.branch_name, repo_path, self.task_gid)
            self.is_active = True
            self.start_time = time.time()
            self.add_class("active")
            
            # Re-compose to show Stop button? Or just update button
            # Textual doesn't easily support replacing widgets in-place without removing/adding
            # But we can swap the button display if we had both and hid one, or just remove and mount new one.
            # Simpler: Post a message to Dashboard to refresh everything
            self.post_message(self.StatusChanged())
            
        elif button_id == "stop-btn":
            db.stop_any_active_session()
            self.is_active = False
            self.remove_class("active")
            self.post_message(self.StatusChanged())
            
        elif button_id == "checkout-btn":
            # Trigger checkout
            # This requires git command execution. 
            # For TUI, maybe we just notify for now or use gitpython if available in DB/helpers
            # The user asked for "checkout button if it is a branch linked task"
            # We can use os.system or subprocess, or better, the Checkout command logic.
            # But importing commands might be circular or heavy.
            # Let's post a message to App/Dashboard to handle checkout
            self.post_message(self.CheckoutRequested(self.branch_name))

        elif button_id == "push-btn":
            from ...git_handler import GitHandler
            try:
                GitHandler().push_branch(self.branch_name)
                self.notify(f"Successfully pushed {self.branch_name}", title="Push Success", severity="information")
            except Exception as e:
                self.notify(f"Failed to push: {e}", title="Push Error", severity="error")

    class StatusChanged(Message):
        """Sent when task status changes (start/stop)."""
        pass

    class CheckoutRequested(Message):
        """Sent when checkout is requested."""
        def __init__(self, branch: str):
            self.branch = branch
            super().__init__()
