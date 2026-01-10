from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input, ListView, ListItem, Checkbox
from textual.containers import Container, Vertical, Horizontal
from textual import work
from ...config import ConfigManager
from ...asana_client import AsanaClient

class TagSelectionModal(ModalScreen):
    def __init__(self, workspace_gid: str, **kwargs):
        super().__init__(**kwargs)
        self.workspace_gid = workspace_gid
        self.selected_tags = set()
        self.all_tags = []

    def compose(self) -> ComposeResult:
        with Container(classes="options-modal"):
            yield Label("Select Tags", classes="modal-header")
            yield Label("Space to toggle, Enter to confirm", classes="modal-subtitle")
            
            yield ListView(id="tag-list")
            
            yield Input(placeholder="Create new tag...", id="new-tag-input")
            
            with Horizontal(classes="modal-actions"):
                yield Button("Confirm", variant="success", id="btn-confirm")
                yield Button("Skip", variant="default", id="btn-skip")

    def on_mount(self) -> None:
        self._fetch_tags()

    @work(exclusive=True, thread=True)
    def _fetch_tags(self) -> None:
        try:
            config = ConfigManager()
            token = config.get_api_token()
            
            with AsanaClient(token) as client:
                tags = client.get_tags(self.workspace_gid)
                
            self.app.call_from_thread(self._update_tag_list, tags)
        except Exception as e:
            self.app.call_from_thread(self.notify, f"Failed to fetch tags: {e}", severity="error")

    def _update_tag_list(self, tags: list) -> None:
        self.all_tags = tags
        list_view = self.query_one("#tag-list", ListView)
        list_view.clear()
        
        for tag in tags:
            # We use a custom ListItem that tracks selection state visually
            # Since Checkbox inside ListItem might be tricky with focus, let's just use text
            # and toggle style or prefix.
            item = ListItem(Label(f"[ ] {tag['name']}"), name=tag['gid'])
            item.tag_name = tag['name']
            item.tag_gid = tag['gid']
            list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        tag_gid = item.tag_gid
        
        if tag_gid in self.selected_tags:
            self.selected_tags.remove(tag_gid)
            item.query_one(Label).update(f"[ ] {item.tag_name}")
        else:
            self.selected_tags.add(tag_gid)
            item.query_one(Label).update(f"[x] {item.tag_name}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        tag_name = event.value
        if tag_name:
            self._create_tag(tag_name)
            event.input.value = ""

    @work(exclusive=True, thread=True)
    def _create_tag(self, tag_name: str) -> None:
        try:
            config = ConfigManager()
            token = config.get_api_token()
            
            with AsanaClient(token) as client:
                new_tag = client.create_tag(self.workspace_gid, tag_name)
                
            self.app.call_from_thread(self._on_tag_created, new_tag)
        except Exception as e:
            self.app.call_from_thread(self.notify, f"Failed to create tag: {e}", severity="error")

    def _on_tag_created(self, tag: dict) -> None:
        self.all_tags.append(tag)
        self.selected_tags.add(tag['gid'])
        
        list_view = self.query_one("#tag-list", ListView)
        item = ListItem(Label(f"[x] {tag['name']}"), name=tag['gid'])
        item.tag_name = tag['name']
        item.tag_gid = tag['gid']
        list_view.append(item)
        
        # Scroll to bottom
        list_view.scroll_to_end()
        self.notify(f"Created tag: {tag['name']}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm":
            self.dismiss(list(self.selected_tags))
        elif event.button.id == "btn-skip":
            self.dismiss([])
