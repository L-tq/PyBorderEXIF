#!/usr/bin/env python3
"""GUI (Graphical User Interface) for PyBorderEXIF using tkinter."""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

from border_exif.config import (
    Config, BORDER_PRESETS, DEFAULT_METADATA_FIELDS,
    FONT_FAMILIES, DEFAULT_FONT_FAMILY, BREAK_MARKER,
)
from border_exif.core import process_image, process_images, get_supported_images_from_dir
from border_exif.exif_reader import (
    get_all_field_names, get_field_label, extract_exif, exif_to_display_lines,
)


class PreviewDialog(tk.Toplevel):
    """Dialog to preview and edit EXIF text for each image before processing."""

    def __init__(self, parent, image_paths, config):
        super().__init__(parent)
        self.title("Preview & Edit Text")
        self.geometry("1000x650")
        self.minsize(800, 500)
        self.transient(parent)
        self.grab_set()

        self._image_paths = list(image_paths)
        self._config = config
        self._per_image_lines = {}
        self._result = None

        self._build_ui()
        self._load_exif_data()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window()

    @property
    def result(self):
        return self._result

    def _build_ui(self):
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: image list
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, width=250)

        ttk.Label(left_frame, text="Images:", font=("", 10, "bold")).pack(anchor=tk.W, padx=5, pady=(5, 2))
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._image_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, exportselection=False)
        img_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._image_listbox.yview)
        self._image_listbox.config(yscrollcommand=img_scroll.set)
        self._image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        img_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._image_listbox.bind("<<ListboxSelect>>", self._on_image_select)

        for p in self._image_paths:
            self._image_listbox.insert(tk.END, os.path.basename(p))

        # Right: text editor
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, width=700)

        ttk.Label(right_frame, text="Text Lines (one per line, edit as needed):",
                  font=("", 10, "bold")).pack(anchor=tk.W, padx=5, pady=(5, 2))

        text_frame = ttk.Frame(right_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("monospace", 11),
                                    undo=True, exportselection=False)
        text_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self._text_widget.yview)
        self._text_widget.config(yscrollcommand=text_scroll.set)
        self._text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(btn_frame, textvariable=self._status_var).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Process All", command=self._on_process_all).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT, padx=5)

    def _load_exif_data(self):
        exif_cfg = self._config.exif
        fields = exif_cfg.get("fields", [])
        field_layout = exif_cfg.get("field_layout")
        author = self._config.author_name

        for i, path in enumerate(self._image_paths):
            try:
                exif_data = extract_exif(path)
                lines = exif_to_display_lines(exif_data, fields, author, field_layout)
            except Exception:
                lines = [author] if author else []
            self._per_image_lines[path] = lines
            self._status_var.set(f"Loaded {i + 1}/{len(self._image_paths)}")

        if self._image_paths:
            self._image_listbox.selection_set(0)
            self._on_image_select()

        self._status_var.set(f"{len(self._image_paths)} image(s) loaded — edit text and click Process All")

    def _on_image_select(self, event=None):
        sel = self._image_listbox.curselection()
        if not sel:
            return
        path = self._image_paths[sel[0]]

        # Save current text if any was being edited
        current_sel = getattr(self, '_current_edit_idx', None)
        if current_sel is not None and current_sel < len(self._image_paths):
            self._save_current_text()

        self._current_edit_idx = sel[0]
        lines = self._per_image_lines.get(path, [])
        self._text_widget.delete("1.0", tk.END)
        self._text_widget.insert("1.0", "\n".join(lines))

    def _save_current_text(self):
        idx = getattr(self, '_current_edit_idx', None)
        if idx is None or idx >= len(self._image_paths):
            return
        path = self._image_paths[idx]
        text = self._text_widget.get("1.0", "end-1c")
        lines = text.split("\n")
        if lines == [""]:
            lines = []
        self._per_image_lines[path] = lines

    def _on_process_all(self):
        self._save_current_text()
        self._result = dict(self._per_image_lines)
        self.destroy()

    def _on_cancel(self):
        self._result = None
        self.destroy()


