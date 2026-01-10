from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input
from textual.containers import Container, Vertical, Horizontal
import re

class TaskOptionsModal(ModalScreen):
    def __init__(self, task_name: str, task_gid: str, **kwargs):
        super().__init__(**kwargs)
        self.task_name = task_name
        self.task_gid = task_gid
        self.mode = "select" # select, create_branch, checkout_existing

    def compose(self) -> ComposeResult:
        with Container(classes="options-modal"):
            yield Label(f"Task: {self.task_name}", classes="modal-header")
            
            with Vertical(id="select-mode"):
                yield Button("Create New Branch", variant="success", id="btn-create")
                yield Button("Checkout Existing Branch", variant="primary", id="btn-checkout")
                yield Button("Track Globally (No Branch)", variant="default", id="btn-global")
                yield Button("Cancel", variant="error", id="btn-cancel")
            
            with Vertical(id="input-mode", classes="hidden"):
                yield Label("Enter Branch Name:", id="input-label")
                yield Input(id="branch-input")
                with Horizontal():
                    yield Button("Confirm", variant="success", id="btn-confirm")
                    yield Button("Back", variant="default", id="btn-back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        
        if btn_id == "btn-cancel":
            self.dismiss(None)
            
        elif btn_id == "btn-global":
            self.dismiss({
                "action": "track_global",
                "task_name": self.task_name,
                "task_gid": self.task_gid
            })
            
        elif btn_id == "btn-create":
            self.mode = "create_branch"
            self.show_input("Create Branch", self._slugify(self.task_name))
            
        elif btn_id == "btn-checkout":
            self.mode = "checkout_existing"
            self.show_input("Checkout Branch", "")
            
        elif btn_id == "btn-back":
            self.mode = "select"
            self.query_one("#select-mode").remove_class("hidden")
            self.query_one("#input-mode").add_class("hidden")
            
        elif btn_id == "btn-confirm":
            branch_name = self.query_one("#branch-input", Input).value
            if branch_name:
                self.dismiss({
                    "action": self.mode, 
                    "branch_name": branch_name,
                    "task_name": self.task_name,
                    "task_gid": self.task_gid
                })

    def show_input(self, title: str, value: str) -> None:
        self.query_one("#select-mode").add_class("hidden")
        input_container = self.query_one("#input-mode")
        input_container.remove_class("hidden")
        
        self.query_one("#input-label", Label).update(title)
        inp = self.query_one("#branch-input", Input)
        inp.value = value
        inp.focus()

    def _slugify(self, text: str) -> str:
        # Simple slugify
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'[\s-]+', '-', text).strip('-')
        return f"feature/{text}"
