#!/usr/bin/env python3
"""TUI (Text User Interface) for PyBorderEXIF using Textual."""

import os
import sys
import asyncio

from border_exif.config import (
    Config, BORDER_PRESETS, FONT_FAMILIES, DEFAULT_FONT_FAMILY, BREAK_MARKER,
)
from border_exif.core import process_images, get_supported_images_from_dir
from border_exif.exif_reader import (
    get_all_field_names, get_field_label, extract_exif, exif_to_display_lines,
)

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.widgets import (
        Header, Footer, Button, Label, Input, Select, Switch,
        Static, DirectoryTree, ListView, ListItem, ProgressBar,
        Checkbox, RadioSet, RadioButton, TabbedContent, TabPane, TextArea,
    )
    from textual.screen import Screen
    from textual import on
    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False


if not HAS_TEXTUAL:
    print("Textual is required for TUI mode. Install with: pip install textual")
    sys.exit(1)


class PreviewItem(ListItem):
    """An item in the preview image list."""

    def __init__(self, *children, path, **kwargs):
        super().__init__(*children, **kwargs)
        self.path = path


class PreviewScreen(Screen):
    """Screen to preview and edit EXIF text per image before processing."""

    def __init__(self, image_paths, config):
        super().__init__()
        self._image_paths = list(image_paths)
        self._config = config
        self._per_image_lines = {}
        self._current_edit_path = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="preview-main"):
            with Vertical(id="preview-left"):
                yield Label("Images:", classes="section-label")
                yield ListView(id="preview-image-list")
            with Vertical(id="preview-right"):
                yield Label("Text Lines (edit as needed):", classes="section-label")
                yield TextArea(id="preview-text", language=None)
        with Horizontal(id="preview-actions"):
            yield Label("", id="preview-status")
            yield Button("Process All", id="btn-process-all", variant="primary")
            yield Button("Cancel", id="btn-cancel-preview", variant="default")
        yield Footer()

    def on_mount(self):
        self._load_exif_data()

    @on(ListView.Selected, "#preview-image-list")
    def on_image_select(self, event):
        if self._current_edit_path is not None:
            self._save_current_text()
        if isinstance(event.item, PreviewItem):
            self._current_edit_path = event.item.path
            lines = self._per_image_lines.get(event.item.path, [])
            text_area = self.query_one("#preview-text", TextArea)
            text_area.text = "\n".join(lines)

    def _save_current_text(self):
        if self._current_edit_path is None:
            return
        text_area = self.query_one("#preview-text", TextArea)
        text = text_area.text
        lines = text.split("\n")
        if lines == [""]:
            lines = []
        self._per_image_lines[self._current_edit_path] = lines

    def _load_exif_data(self):
        exif_cfg = self._config.exif
        fields = exif_cfg.get("fields", [])
        field_layout = exif_cfg.get("field_layout")
        author = self._config.author_name
        list_view = self.query_one("#preview-image-list", ListView)
        status = self.query_one("#preview-status", Label)

        for i, path in enumerate(self._image_paths):
            try:
                exif_data = extract_exif(path)
                lines = exif_to_display_lines(exif_data, fields, author, field_layout)
            except Exception:
                lines = [author] if author else []
            self._per_image_lines[path] = lines
            item = PreviewItem(
                Label(os.path.basename(path)),
                path=path,
            )
            list_view.append(item)
            status.update(f"Loaded {i + 1}/{len(self._image_paths)}")

        if self._image_paths:
            list_view.index = 0
            # Trigger initial text display
            first_item = list_view.children[0]
            if isinstance(first_item, PreviewItem):
                self._current_edit_path = first_item.path
                lines = self._per_image_lines.get(first_item.path, [])
                self.query_one("#preview-text", TextArea).text = "\n".join(lines)

        status.update(f"{len(self._image_paths)} image(s) — edit text, then Process All")

    @on(Button.Pressed, "#btn-process-all")
    def on_process_all(self):
        self._save_current_text()
        self.dismiss(dict(self._per_image_lines))

    @on(Button.Pressed, "#btn-cancel-preview")
    def on_cancel(self):
        self.dismiss(None)


