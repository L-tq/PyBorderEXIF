#!/usr/bin/env python3
"""TUI (Text User Interface) for PyBorderEXIF using Textual."""

import os
import sys
import asyncio

from border_exif.config import Config, BORDER_PRESETS
from border_exif.core import process_images, get_supported_images_from_dir
from border_exif.exif_reader import get_all_field_names, get_field_label

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.widgets import (
        Header, Footer, Button, Label, Input, Select, Switch,
        Static, DirectoryTree, ListView, ListItem, ProgressBar,
        Checkbox, RadioSet, RadioButton, TabbedContent, TabPane,
    )
    from textual.screen import Screen
    from textual import on
    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False


if not HAS_TEXTUAL:
    print("Textual is required for TUI mode. Install with: pip install textual")
    sys.exit(1)


class ProcessingScreen(Screen):
    """Screen shown during batch processing."""

    def __init__(self, image_paths, config):
        super().__init__()
        self._images = image_paths
        self._config = config

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Processing Images...", id="status-label"),
            ProgressBar(total=len(self._images), id="progress"),
            Static("", id="current-file"),
            id="processing-container",
        )
        yield Footer()

    def on_mount(self):
        asyncio.create_task(self._do_processing())

    async def _do_processing(self):
        from border_exif.core import process_image

        progress = self.query_one("#progress", ProgressBar)
        current_file = self.query_one("#current-file", Static)

        total = len(self._images)
        for i, path in enumerate(self._images):
            current_file.update(f"[{i+1}/{total}] {os.path.basename(path)}")
            try:
                await asyncio.to_thread(process_image, path, self._config)
            except Exception as e:
                current_file.update(f"[{i+1}/{total}] FAILED: {os.path.basename(path)} - {e}")
            progress.advance(1)

        self.dismiss(f"Processed {total} image(s)")


class FileListItem(ListItem):
    """A file list item with checkbox."""

    def __init__(self, *children, path, selected=True, **kwargs):
        super().__init__(*children, **kwargs)
        self.path = path
        self.selected = selected


class DirPickerScreen(Screen):
    """Screen for browsing and selecting a directory."""

    def __init__(self, start_path, on_select):
        super().__init__()
        self._start_path = start_path
        self._on_select = on_select

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Navigate the tree, then click 'Select Directory'.", id="picker-hint")
        yield DirectoryTree(self._start_path, id="dir-tree")
        with Horizontal(id="picker-actions"):
            yield Button("Select Directory", id="btn-select-dir", variant="primary")
            yield Button("Cancel", id="btn-cancel", variant="default")
        yield Footer()

    @on(Button.Pressed, "#btn-select-dir")
    def on_select_dir(self):
        tree = self.query_one("#dir-tree", DirectoryTree)
        self._on_select(str(tree.path))
        self.dismiss()

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self):
        self.dismiss()


_EXIF_FIELD_COLUMNS = [
    ["camera_model", "lens_model", "focal_length_35mm", "make", "body_serial_number", "lens_serial_number"],
    ["aperture", "iso", "exposure_time", "exposure_bias", "metering_mode", "flash", "white_balance"],
    ["datetime_original", "artist", "copyright", "software", "orientation", "image_unique_id"],
]
_EXIF_FIELD_COLUMN_MAP = {f: i for i, g in enumerate(_EXIF_FIELD_COLUMNS) for f in g}


