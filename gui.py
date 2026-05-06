#!/usr/bin/env python3
"""GUI (Graphical User Interface) for PyBorderEXIF using tkinter."""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

from border_exif.config import Config, BORDER_PRESETS, DEFAULT_METADATA_FIELDS
from border_exif.core import process_image, process_images, get_supported_images_from_dir
from border_exif.exif_reader import get_all_field_names, get_field_label


class PyBorderEXIFGUI:
    """Main GUI application window."""

    def __init__(self):
        self._config = Config()
        self._image_files = []
        self._field_vars = {}

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

        ttk.Label(border_frame, text="Border Color:").grid(row=row + 3, column=0, sticky=tk.W, padx=5, pady=5)
        color_frame = ttk.Frame(border_frame)
        color_frame.grid(row=row + 4, column=0, sticky=tk.W, padx=20)
        self._border_color_r = tk.IntVar(value=255)
        self._border_color_g = tk.IntVar(value=255)
        self._border_color_b = tk.IntVar(value=255)
        for i, (label, var) in enumerate([("R", self._border_color_r), ("G", self._border_color_g), ("B", self._border_color_b)]):
            ttk.Label(color_frame, text=label).grid(row=0, column=i * 2, padx=2)
            ttk.Spinbox(color_frame, from_=0, to=255, textvariable=var, width=5).grid(row=1, column=i * 2, padx=2)
        ttk.Button(border_frame, text="Pick Color...", command=self._pick_border_color).grid(row=row + 5, column=0, sticky=tk.W, padx=20, pady=5)

        # --- EXIF Tab ---
        exif_frame = ttk.Frame(notebook)
        notebook.add(exif_frame, text="EXIF")

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

        ttk.Label(exif_frame, text="Font Color:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        font_color_frame = ttk.Frame(exif_frame)
        font_color_frame.grid(row=4, column=1, sticky=tk.W, padx=5)
        self._font_color_r = tk.IntVar(value=0)
        self._font_color_g = tk.IntVar(value=0)
        self._font_color_b = tk.IntVar(value=0)
        for i, (label, var) in enumerate([("R", self._font_color_r), ("G", self._font_color_g), ("B", self._font_color_b)]):
            ttk.Label(font_color_frame, text=label).grid(row=0, column=i * 2, padx=2)
            ttk.Spinbox(font_color_frame, from_=0, to=255, textvariable=var, width=5).grid(row=1, column=i * 2, padx=2)
        ttk.Button(font_color_frame, text="Pick...", command=self._pick_font_color).grid(row=1, column=6, padx=5)

        ttk.Label(exif_frame, text="EXIF Fields:", font=("", 10, "bold")).grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(10, 5))

        fields_container = ttk.Frame(exif_frame)
        fields_container.grid(row=6, column=0, columnspan=2, sticky=tk.NSEW, padx=10)
        exif_frame.rowconfigure(6, weight=1)

        canvas = tk.Canvas(fields_container, height=180)
        scrollbar = ttk.Scrollbar(fields_container, orient=tk.VERTICAL, command=canvas.yview)
        self._fields_inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self._fields_inner, anchor=tk.NW)
        canvas.config(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._fields_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Populate field checkboxes
        all_fields = get_all_field_names()
        for i, field_id in enumerate(all_fields):
            var = tk.BooleanVar(value=field_id in DEFAULT_METADATA_FIELDS)
            self._field_vars[field_id] = var
            ttk.Checkbutton(self._fields_inner, text=get_field_label(field_id), variable=var).grid(
                row=i // 3, column=i % 3, sticky=tk.W, padx=5, pady=2)

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

        exif = self._config.exif
        self._text_pos_var.set(exif.get("position", "bottom"))
        self._text_align_var.set(exif.get("alignment", "left"))
        self._font_size_var.set(exif.get("font_size", 24))
        fc = exif.get("font_color", [0, 0, 0])
        self._font_color_r.set(fc[0])
        self._font_color_g.set(fc[1])
        self._font_color_b.set(fc[2])

        enabled_fields = exif.get("fields", DEFAULT_METADATA_FIELDS)
        for field_id, var in self._field_vars.items():
            var.set(field_id in enabled_fields)

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
        self._config.border = border

        exif = self._config.exif
        exif["position"] = self._text_pos_var.get()
        exif["alignment"] = self._text_align_var.get()
        exif["font_size"] = self._font_size_var.get()
        exif["font_color"] = [self._font_color_r.get(), self._font_color_g.get(), self._font_color_b.get()]
        exif["fields"] = [k for k, v in self._field_vars.items() if v.get()]
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
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All Files", "*.*")]
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

        self._progress_bar["maximum"] = len(images)
        self._progress_bar["value"] = 0
        self._progress_var.set(f"Processing 0/{len(images)}...")

        def run():
            for i, path in enumerate(images):
                try:
                    process_image(path, self._config)
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