class PyBorderEXIFGUI:
    """Main GUI application window."""

    def __init__(self):
        self._config = Config()
        self._image_files = []
        self._field_vars = {}
        self._label_to_id = {}
        self._id_to_label = {}

        self._root = tk.Tk()
        self._root.title("PyBorderEXIF")
        self._root.geometry("900x700")
        self._root.minsize(800, 600)

        self._build_ui()
        self._load_config_to_ui()

    def run(self):
        self._root.mainloop()

    def _build_ui(self):
        # Menu bar
        menubar = tk.Menu(self._root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Reset Config", command=self._reset_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self._root.config(menu=menubar)

        # Main notebook (tabs)
        notebook = ttk.Notebook(self._root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Files Tab ---
        files_frame = ttk.Frame(notebook)
        notebook.add(files_frame, text="Files")

        # Input directory
        ttk.Label(files_frame, text="Input Directory:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self._input_dir_var = tk.StringVar()
        ttk.Entry(files_frame, textvariable=self._input_dir_var, width=60).grid(row=0, column=1, sticky=tk.EW, padx=5)
        ttk.Button(files_frame, text="Browse", command=self._browse_input_dir).grid(row=0, column=2, padx=5)
        ttk.Button(files_frame, text="Load Images", command=self._load_dir_images).grid(row=0, column=3, padx=5)

        # Image list
        ttk.Label(files_frame, text="Images:").grid(row=1, column=0, sticky=tk.NW, padx=5, pady=5)
        list_frame = ttk.Frame(files_frame)
        list_frame.grid(row=1, column=1, columnspan=3, sticky=tk.NSEW, padx=5, pady=5)
        self._image_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=8)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._image_listbox.yview)
        self._image_listbox.config(yscrollcommand=scrollbar.set)
        self._image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add individual files button
        ttk.Button(files_frame, text="Add Files", command=self._add_files).grid(row=2, column=1, sticky=tk.W, padx=5)

        # Output directory
        ttk.Label(files_frame, text="Output Directory:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self._output_dir_var = tk.StringVar()
        ttk.Entry(files_frame, textvariable=self._output_dir_var, width=60).grid(row=3, column=1, sticky=tk.EW, padx=5)
        ttk.Button(files_frame, text="Browse", command=self._browse_output_dir).grid(row=3, column=2, padx=5)

        files_frame.columnconfigure(1, weight=1)
        files_frame.rowconfigure(1, weight=1)

        # --- Border Tab ---
        border_frame = ttk.Frame(notebook)
        notebook.add(border_frame, text="Border")

        self._border_preset_var = tk.StringVar(value="medium")
        ttk.Label(border_frame, text="Preset:", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        row = 1
        for name in BORDER_PRESETS:
            ttk.Radiobutton(border_frame, text=name.title(), variable=self._border_preset_var,
                            value=name).grid(row=row, column=0, sticky=tk.W, padx=20)
            row += 1
        ttk.Radiobutton(border_frame, text="Custom", variable=self._border_preset_var,
                        value="custom").grid(row=row, column=0, sticky=tk.W, padx=20)

        ttk.Label(border_frame, text="Custom (top, bottom, left, right):").grid(row=row + 1, column=0, sticky=tk.W, padx=5, pady=5)
        custom_frame = ttk.Frame(border_frame)
        custom_frame.grid(row=row + 2, column=0, sticky=tk.W, padx=20)
        self._border_custom_vars = {}
        for i, side in enumerate(["top", "bottom", "left", "right"]):
            ttk.Label(custom_frame, text=side.title()).grid(row=0, column=i * 2, padx=2)
            var = tk.IntVar(value=0)
            self._border_custom_vars[side] = var
            ttk.Spinbox(custom_frame, from_=0, to=500, textvariable=var, width=6).grid(row=1, column=i * 2, padx=2)

        # Fixed ratio
        fr_row = row + 3
        ttk.Separator(border_frame, orient=tk.HORIZONTAL).grid(row=fr_row, column=0, sticky=tk.EW, padx=5, pady=10)
        self._fixed_ratio_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(border_frame, text="Fixed Aspect Ratio - keep original ratio when adding borders",
                        variable=self._fixed_ratio_var, command=self._on_fixed_ratio_toggle).grid(
            row=fr_row + 1, column=0, sticky=tk.W, padx=5, pady=2)

        fr_params_frame = ttk.Frame(border_frame)
        fr_params_frame.grid(row=fr_row + 2, column=0, sticky=tk.W, padx=20, pady=5)
        self._fr_params_frame = fr_params_frame

        self._fr_vars = {}
        for i, (label, key) in enumerate([("a (L/R)", "a"), ("b (Top)", "b"), ("c (Bottom)", "c")]):
            ttk.Label(fr_params_frame, text=label).grid(row=0, column=i * 2, padx=2)
            var = tk.IntVar(value=50)
            self._fr_vars[key] = var
            w = ttk.Spinbox(fr_params_frame, from_=0, to=2000, textvariable=var, width=6)
            w.grid(row=1, column=i * 2, padx=2)
            self._fr_vars[key + "_widget"] = w

        ttk.Label(fr_params_frame, text="Auto:").grid(row=0, column=6, padx=(10, 2))
        self._fr_auto_var = tk.StringVar(value="c")
        fr_auto = ttk.Combobox(fr_params_frame, textvariable=self._fr_auto_var,
                               values=["a", "b", "c"], state="readonly", width=3)
        fr_auto.grid(row=1, column=6, padx=2)
        fr_auto.bind("<<ComboboxSelected>>", lambda e: self._on_fixed_ratio_auto_changed())

        ttk.Label(border_frame, text="Border Color:").grid(row=fr_row + 3, column=0, sticky=tk.W, padx=5, pady=5)
        color_frame = ttk.Frame(border_frame)
        color_frame.grid(row=fr_row + 4, column=0, sticky=tk.W, padx=20)
        self._border_color_r = tk.IntVar(value=255)
        self._border_color_g = tk.IntVar(value=255)
        self._border_color_b = tk.IntVar(value=255)
        for i, (label, var) in enumerate([("R", self._border_color_r), ("G", self._border_color_g), ("B", self._border_color_b)]):
            ttk.Label(color_frame, text=label).grid(row=0, column=i * 2, padx=2)
            ttk.Spinbox(color_frame, from_=0, to=255, textvariable=var, width=5).grid(row=1, column=i * 2, padx=2)
        ttk.Button(border_frame, text="Pick Color...", command=self._pick_border_color).grid(row=fr_row + 5, column=0, sticky=tk.W, padx=20, pady=5)

        # --- EXIF Tab ---
        exif_frame = ttk.Frame(notebook)
        notebook.add(exif_frame, text="EXIF")
        exif_frame.columnconfigure(1, weight=1)

        ttk.Label(exif_frame, text="Author Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self._author_var = tk.StringVar()
        ttk.Entry(exif_frame, textvariable=self._author_var, width=40).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(exif_frame, text="Text Position:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self._text_pos_var = tk.StringVar(value="bottom")
        pos_combo = ttk.Combobox(exif_frame, textvariable=self._text_pos_var,
                                 values=["top", "bottom", "left", "right"], state="readonly", width=10)
        pos_combo.grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(exif_frame, text="Text Alignment:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self._text_align_var = tk.StringVar(value="left")
        align_combo = ttk.Combobox(exif_frame, textvariable=self._text_align_var,
                                   values=["left", "center", "right"], state="readonly", width=10)
        align_combo.grid(row=2, column=1, sticky=tk.W, padx=5)

        ttk.Label(exif_frame, text="Font Size:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self._font_size_var = tk.IntVar(value=24)
        ttk.Spinbox(exif_frame, from_=8, to=120, textvariable=self._font_size_var, width=8).grid(row=3, column=1, sticky=tk.W, padx=5)

        ttk.Label(exif_frame, text="Font Family:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self._font_family_var = tk.StringVar(value=DEFAULT_FONT_FAMILY)
        font_families_list = list(FONT_FAMILIES.keys())
        font_family_combo = ttk.Combobox(exif_frame, textvariable=self._font_family_var,
                                         values=font_families_list, state="readonly", width=24)
        font_family_combo.grid(row=4, column=1, sticky=tk.W, padx=5)

        ttk.Label(exif_frame, text="Font Color:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        font_color_frame = ttk.Frame(exif_frame)
        font_color_frame.grid(row=5, column=1, sticky=tk.W, padx=5)
        self._font_color_r = tk.IntVar(value=0)
        self._font_color_g = tk.IntVar(value=0)
        self._font_color_b = tk.IntVar(value=0)
        for i, (label, var) in enumerate([("R", self._font_color_r), ("G", self._font_color_g), ("B", self._font_color_b)]):
            ttk.Label(font_color_frame, text=label).grid(row=0, column=i * 2, padx=2)
            ttk.Spinbox(font_color_frame, from_=0, to=255, textvariable=var, width=5).grid(row=1, column=i * 2, padx=2)
        ttk.Button(font_color_frame, text="Pick...", command=self._pick_font_color).grid(row=1, column=6, padx=5)

        # Field Layout Editor
        self._field_vars = {}
        layout_header = ttk.Frame(exif_frame)
        layout_header.grid(row=6, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=(10, 0))
        ttk.Label(layout_header, text="Field Layout:", font=("", 10, "bold")).pack(side=tk.LEFT)
        ttk.Button(layout_header, text="Reset to Default", command=self._reset_field_layout).pack(side=tk.RIGHT)

        layout_container = ttk.Frame(exif_frame)
        layout_container.grid(row=7, column=0, columnspan=2, sticky=tk.NSEW, padx=10, pady=5)
        exif_frame.rowconfigure(7, weight=1)

        # Layout listbox with scrollbar
        layout_list_frame = ttk.Frame(layout_container)
        layout_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._layout_listbox = tk.Listbox(layout_list_frame, selectmode=tk.SINGLE, height=8)
        layout_scrollbar = ttk.Scrollbar(layout_list_frame, orient=tk.VERTICAL, command=self._layout_listbox.yview)
        self._layout_listbox.config(yscrollcommand=layout_scrollbar.set)
        self._layout_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        layout_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Control buttons
        layout_btn_frame = ttk.Frame(layout_container)
        layout_btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Button(layout_btn_frame, text="▲ Up", command=self._layout_move_up).pack(fill=tk.X, pady=1)
        ttk.Button(layout_btn_frame, text="▼ Down", command=self._layout_move_down).pack(fill=tk.X, pady=1)
        ttk.Separator(layout_btn_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4)
        ttk.Button(layout_btn_frame, text="+ Field", command=self._layout_add_field).pack(fill=tk.X, pady=1)
        ttk.Button(layout_btn_frame, text="− Remove", command=self._layout_remove_item).pack(fill=tk.X, pady=1)
        ttk.Separator(layout_btn_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4)
        ttk.Button(layout_btn_frame, text="↩ Break", command=self._layout_insert_break).pack(fill=tk.X, pady=1)

        # Available fields for adding
        ttk.Label(layout_container, text="Available:").pack(side=tk.LEFT, padx=(5, 0))
        self._available_fields_combo = ttk.Combobox(layout_container, state="readonly", width=16)
        self._available_fields_combo.pack(side=tk.LEFT, padx=5)
        self._available_fields_combo.bind("<<ComboboxSelected>>", lambda e: self._layout_add_field())
        self._refresh_available_fields_combo()

        # --- Logos Tab ---
        logos_frame = ttk.Frame(notebook)
        notebook.add(logos_frame, text="Logos")

        self._logo_widgets = []
        for i in range(4):
            row_offset = i * 2
            ttk.Label(logos_frame, text=f"Logo {i + 1}:", font=("", 9, "bold")).grid(
                row=row_offset, column=0, sticky=tk.W, padx=5, pady=2)

            enable_var = tk.BooleanVar(value=False)
            path_var = tk.StringVar()
            pos_var = tk.StringVar(value="bottom-left")

            ttk.Checkbutton(logos_frame, text="Enable", variable=enable_var).grid(
                row=row_offset, column=1, sticky=tk.W, padx=5)

            path_frame = ttk.Frame(logos_frame)
            path_frame.grid(row=row_offset + 1, column=0, columnspan=4, sticky=tk.EW, padx=20, pady=2)
            ttk.Entry(path_frame, textvariable=path_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Button(path_frame, text="Browse",
                       command=lambda v=path_var, p=pos_var: self._browse_logo(v)).pack(side=tk.LEFT, padx=5)
            ttk.Combobox(path_frame, textvariable=pos_var,
                         values=["top-left", "top-right", "bottom-left", "bottom-right",
                                 "center-top", "center-bottom", "left-center", "right-center"],
                         state="readonly", width=15).pack(side=tk.LEFT, padx=5)

            self._logo_widgets.append({
                "enable": enable_var,
                "path": path_var,
                "position": pos_var,
            })

        logos_frame.columnconfigure(0, weight=1)

        # --- Bottom action bar ---
        action_frame = ttk.Frame(self._root)
        action_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        self._progress_var = tk.StringVar(value="Ready")
        ttk.Label(action_frame, textvariable=self._progress_var).pack(side=tk.LEFT, padx=5)

        ttk.Button(action_frame, text="Process", command=self._on_process, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)

        # Progress bar
        self._progress_bar = ttk.Progressbar(action_frame, mode="determinate", length=200)
        self._progress_bar.pack(side=tk.RIGHT, padx=5)

    def _refresh_available_fields_combo(self):
        """Refresh the list of available fields (not yet in layout)."""
        in_layout = self._get_layout_field_ids()
        available = [f for f in get_all_field_names() if f not in in_layout]
        self._available_fields_combo["values"] = [get_field_label(f) for f in available]
        self._available_fields_map = {get_field_label(f): f for f in available}

    def _get_layout_field_ids(self):
        """Return list of field IDs currently in the layout (excluding breaks)."""
        ids = []
        for i in range(self._layout_listbox.size()):
            text = self._layout_listbox.get(i)
            if text != "——— Line Break ———":
                ids.append(self._label_to_id.get(text, text))
        return ids

    def _refresh_layout_listbox(self):
        """Rebuild the layout listbox from current layout state."""
        self._layout_listbox.delete(0, tk.END)
        layout = self._get_current_layout()
        for item in layout:
            if item == BREAK_MARKER:
                self._layout_listbox.insert(tk.END, "——— Line Break ———")
            else:
                label = get_field_label(item)
                self._label_to_id[label] = item
                self._id_to_label[item] = label
                self._layout_listbox.insert(tk.END, label)

    def _get_current_layout(self):
        """Return current layout as list of field IDs and BREAK_MARKER strings."""
        layout = []
        for i in range(self._layout_listbox.size()):
            text = self._layout_listbox.get(i)
            if text == "——— Line Break ———":
                layout.append(BREAK_MARKER)
            else:
                layout.append(self._label_to_id.get(text, text))
        return layout

    def _layout_move_up(self):
        sel = self._layout_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        text = self._layout_listbox.get(idx)
        self._layout_listbox.delete(idx)
        self._layout_listbox.insert(idx - 1, text)
        self._layout_listbox.selection_set(idx - 1)

    def _layout_move_down(self):
        sel = self._layout_listbox.curselection()
        if not sel or sel[0] >= self._layout_listbox.size() - 1:
            return
        idx = sel[0]
        text = self._layout_listbox.get(idx)
        self._layout_listbox.delete(idx)
        self._layout_listbox.insert(idx + 1, text)
        self._layout_listbox.selection_set(idx + 1)

    def _layout_add_field(self):
        label = self._available_fields_combo.get()
        if not label or label not in self._available_fields_map:
            return
        field_id = self._available_fields_map[label]
        delim_label = get_field_label(field_id)
        self._label_to_id[delim_label] = field_id
        self._id_to_label[field_id] = delim_label

        sel = self._layout_listbox.curselection()
        if sel:
            self._layout_listbox.insert(sel[0] + 1, delim_label)
        else:
            self._layout_listbox.insert(tk.END, delim_label)
        self._refresh_available_fields_combo()

    def _layout_remove_item(self):
        sel = self._layout_listbox.curselection()
        if not sel:
            return
        text = self._layout_listbox.get(sel[0])
        self._layout_listbox.delete(sel[0])
        if text != "——— Line Break ———":
            self._refresh_available_fields_combo()

    def _layout_insert_break(self):
        sel = self._layout_listbox.curselection()
        if sel:
            self._layout_listbox.insert(sel[0] + 1, "——— Line Break ———")
        else:
            self._layout_listbox.insert(tk.END, "——— Line Break ———")

    def _reset_field_layout(self):
        self._layout_listbox.delete(0, tk.END)
        for field_id in DEFAULT_METADATA_FIELDS:
            label = get_field_label(field_id)
            self._label_to_id[label] = field_id
            self._id_to_label[field_id] = label
            self._layout_listbox.insert(tk.END, label)
        self._refresh_available_fields_combo()

    def _populate_layout_from_list(self, field_list):
        """Populate layout listbox from a list of field IDs (no breaks, one per line)."""
        self._layout_listbox.delete(0, tk.END)
        for field_id in field_list:
            label = get_field_label(field_id)
            self._label_to_id[label] = field_id
            self._id_to_label[field_id] = label
            self._layout_listbox.insert(tk.END, label)

    def _load_config_to_ui(self):
        """Populate UI from config."""
        self._input_dir_var.set(self._config.input_dir)
        self._output_dir_var.set(self._config.output_dir)
        self._author_var.set(self._config.author_name)

        border = self._config.border
        if border.get("use_custom"):
            self._border_preset_var.set("custom")
        else:
            self._border_preset_var.set(border.get("preset", "medium"))

        custom = border.get("custom", {})
        for side in ["top", "bottom", "left", "right"]:
            self._border_custom_vars[side].set(custom.get(side, 0))

        bc = border.get("color", [255, 255, 255])
        self._border_color_r.set(bc[0])
        self._border_color_g.set(bc[1])
        self._border_color_b.set(bc[2])

        # Fixed ratio
        self._fixed_ratio_var.set(border.get("use_fixed_ratio", False))
        fr = border.get("fixed_ratio", {})
        for key in ("a", "b", "c"):
            self._fr_vars[key].set(fr.get(key, 50))
        self._fr_auto_var.set(fr.get("auto_param", "c"))
        self._update_fixed_ratio_inputs()

        exif = self._config.exif
        self._text_pos_var.set(exif.get("position", "bottom"))
        self._text_align_var.set(exif.get("alignment", "left"))
        self._font_size_var.set(exif.get("font_size", 24))
        self._font_family_var.set(exif.get("font_family", DEFAULT_FONT_FAMILY))
        fc = exif.get("font_color", [0, 0, 0])
        self._font_color_r.set(fc[0])
        self._font_color_g.set(fc[1])
        self._font_color_b.set(fc[2])

        field_layout = exif.get("field_layout")
        if field_layout:
            self._layout_listbox.delete(0, tk.END)
            for item in field_layout:
                if item == BREAK_MARKER:
                    self._layout_listbox.insert(tk.END, "——— Line Break ———")
                else:
                    label = get_field_label(item)
                    self._label_to_id[label] = item
                    self._id_to_label[item] = label
                    self._layout_listbox.insert(tk.END, label)
        else:
            enabled_fields = exif.get("fields", DEFAULT_METADATA_FIELDS)
            self._populate_layout_from_list(enabled_fields)
        self._refresh_available_fields_combo()

        logos = self._config.logos
        for i, lw in enumerate(self._logo_widgets):
            if i < len(logos):
                lw["enable"].set(logos[i].get("enabled", False))
                lw["path"].set(logos[i].get("path", ""))
                lw["position"].set(logos[i].get("position", "bottom-left"))

    def _sync_ui_to_config(self):
        """Save UI state to config."""
        self._config.input_dir = self._input_dir_var.get()
        self._config.output_dir = self._output_dir_var.get()
        self._config.author_name = self._author_var.get()

        border = self._config.border
        preset = self._border_preset_var.get()
        if preset == "custom":
            border["use_custom"] = True
        else:
            border["preset"] = preset
            border["use_custom"] = False
        border["custom"] = {side: var.get() for side, var in self._border_custom_vars.items()}
        border["color"] = [self._border_color_r.get(), self._border_color_g.get(), self._border_color_b.get()]
        border["use_fixed_ratio"] = self._fixed_ratio_var.get()
        fr = border.get("fixed_ratio", {})
        for key in ("a", "b", "c"):
            fr[key] = self._fr_vars[key].get()
        fr["auto_param"] = self._fr_auto_var.get()
        border["fixed_ratio"] = fr
        self._config.border = border

        exif = self._config.exif
        exif["position"] = self._text_pos_var.get()
        exif["alignment"] = self._text_align_var.get()
        exif["font_size"] = self._font_size_var.get()
        exif["font_family"] = self._font_family_var.get()
        exif["font_color"] = [self._font_color_r.get(), self._font_color_g.get(), self._font_color_b.get()]
        exif["field_layout"] = self._get_current_layout()
        exif["fields"] = [item for item in exif["field_layout"] if item != BREAK_MARKER]
        self._config.exif = exif

        logos = []
        for lw in self._logo_widgets:
            logos.append({
                "enabled": lw["enable"].get(),
                "path": lw["path"].get(),
                "position": lw["position"].get(),
                "scale": 0.5,
                "offset_x": 0,
                "offset_y": 0,
            })
        self._config.logos = logos

        self._config.save()

    def _browse_input_dir(self):
        d = filedialog.askdirectory(title="Select Input Directory")
        if d:
            self._input_dir_var.set(d)

    def _browse_output_dir(self):
        d = filedialog.askdirectory(title="Select Output Directory")
        if d:
            self._output_dir_var.set(d)

    def _browse_logo(self, path_var):
        f = filedialog.askopenfilename(
            title="Select Logo",
            filetypes=[("Logo Files", "*.png *.jpg *.jpeg *.bmp *.gif *.svg"), ("All Files", "*.*")]
        )
        if f:
            path_var.set(f)

    def _load_dir_images(self):
        d = self._input_dir_var.get()
        if not d or not os.path.isdir(d):
            messagebox.showerror("Error", "Please select a valid input directory first.")
            return
        self._image_files = get_supported_images_from_dir(d)
        self._image_listbox.delete(0, tk.END)
        for f in self._image_files:
            self._image_listbox.insert(tk.END, os.path.basename(f))
        self._progress_var.set(f"Loaded {len(self._image_files)} image(s)")

    def _add_files(self):
        files = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.tiff *.arw *.nef *.cr2 *.cr3 *.dng *.rw2 *.orf *.raf *.dng"),
                       ("All Files", "*.*")]
        )
        if files:
            for f in files:
                self._image_files.append(f)
                self._image_listbox.insert(tk.END, os.path.basename(f))
            self._progress_var.set(f"{len(self._image_files)} image(s) loaded")

    def _pick_border_color(self):
        c = colorchooser.askcolor(
            color=(f"#{self._border_color_r.get():02x}{self._border_color_g.get():02x}{self._border_color_b.get():02x}"),
            title="Border Color"
        )
        if c[0]:
            self._border_color_r.set(int(c[0][0]))
            self._border_color_g.set(int(c[0][1]))
            self._border_color_b.set(int(c[0][2]))

    def _pick_font_color(self):
        c = colorchooser.askcolor(
            color=(f"#{self._font_color_r.get():02x}{self._font_color_g.get():02x}{self._font_color_b.get():02x}"),
            title="Font Color"
        )
        if c[0]:
            self._font_color_r.set(int(c[0][0]))
            self._font_color_g.set(int(c[0][1]))
            self._font_color_b.set(int(c[0][2]))

    def _on_fixed_ratio_toggle(self):
        self._update_fixed_ratio_inputs()

    def _on_fixed_ratio_auto_changed(self):
        self._update_fixed_ratio_inputs()

    def _update_fixed_ratio_inputs(self):
        auto = self._fr_auto_var.get()
        for key in ("a", "b", "c"):
            w = self._fr_vars.get(key + "_widget")
            if w:
                w.configure(state="disabled" if key == auto else "normal")

    def _reset_config(self):
        if messagebox.askyesno("Reset Config", "Reset all settings to defaults?"):
            self._config.reset()
            self._load_config_to_ui()

    def _get_images_to_process(self):
        """Get list of images based on current UI state."""
        selected = self._image_listbox.curselection()
        if selected:
            return [self._image_files[i] for i in selected]
        return list(self._image_files)

    def _on_process(self):
        self._sync_ui_to_config()

        images = self._get_images_to_process()
        if not images:
            messagebox.showwarning("No Images", "Please load or select images to process.")
            return

        # Show preview dialog for per-image text editing
        dialog = PreviewDialog(self._root, images, self._config)
        if dialog.result is None:
            self._progress_var.set("Cancelled")
            return

        per_image_lines = dialog.result

        self._progress_bar["maximum"] = len(images)
        self._progress_bar["value"] = 0
        self._progress_var.set(f"Processing 0/{len(images)}...")

        def run():
            for i, path in enumerate(images):
                try:
                    lines = per_image_lines.get(path)
                    process_image(path, self._config, text_lines=lines)
                except Exception as e:
                    self._root.after(0, lambda e=e, p=path: self._progress_var.set(f"Failed: {os.path.basename(p)} - {e}"))
                self._root.after(0, lambda i=i: self._update_progress(i + 1, len(images)))
            self._root.after(0, lambda: self._progress_var.set(f"Done: {len(images)} image(s) processed"))

        threading.Thread(target=run, daemon=True).start()

    def _update_progress(self, current, total):
        self._progress_bar["value"] = current
        self._progress_var.set(f"Processing {current}/{total}...")


def main():
    gui = PyBorderEXIFGUI()
    gui.run()


if __name__ == "__main__":
    main()
