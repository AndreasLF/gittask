from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Label, Static
from textual.containers import Container, Horizontal, VerticalScroll
from ...database import DBManager
from ..widgets.task_card import TaskCard
from .log_view import LogScreen
import time

class Dashboard(Screen):
    def __init__(self, **kwargs):
        super().__init__(id="dashboard", **kwargs)

    def compose(self) -> ComposeResult:
        yield Container(
            VerticalScroll(id="task-grid", classes="task-grid"),
            Horizontal(
                Button("New Task", variant="success", id="new-task-btn"),
                Button("Sync", variant="primary", id="sync-btn"),
                Button("Status", variant="default", id="status-btn"),
                Button("Progress", variant="default", id="progress-btn"),
                Button("Quit", variant="error", id="quit-btn"),
                classes="bottom-bar"
            ),
            classes="dashboard-container"
        )

    def on_mount(self) -> None:
        self.refresh_tasks()

    def on_screen_resume(self) -> None:
        self.refresh_tasks()

    def refresh_tasks(self) -> None:
        grid = self.query_one("#task-grid")
        grid.remove_children()
        
        db = DBManager()
        branch_map = db.branch_map.all()
        active = db.get_active_session()
        
        tasks_to_show = []
        seen_branches = set()
        
        # Prioritize active session
        if active:
            branch = active.get('branch')
            if branch and branch not in seen_branches:
                # Get task details
                task_info = db.get_task_for_branch(branch, active.get('repo_path'))
                if not task_info:
                    task_info = {
                        'branch': branch,
                        'asana_task_name': 'Unknown Task',
                        'asana_task_gid': active.get('task_gid')
                    }
                else:
                    # Ensure branch key exists if it came from branch_map (which uses branch_name)
                    task_info['branch'] = task_info.get('branch_name', branch)
                    
                tasks_to_show.append(task_info)
                seen_branches.add(branch)
        
        # Add from branch_map
        for item in branch_map:
            branch = item.get('branch_name') or item.get('branch')
            if branch and branch not in seen_branches:
                item['branch'] = branch # Normalize for TaskCard
                tasks_to_show.append(item)
                seen_branches.add(branch)
                
        # Get current branch
        try:
            from ...git_handler import GitHandler
            git = GitHandler()
            current_branch = git.get_current_branch()
        except Exception:
            current_branch = None

        # Create cards
        for task_data in tasks_to_show:
            grid.mount(TaskCard(task_data, current_branch=current_branch))
            
    def on_task_card_status_changed(self, message: TaskCard.StatusChanged) -> None:
        # Refresh all cards to update active state (only one can be active)
        # Or just re-mount everything to be safe and simple
        self.refresh_tasks()
        
    def on_task_card_checkout_requested(self, message: TaskCard.CheckoutRequested) -> None:
        self.notify(f"Checking out {message.branch}...")
        self.run_worker(self.perform_checkout(message.branch))

    async def perform_checkout(self, branch: str) -> None:
        import sys
        import subprocess
        from .log_view import LogScreen
        
        # Run checkout command
        cmd = [sys.executable, "-m", "gittask.main", "checkout", branch]
        
        try:
            # Run in a thread to avoid blocking the event loop, although subprocess.run blocks the thread.
            # Textual workers run in threads by default if not async, but here we are async def.
            # We should use asyncio.create_subprocess_exec or run in executor.
            # But for simplicity in this context, let's use subprocess.run in a thread via run_worker default behavior 
            # if we made this non-async, OR use asyncio subprocess.
            
            # Let's use asyncio subprocess
            import asyncio
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            output = stdout.decode() + stderr.decode()
            
            if process.returncode == 0:
                self.notify(f"Checked out {branch}")
                self.refresh_tasks()
            else:
                self.app.push_screen(LogScreen("Checkout Failed", output))
                
        except Exception as e:
            self.notify(f"Checkout failed: {e}", severity="error")
        
    async def perform_sync(self) -> None:
        import sys
        import subprocess
        from .log_view import LogScreen
        import asyncio
        
        self.notify("Syncing with Asana...")
        
        # Run sync command
        cmd = [sys.executable, "-m", "gittask.main", "sync"]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            output = stdout.decode() + stderr.decode()
            
            if process.returncode == 0:
                self.notify("Sync completed successfully")
                self.refresh_tasks()
            else:
                self.app.push_screen(LogScreen("Sync Failed", output))
                
        except Exception as e:
            self.notify(f"Sync failed: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-task-btn":
            self.app.action_navigate("search")
        elif event.button.id == "sync-btn":
            self.run_worker(self.perform_sync())
        elif event.button.id == "status-btn":
            self.app.action_navigate("status")
        elif event.button.id == "progress-btn":
            self.app.action_navigate("progress")
        elif event.button.id == "quit-btn":
            self.app.action_request_quit()