class ProcessingScreen(Screen):
    """Screen shown during batch processing."""

    def __init__(self, image_paths, config, per_image_lines=None):
        super().__init__()
        self._images = image_paths
        self._config = config
        self._per_image_lines = per_image_lines or {}

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
                lines = self._per_image_lines.get(path)
                await asyncio.to_thread(process_image, path, self._config, text_lines=lines)
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


class LayoutItem(ListItem):
    """An item in the field layout list."""

    def __init__(self, *children, field_id, **kwargs):
        super().__init__(*children, **kwargs)
        self.field_id = field_id


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
                    yield Label("")
                    yield Label("Fixed Aspect Ratio", classes="section-label")
                    with Horizontal(id="fixed-ratio-toggle-row"):
                        yield Switch(value=False, id="fixed-ratio-enable")
                        yield Label("Keep original aspect ratio when adding borders")
                    with Horizontal(id="fixed-ratio-params"):
                        with Vertical(classes="fr-param"):
                            yield Label("a (Left/Right)")
                            yield Input(value="50", id="fr-a", placeholder="px")
                        with Vertical(classes="fr-param"):
                            yield Label("b (Top)")
                            yield Input(value="50", id="fr-b", placeholder="px")
                        with Vertical(classes="fr-param"):
                            yield Label("c (Bottom)")
                            yield Input(value="50", id="fr-c", placeholder="px")
                        with Vertical(classes="fr-param"):
                            yield Label("Auto (computed)")
                            yield Select([("a (L/R)", "a"), ("b (Top)", "b"), ("c (Bottom)", "c")],
                                        id="fr-auto-param", value="c")
                    yield Label("")
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
                        yield Label("Font Family:", classes="section-label")
                        font_opts = [(name, name) for name in FONT_FAMILIES.keys()]
                        yield Select(font_opts, id="font-family", value=DEFAULT_FONT_FAMILY)
                    with Vertical(classes="exif-form-col"):
                        yield Label("Text Alignment:", classes="section-label")
                        yield Select([("Left", "left"), ("Center", "center"), ("Right", "right")],
                                     id="text-align", value="left")
                        yield Label("Font Color (R,G,B):", classes="section-label")
                        yield Input(value="0,0,0", id="font-color")
                        yield Label("Margin (px):", classes="section-label")
                        yield Input(value=str(self._config.exif.get("margin", 10)), id="exif-margin")
                        yield Label("Line Spacing (px):", classes="section-label")
                        yield Input(value=str(self._config.exif.get("line_spacing", 4)), id="exif-line-spacing")

            with TabPane("Field Layout", id="tab-fields"):
                with Horizontal(id="fields-content"):
                    with Vertical(id="layout-list-panel"):
                        yield Label("Layout (order & line breaks):", classes="section-label")
                        yield ListView(id="layout-list")
                    with Vertical(id="layout-controls"):
                        yield Label("Actions:", classes="section-label")
                        yield Button("▲ Up", id="btn-layout-up", variant="default")
                        yield Button("▼ Down", id="btn-layout-down", variant="default")
                        yield Label("")
                        yield Button("↩ Insert Break", id="btn-layout-break", variant="default")
                        yield Button("✕ Remove", id="btn-layout-remove", variant="default")
                        yield Label("")
                        yield Label("Available Fields:", classes="section-label")
                        yield Select([], id="layout-available", prompt="Add field...")
                        yield Label("")
                        yield Button("Reset to Default", id="btn-layout-reset", variant="default")

            with TabPane("Logos", id="tab-logos"):
                with ScrollableContainer(id="logo-scroll"):
                    for i in range(4):
                        logo = self._config.logos[i] if i < len(self._config.logos) else {}
                        with Vertical(classes="logo-group"):
                            yield Label(f"Logo {i + 1}", classes="section-label")
                            with Horizontal(classes="logo-row"):
                                yield Switch(value=logo.get("enabled", False), id=f"logo-{i}-enable")
                                yield Label("Enable", classes="inline-label")
                            with Horizontal(classes="logo-row"):
                                yield Label("Path:", classes="logo-field-label")
                                yield Input(
                                    value=logo.get("path", ""),
                                    id=f"logo-{i}-path",
                                    placeholder=f"Logo {i+1} path..."
                                )
                            with Horizontal(classes="logo-row"):
                                yield Label("Position:", classes="logo-field-label")
                                yield Select(
                                    [("Top-Left", "top-left"), ("Top-Right", "top-right"),
                                     ("Bottom-Left", "bottom-left"), ("Bottom-Right", "bottom-right")],
                                    id=f"logo-{i}-pos",
                                    value=logo.get("position", "bottom-left")
                                )
                            with Vertical(id=f"logo-{i}-bottom-controls", classes="bottom-logo-controls"):
                                yield Label("Bottom Border Settings:", classes="group-label")
                                with Horizontal(classes="logo-row"):
                                    yield Label("Alignment:", classes="logo-field-label")
                                    yield Select(
                                        [("Left", "left"), ("Center", "center"), ("Right", "right")],
                                        id=f"logo-{i}-bottom-layout",
                                        value=logo.get("bottom_layout", "left")
                                    )
                                with Horizontal(classes="logo-row"):
                                    yield Label("Size (%):", classes="logo-field-label")
                                    yield Input(
                                        value=str(logo.get("bottom_size_pct", 80.0)),
                                        id=f"logo-{i}-size-pct",
                                        placeholder="80"
                                    )
                                with Horizontal(classes="logo-row"):
                                    yield Label("Margin H:", classes="logo-field-label")
                                    yield Input(
                                        value=str(logo.get("bottom_margin_x", 10)),
                                        id=f"logo-{i}-margin-x",
                                        placeholder="10"
                                    )
                                with Horizontal(classes="logo-row"):
                                    yield Label("Margin V:", classes="logo-field-label")
                                    yield Input(
                                        value=str(logo.get("bottom_margin_y", 10)),
                                        id=f"logo-{i}-margin-y",
                                        placeholder="10"
                                    )
                                with Horizontal(classes="logo-row"):
                                    yield Label("Text Spacing:", classes="logo-field-label")
                                    yield Input(
                                        value=str(logo.get("bottom_text_spacing", 10)),
                                        id=f"logo-{i}-text-spacing",
                                        placeholder="10"
                                    )

        with Horizontal(id="action-bar"):
            yield Button("Process", id="btn-process", variant="primary")
            yield Button("Refresh", id="btn-refresh", variant="default")
            yield Button("Quit", id="btn-quit", variant="error")

        yield Footer()

    def on_mount(self):
        self._refresh_state()

    def _get_layout_as_list(self):
        """Return current layout from the layout ListView."""
        layout = []
        list_view = self.query_one("#layout-list", ListView)
        for item in list_view.children:
            if isinstance(item, LayoutItem):
                layout.append(item.field_id)
        return layout

    def _rebuild_layout_list(self, layout):
        """Rebuild the layout ListView from a layout list."""
        list_view = self.query_one("#layout-list", ListView)
        list_view.clear()
        for item in layout:
            if item == BREAK_MARKER:
                display = "——— Line Break ———"
            else:
                display = get_field_label(item)
            list_view.append(LayoutItem(Label(display), field_id=item))

    def _get_layout_field_ids(self):
        ids = set()
        list_view = self.query_one("#layout-list", ListView)
        for item in list_view.children:
            if isinstance(item, LayoutItem) and item.field_id != BREAK_MARKER:
                ids.add(item.field_id)
        return ids

    def _refresh_available_fields_combo(self):
        """Refresh the available fields Select with fields not yet in layout."""
        in_layout = self._get_layout_field_ids()
        available = [f for f in self._available_fields if f not in in_layout]
        opts = [(get_field_label(f), f) for f in available]
        sel = self.query_one("#layout-available", Select)
        sel.set_options(opts)

    @on(Button.Pressed, "#btn-layout-up")
    def on_layout_up(self):
        list_view = self.query_one("#layout-list", ListView)
        if list_view.index is None or list_view.index == 0:
            return
        idx = list_view.index
        layout = self._get_layout_as_list()
        layout.insert(idx - 1, layout.pop(idx))
        self._rebuild_layout_list(layout)
        list_view.index = idx - 1

    @on(Button.Pressed, "#btn-layout-down")
    def on_layout_down(self):
        list_view = self.query_one("#layout-list", ListView)
        if list_view.index is None or list_view.index >= len(list_view.children) - 1:
            return
        idx = list_view.index
        layout = self._get_layout_as_list()
        layout.insert(idx + 1, layout.pop(idx))
        self._rebuild_layout_list(layout)
        list_view.index = idx + 1

    @on(Button.Pressed, "#btn-layout-break")
    def on_layout_break(self):
        list_view = self.query_one("#layout-list", ListView)
        item = LayoutItem(Label("——— Line Break ———"), field_id=BREAK_MARKER)
        if list_view.index is not None:
            list_view.mount(item, after=list_view.index)
        else:
            list_view.append(item)

    @on(Button.Pressed, "#btn-layout-remove")
    def on_layout_remove(self):
        list_view = self.query_one("#layout-list", ListView)
        if list_view.index is not None:
            list_view.pop(list_view.index)
        self._refresh_available_fields_combo()

    @on(Select.Changed, "#layout-available")
    def on_layout_add_field(self, event):
        if not event.value or event.value in (Select.BLANK, Select.NULL):
            return
        field_id = event.value
        display = get_field_label(field_id)
        item = LayoutItem(Label(display), field_id=field_id)
        list_view = self.query_one("#layout-list", ListView)
        if list_view.index is not None:
            list_view.mount(item, after=list_view.index)
        else:
            list_view.append(item)
        self.query_one("#layout-available", Select).clear()
        self._refresh_available_fields_combo()

    @on(Button.Pressed, "#btn-layout-reset")
    def on_layout_reset(self):
        from border_exif.config import DEFAULT_METADATA_FIELDS
        self._rebuild_layout_list(DEFAULT_METADATA_FIELDS)
        self._refresh_available_fields_combo()

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

        # Fixed ratio
        self.query_one("#fixed-ratio-enable", Switch).value = self._config.border.get("use_fixed_ratio", False)
        fr = self._config.border.get("fixed_ratio", {})
        self.query_one("#fr-a", Input).value = str(fr.get("a", 50))
        self.query_one("#fr-b", Input).value = str(fr.get("b", 50))
        self.query_one("#fr-c", Input).value = str(fr.get("c", 50))
        self.query_one("#fr-auto-param", Select).value = fr.get("auto_param", "c")
        self._update_fixed_ratio_inputs()

        # Border color
        bc = self._config.border.get("color", [255, 255, 255])
        self.query_one("#border-color", Input).value = f"{bc[0]},{bc[1]},{bc[2]}"

        # EXIF fields - rebuild layout list only on first mount
        list_view = self.query_one("#layout-list", ListView)
        if len(list_view.children) == 0:
            field_layout = self._config.exif.get("field_layout")
            if field_layout:
                self._rebuild_layout_list(field_layout)
            else:
                enabled_fields = self._config.exif.get("fields", [])
                self._rebuild_layout_list(enabled_fields)
            self._refresh_available_fields_combo()

        # Font color
        fc = self._config.exif.get("font_color", [0, 0, 0])
        self.query_one("#font-color", Input).value = f"{fc[0]},{fc[1]},{fc[2]}"

        # Font family
        ff = self._config.exif.get("font_family", DEFAULT_FONT_FAMILY)
        try:
            self.query_one("#font-family", Select).value = ff
        except Exception:
            pass

        # Margin and line spacing
        self.query_one("#exif-margin", Input).value = str(self._config.exif.get("margin", 10))
        self.query_one("#exif-line-spacing", Input).value = str(self._config.exif.get("line_spacing", 4))

        # Logo controls initial state
        for i in range(4):
            self._update_logo_controls_state(i)

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

        # Fixed ratio
        border["use_fixed_ratio"] = self.query_one("#fixed-ratio-enable", Switch).value
        fr = border.get("fixed_ratio", {})
        try:
            fr["a"] = int(self.query_one("#fr-a", Input).value)
        except ValueError:
            pass
        try:
            fr["b"] = int(self.query_one("#fr-b", Input).value)
        except ValueError:
            pass
        try:
            fr["c"] = int(self.query_one("#fr-c", Input).value)
        except ValueError:
            pass
        fr["auto_param"] = self.query_one("#fr-auto-param", Select).value
        border["fixed_ratio"] = fr

        self._config.border = border

        # EXIF
        exif = self._config.exif
        exif["position"] = self.query_one("#text-position", Select).value
        exif["alignment"] = self.query_one("#text-align", Select).value
        try:
            exif["font_size"] = int(self.query_one("#font-size", Input).value)
        except ValueError:
            pass
        exif["font_family"] = self.query_one("#font-family", Select).value
        try:
            exif["font_color"] = [int(x) for x in self.query_one("#font-color", Input).value.split(",")]
        except ValueError:
            pass
        try:
            exif["margin"] = int(self.query_one("#exif-margin", Input).value)
        except ValueError:
            pass
        try:
            exif["line_spacing"] = int(self.query_one("#exif-line-spacing", Input).value)
        except ValueError:
            pass
        # Gather field layout
        layout = self._get_layout_as_list()
        exif["field_layout"] = layout
        exif["fields"] = [item for item in layout if item != BREAK_MARKER]
        self._config.exif = exif

        # Logos
        logos = []
        for i in range(4):
            sw = self.query_one(f"#logo-{i}-enable", Switch)
            inp = self.query_one(f"#logo-{i}-path", Input)
            sel = self.query_one(f"#logo-{i}-pos", Select)
            logo = {
                "enabled": sw.value,
                "path": inp.value,
                "position": sel.value if sel.value else "bottom-left",
                "scale": 0.5,
                "offset_x": 0,
                "offset_y": 0,
            }
            # Read bottom-border controls
            try:
                logo["bottom_layout"] = self.query_one(f"#logo-{i}-bottom-layout", Select).value
            except Exception:
                logo["bottom_layout"] = "left"
            try:
                logo["bottom_size_pct"] = float(self.query_one(f"#logo-{i}-size-pct", Input).value or 80)
            except (ValueError, Exception):
                logo["bottom_size_pct"] = 80.0
            try:
                logo["bottom_margin_x"] = int(self.query_one(f"#logo-{i}-margin-x", Input).value or 10)
            except (ValueError, Exception):
                logo["bottom_margin_x"] = 10
            try:
                logo["bottom_margin_y"] = int(self.query_one(f"#logo-{i}-margin-y", Input).value or 10)
            except (ValueError, Exception):
                logo["bottom_margin_y"] = 10
            try:
                logo["bottom_text_spacing"] = int(self.query_one(f"#logo-{i}-text-spacing", Input).value or 10)
            except (ValueError, Exception):
                logo["bottom_text_spacing"] = 10
            logos.append(logo)
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

    def _update_fixed_ratio_inputs(self):
        """Disable the input for the auto-calculated parameter."""
        auto = self.query_one("#fr-auto-param", Select).value
        for param_id in ("#fr-a", "#fr-b", "#fr-c"):
            inp = self.query_one(param_id, Input)
            if param_id == f"#fr-{auto}":
                inp.disabled = True
                inp.add_class("fr-auto-disabled")
            else:
                inp.disabled = False
                inp.remove_class("fr-auto-disabled")

    @on(Switch.Changed, "#fixed-ratio-enable")
    def on_fixed_ratio_toggled(self):
        self._update_fixed_ratio_inputs()

    @on(Select.Changed, "#fr-auto-param")
    def on_fixed_ratio_auto_changed(self):
        self._update_fixed_ratio_inputs()

    def _update_logo_controls_state(self, i):
        """Enable/disable bottom-border controls based on position and layout."""
        try:
            pos_select = self.query_one(f"#logo-{i}-pos", Select)
        except Exception:
            return
        try:
            controls = self.query_one(f"#logo-{i}-bottom-controls", Vertical)
        except Exception:
            return

        is_bottom = pos_select.value is not None and str(pos_select.value).startswith("bottom-")
        controls.disabled = not is_bottom

        if is_bottom:
            try:
                layout_sel = self.query_one(f"#logo-{i}-bottom-layout", Select)
                is_center = layout_sel.value == "center"
            except Exception:
                is_center = False
            try:
                mx = self.query_one(f"#logo-{i}-margin-x", Input)
                if is_center:
                    mx.disabled = True
                    mx.add_class("fr-auto-disabled")
                else:
                    mx.disabled = False
                    mx.remove_class("fr-auto-disabled")
            except Exception:
                pass

    @on(Select.Changed)
    def on_logo_select_changed(self, event):
        """React to logo position or layout changes to update control states."""
        widget_id = event.widget.id or ""
        if widget_id.startswith("logo-") and (widget_id.endswith("-pos") or widget_id.endswith("-bottom-layout")):
            try:
                idx = int(widget_id.replace("logo-", "").split("-")[0])
                self._update_logo_controls_state(idx)
            except (ValueError, IndexError):
                pass

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

        # Show preview screen, then process on dismiss
        def on_preview_done(result):
            if result is not None:
                self.app.push_screen(ProcessingScreen(images, self._config, per_image_lines=result))

        self.app.push_screen(PreviewScreen(images, self._config), callback=on_preview_done)

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

    #fixed-ratio-toggle-row {
        margin-bottom: 1;
    }

    #fixed-ratio-params {
        margin-bottom: 1;
    }

    .fr-param {
        width: 1fr;
        margin-right: 1;
    }

    .fr-auto-disabled {
        opacity: 0.5;
    }

    #preview-main {
        height: 1fr;
    }

    #preview-left {
        width: 30%;
        margin-right: 1;
    }

    #preview-right {
        width: 70%;
    }

    #preview-image-list {
        height: 1fr;
    }

    #preview-text {
        height: 1fr;
    }

    #preview-actions {
        dock: bottom;
        height: 3;
        align: center middle;
    }

    #preview-actions Button {
        margin: 0 1;
    }

    #preview-status {
        margin-right: 1;
    }

    #layout-list-panel {
        width: 3fr;
        margin-right: 1;
    }

    #layout-controls {
        width: 1fr;
    }

    #layout-list {
        height: 1fr;
    }

    #layout-controls Button {
        width: 100%;
        margin-bottom: 1;
    }

    #layout-available {
        width: 100%;
    }

    #logo-scroll {
        height: 1fr;
    }

    .logo-group {
        border: solid $accent;
        padding: 1;
        margin-bottom: 1;
    }

    .bottom-logo-controls {
        margin-left: 2;
        padding: 1;
        border: dashed $surface;
    }

    .group-label {
        text-style: italic;
        color: $text-muted;
        margin-bottom: 1;
    }

    .inline-label {
        margin-left: 1;
    }

    .logo-field-label {
        width: 14;
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
