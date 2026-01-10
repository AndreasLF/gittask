from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, RichLog
from textual.containers import Container, Vertical

class LogScreen(ModalScreen):
    def __init__(self, title: str, content: str, **kwargs):
        super().__init__(**kwargs)
        self.log_title = title
        self.content = content

    def compose(self) -> ComposeResult:
        yield Container(
            Label(self.log_title, classes="log-title"),
            RichLog(id="log-view", wrap=True, highlight=True, markup=True),
            Button("Close", variant="primary", id="close-btn"),
            classes="log-modal"
        )

    def on_mount(self) -> None:
        log = self.query_one(RichLog)
        log.write(self.content)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.dismiss()