class MainScreen(Screen):
    """Main TUI screen."""

    def __init__(self, config):
        super().__init__()
        self._config = config
        self._image_files = []
        self._available_fields = get_all_field_names()

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Files", id="tab-files"):
                with Horizontal():
                    with Container(id="dir-panel"):
                        yield Label("Input Directory:", classes="section-label")
                        yield Input(value=self._config.input_dir, id="input-dir", placeholder="Select or type directory...")
                        with Horizontal():
                            yield Button("Browse", id="btn-browse-dir", variant="primary")
                            yield Button("Load", id="btn-load-dir", variant="default")
                        yield Label("", id="dir-status")
                        yield Label("Selected Images:", classes="section-label")
                        with Horizontal(id="file-select-actions"):
                            yield Button("Select All", id="btn-select-all", variant="default")
                            yield Button("Deselect All", id="btn-deselect-all", variant="default")
                        yield ScrollableContainer(ListView(id="file-list"), id="file-list-container")
                    with Container(id="options-panel"):
                        yield Label("Output Directory:", classes="section-label")
                        yield Input(value=self._config.output_dir, id="output-dir", placeholder="Output directory...")
                        yield Button("Browse Output", id="btn-browse-out", variant="default")

            with TabPane("Border", id="tab-border"):
                with Vertical():
                    yield Label("Border Preset", classes="section-label")
                    with RadioSet(id="border-preset"):
                        for name in BORDER_PRESETS:
                            yield RadioButton(name.title(), value=name)
                        yield RadioButton("Custom", value="custom")
                    yield Label("Custom Border (top,bottom,left,right):", classes="section-label")
                    yield Input(placeholder="e.g., 30,80,30,30", id="custom-border")
                    yield Label("Border Color (R,G,B):", classes="section-label")
                    yield Input(value="255,255,255", id="border-color")

            with TabPane("EXIF", id="tab-exif"):
                with Horizontal():
                    with Vertical(classes="exif-form-col"):
                        yield Label("Author Name:", classes="section-label")
                        yield Input(value=self._config.author_name, id="author-name", placeholder="Enter author name...")
                        yield Label("Text Position:", classes="section-label")
                        yield Select([("Bottom", "bottom"), ("Top", "top"), ("Left", "left"), ("Right", "right")],
                                     id="text-position", value="bottom")
                        yield Label("Font Size:", classes="section-label")
                        yield Input(value=str(self._config.exif.get("font_size", 24)), id="font-size")
                    with Vertical(classes="exif-form-col"):
                        yield Label("Text Alignment:", classes="section-label")
                        yield Select([("Left", "left"), ("Center", "center"), ("Right", "right")],
                                     id="text-align", value="left")
                        yield Label("Font Color (R,G,B):", classes="section-label")
                        yield Input(value="0,0,0", id="font-color")

            with TabPane("Fields", id="tab-fields"):
                with Vertical(id="fields-content"):
                    with Horizontal():
                        with Vertical(classes="exif-column"):
                            yield Label("Camera & Lens", classes="column-header")
                            yield Vertical(id="exif-col-0")
                        with Vertical(classes="exif-column"):
                            yield Label("Exposure", classes="column-header")
                            yield Vertical(id="exif-col-1")
                        with Vertical(classes="exif-column"):
                            yield Label("Info & Meta", classes="column-header")
                            yield Vertical(id="exif-col-2")

            with TabPane("Logos", id="tab-logos"):
                with Vertical():
                    for i in range(4):
                        logo = self._config.logos[i] if i < len(self._config.logos) else {}
                        with Horizontal(classes="logo-row"):
                            yield Switch(value=logo.get("enabled", False), id=f"logo-{i}-enable")
                            yield Input(
                                value=logo.get("path", ""),
                                id=f"logo-{i}-path",
                                placeholder=f"Logo {i+1} path..."
                            )
                            yield Select(
                                [("TL", "top-left"), ("TR", "top-right"),
                                 ("BL", "bottom-left"), ("BR", "bottom-right")],
                                id=f"logo-{i}-pos",
                                value=logo.get("position", "bottom-left")
                            )

        with Horizontal(id="action-bar"):
            yield Button("Process", id="btn-process", variant="primary")
            yield Button("Refresh", id="btn-refresh", variant="default")
            yield Button("Quit", id="btn-quit", variant="error")

        yield Footer()

    def on_mount(self):
        self._refresh_state()

    def _refresh_state(self):
        """Refresh UI state from config."""
        # Border tab
        try:
            bp = self.query_one("#border-preset", RadioSet)
            preset = self._config.border.get("preset", "medium")
            if self._config.border.get("use_custom"):
                custom_btn = bp.query("#custom", RadioButton).first()
                if custom_btn is not None:
                    bp._selected = bp._nodes.index(custom_btn)
            else:
                for btn in bp.query(RadioButton):
                    if btn.value == preset:
                        bp._selected = bp._nodes.index(btn)
                        break
            bp.refresh()
        except Exception:
            pass

        # Custom border
        cb = self._config.border.get("custom", {})
        cbi = self.query_one("#custom-border", Input)
        cbi.value = f"{cb.get('top',0)},{cb.get('bottom',0)},{cb.get('left',0)},{cb.get('right',0)}"

        # Border color
        bc = self._config.border.get("color", [255, 255, 255])
        self.query_one("#border-color", Input).value = f"{bc[0]},{bc[1]},{bc[2]}"

        # EXIF fields - distribute across 3 columns
        col_containers = [self.query_one(f"#exif-col-{i}") for i in range(3)]
        enabled_fields = self._config.exif.get("fields", [])
        all_existing = {}
        for col in col_containers:
            for c in col.children:
                if c.id and c.id.startswith("field-"):
                    all_existing[c.id] = c
        if all_existing:
            for field_id in self._available_fields:
                widget_id = f"field-{field_id}"
                if widget_id in all_existing:
                    all_existing[widget_id].value = field_id in enabled_fields
        else:
            for field_id in self._available_fields:
                label = get_field_label(field_id)
                cb = Checkbox(label, value=field_id in enabled_fields, id=f"field-{field_id}")
                col_idx = _EXIF_FIELD_COLUMN_MAP.get(field_id, 0)
                col_containers[col_idx].mount(cb)

        # Font color
        fc = self._config.exif.get("font_color", [0, 0, 0])
        self.query_one("#font-color", Input).value = f"{fc[0]},{fc[1]},{fc[2]}"

    def _sync_config_from_ui(self):
        """Save current UI state into config object."""
        # Files
        self._config.input_dir = self.query_one("#input-dir", Input).value
        self._config.output_dir = self.query_one("#output-dir", Input).value
        self._config.author_name = self.query_one("#author-name", Input).value

        # Border
        border = self._config.border
        bp = self.query_one("#border-preset", RadioSet)
        if bp._selected is not None:
            pressed = bp._nodes[bp._selected]
            if pressed.value == "custom":
                border["use_custom"] = True
            else:
                border["preset"] = pressed.value
                border["use_custom"] = False
        cb_str = self.query_one("#custom-border", Input).value
        try:
            parts = [int(x.strip()) for x in cb_str.split(",")]
            if len(parts) == 4:
                border["custom"] = {"top": parts[0], "bottom": parts[1], "left": parts[2], "right": parts[3]}
        except ValueError:
            pass
        try:
            border["color"] = [int(x) for x in self.query_one("#border-color", Input).value.split(",")]
        except ValueError:
            pass
        self._config.border = border

        # EXIF
        exif = self._config.exif
        exif["position"] = self.query_one("#text-position", Select).value
        exif["alignment"] = self.query_one("#text-align", Select).value
        try:
            exif["font_size"] = int(self.query_one("#font-size", Input).value)
        except ValueError:
            pass
        try:
            exif["font_color"] = [int(x) for x in self.query_one("#font-color", Input).value.split(",")]
        except ValueError:
            pass
        # Gather enabled fields
        enabled = []
        for field_id in self._available_fields:
            cb = self.query_one(f"#field-{field_id}", Checkbox)
            if cb.value:
                enabled.append(field_id)
        exif["fields"] = enabled
        self._config.exif = exif

        # Logos
        logos = []
        for i in range(4):
            sw = self.query_one(f"#logo-{i}-enable", Switch)
            inp = self.query_one(f"#logo-{i}-path", Input)
            sel = self.query_one(f"#logo-{i}-pos", Select)
            logos.append({
                "enabled": sw.value,
                "path": inp.value,
                "position": sel.value if sel.value else "bottom-left",
                "scale": 0.5,
                "offset_x": 0,
                "offset_y": 0,
            })
        self._config.logos = logos

        self._config.save()

    @on(Button.Pressed, "#btn-browse-dir")
    def on_browse_dir(self):
        start = self.query_one("#input-dir", Input).value or os.path.expanduser("~")
        if not os.path.isdir(start):
            start = os.path.expanduser("~")
        self.app.push_screen(DirPickerScreen(start, lambda path: self._set_input_dir(path)))

    def _set_input_dir(self, path):
        self.query_one("#input-dir", Input).value = path

    @on(Button.Pressed, "#btn-browse-out")
    def on_browse_out(self):
        start = self.query_one("#output-dir", Input).value or os.path.expanduser("~")
        if not os.path.isdir(start):
            start = os.path.expanduser("~")
        self.app.push_screen(DirPickerScreen(start, lambda path: self._set_output_dir(path)))

    def _set_output_dir(self, path):
        self.query_one("#output-dir", Input).value = path

    @on(Button.Pressed, "#btn-load-dir")
    async def on_load_dir(self):
        input_dir = self.query_one("#input-dir", Input).value
        if not input_dir or not os.path.isdir(input_dir):
            self.query_one("#dir-status", Label).update("Invalid directory!")
            return
        files = get_supported_images_from_dir(input_dir)
        # Filter hidden files (safety net)
        files = [f for f in files if not os.path.basename(f).startswith(".")]
        self._image_files = files

        list_view = self.query_one("#file-list", ListView)
        await list_view.clear()
        for f in files:
            item = FileListItem(
                Label(f"✓ {os.path.basename(f)}"),
                path=f,
                selected=True,
            )
            list_view.append(item)

        self._update_selection_status()

    def _update_selection_status(self):
        list_view = self.query_one("#file-list", ListView)
        selected = sum(1 for item in list_view.children
                       if isinstance(item, FileListItem) and item.selected)
        total = len(list_view.children)
        self.query_one("#dir-status", Label).update(
            f"{selected} of {total} image(s) selected"
        )

    @on(Button.Pressed, "#btn-select-all")
    def on_select_all(self):
        list_view = self.query_one("#file-list", ListView)
        for item in list_view.children:
            if isinstance(item, FileListItem) and not item.selected:
                item.selected = True
                label = item.query_one(Label)
                label.update(f"✓ {os.path.basename(item.path)}")
        self._update_selection_status()

    @on(Button.Pressed, "#btn-deselect-all")
    def on_deselect_all(self):
        list_view = self.query_one("#file-list", ListView)
        for item in list_view.children:
            if isinstance(item, FileListItem) and item.selected:
                item.selected = False
                label = item.query_one(Label)
                label.update(f"✗ {os.path.basename(item.path)}")
        self._update_selection_status()

    @on(ListView.Selected, "#file-list")
    def on_file_selected(self, event):
        item = event.item
        if isinstance(item, FileListItem):
            item.selected = not item.selected
            label = item.query_one(Label)
            basename = os.path.basename(item.path)
            label.update(f"{'✓' if item.selected else '✗'} {basename}")
            self._update_selection_status()

    @on(Button.Pressed, "#btn-process")
    def on_process(self):
        self._sync_config_from_ui()

        # Gather selected images from the file list
        list_view = self.query_one("#file-list", ListView)
        images = [item.path for item in list_view.children
                  if isinstance(item, FileListItem) and item.selected]

        if not images:
            self.notify("No images selected! Load a directory and select images first.", severity="error")
            return

        self.app.push_screen(ProcessingScreen(images, self._config))

    @on(Button.Pressed, "#btn-refresh")
    def on_refresh(self):
        self._refresh_state()

    @on(Button.Pressed, "#btn-quit")
    def on_quit(self):
        self._sync_config_from_ui()
        self.app.exit()


class PyBorderEXIFTUI(App):
    """PyBorderEXIF Text User Interface."""

    CSS = """
    Screen {
        align: center middle;
    }

    .section-label {
        margin-top: 1;
        text-style: bold;
        color: $accent;
    }

    #dir-panel {
        width: 40%;
        margin-right: 1;
    }

    #options-panel {
        width: 60%;
    }

    #file-select-actions {
        margin-bottom: 1;
    }

    #file-select-actions Button {
        margin-right: 1;
    }

    #file-list-container {
        height: 15;
    }

    .exif-column {
        width: 1fr;
    }

    .column-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .logo-row {
        margin-bottom: 1;
    }

    #action-bar {
        dock: bottom;
        height: 3;
        align: center middle;
    }

    #action-bar Button {
        margin: 0 1;
    }

    TabPane {
        padding: 1;
    }

    .exif-form-col {
        width: 1fr;
        margin-right: 1;
    }

    #processing-container {
        align: center middle;
        width: 80%;
        height: auto;
        margin-top: 5;
    }

    #status-label {
        text-align: center;
        margin-bottom: 2;
    }

    #progress {
        width: 100%;
    }

    #current-file {
        text-align: center;
        margin-top: 1;
    }

    #picker-hint {
        text-align: center;
        margin: 1 0;
        color: $text-muted;
    }

    #picker-actions {
        dock: bottom;
        height: 3;
        align: center middle;
    }

    #picker-actions Button {
        margin: 0 1;
    }
    """

    def __init__(self, config):
        super().__init__()
        self._config = config

    def on_mount(self):
        self.push_screen(MainScreen(self._config))


def main():
    config = Config()
    app = PyBorderEXIFTUI(config)
    app.run()


if __name__ == "__main__":
    main()
