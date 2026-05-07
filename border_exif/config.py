"""Configuration management with persistent last-used values."""

import os
import yaml

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")

BORDER_PRESETS = {
    "small": {"top": 20, "bottom": 20, "left": 20, "right": 20},
    "medium": {"top": 50, "bottom": 50, "left": 50, "right": 50},
    "large": {"top": 100, "bottom": 100, "left": 100, "right": 100},
    "polaroid": {"top": 30, "bottom": 100, "left": 30, "right": 30},
}

DEFAULT_METADATA_FIELDS = [
    "camera_model",
    "lens_model",
    "focal_length_35mm",
    "aperture",
    "iso",
    "shutter_speed"
]

DEFAULT_FONT_FAMILY = "Roboto Regular"

FONT_FAMILIES = {
    "Roboto Regular": ["Roboto-Regular.ttf"],
    "Roboto Italic": ["Roboto-Italic.ttf"],
    "Roboto Bold": ["Roboto-Bold.ttf"],
    "Roboto Bold Italic": ["Roboto-BoldItalic.ttf"],
    "Roboto Thin": ["Roboto-Thin.ttf"],
    "Roboto Thin Italic": ["Roboto-ThinItalic.ttf"],
    "Roboto Light": ["Roboto-Light.ttf"],
    "Roboto Light Italic": ["Roboto-LightItalic.ttf"],
    "Roboto Medium": ["Roboto-Medium.ttf"],
    "Roboto Medium Italic": ["Roboto-MediumItalic.ttf"],
    "思源黑体 Regular": ["NotoSansCJK-Regular.ttc", "SourceHanSansSC-Regular.otf"],
    "思源黑体 Bold": ["NotoSansCJK-Bold.ttc", "SourceHanSansSC-Bold.otf"],
}

FONT_SEARCH_PATHS = [
    "/usr/share/fonts/truetype/roboto",
    "/usr/share/fonts/truetype",
    "/usr/share/fonts/opentype",
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    os.path.expanduser("~/.fonts"),
    "C:\\Windows\\Fonts",
    "/System/Library/Fonts",
]

BREAK_MARKER = "__break__"


def find_font_file(font_family):
    """Find the font file path for a given font family name."""
    candidates = FONT_FAMILIES.get(font_family, [])
    for filename in candidates:
        for search_path in FONT_SEARCH_PATHS:
            if not os.path.isdir(search_path):
                continue
            for root, dirs, files in os.walk(search_path):
                for f in files:
                    if f.lower() == filename.lower():
                        return os.path.join(root, f)
    return None

DEFAULT_CONFIG = {
    "input_dir": os.path.expanduser("~/Pictures"),
    "output_dir": os.path.expanduser("~/Pictures/bordered"),
    "logo_dir": "",
    "author_name": "",
    "border": {
        "preset": "medium",
        "custom": {"top": 0, "bottom": 0, "left": 0, "right": 0},
        "color": [255, 255, 255],
        "use_custom": False,
        "use_fixed_ratio": False,
        "fixed_ratio": {"a": 50, "b": 50, "c": 50, "auto_param": "c"},
    },
    "exif": {
        "enabled": True,
        "fields": DEFAULT_METADATA_FIELDS[:],
        "font_size": 24,
        "font_color": [0, 0, 0],
        "font_family": DEFAULT_FONT_FAMILY,
        "field_layout": None,
        "position": "bottom",
        "alignment": "left",
        "margin": 10,
        "line_spacing": 4,
    },
    "logos": [
        {"enabled": False, "path": "", "position": "bottom-left", "scale": 0.5, "offset_x": 0, "offset_y": 0},
        {"enabled": False, "path": "", "position": "bottom-right", "scale": 0.5, "offset_x": 0, "offset_y": 0},
        {"enabled": False, "path": "", "position": "top-left", "scale": 0.5, "offset_x": 0, "offset_y": 0},
        {"enabled": False, "path": "", "position": "top-right", "scale": 0.5, "offset_x": 0, "offset_y": 0},
    ],
    "output": {
        "format": "JPEG",
        "jpeg_quality": 95,
        "suffix": "_bordered",
    },
}


def _deep_merge(default, override):
    """Recursively merge override into default dict."""
    result = dict(default)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _save_config(data, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def _load_config(path=None):
    path = path or DEFAULT_CONFIG_PATH
    if os.path.exists(path):
        data = None
        for encoding in ("utf-8", "gbk", "gb18030"):
            try:
                with open(path, "r", encoding=encoding) as f:
                    data = yaml.safe_load(f)
                if encoding != "utf-8":
                    _save_config(data, path)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if data:
            return _deep_merge(DEFAULT_CONFIG, data)
    return dict(DEFAULT_CONFIG)


class Config:
    """Configuration manager with auto-save for last-used values."""

    def __init__(self, path=None):
        self._path = path or DEFAULT_CONFIG_PATH
        self._data = _load_config(self._path)
        self._ensure_dir_exists()

    def _ensure_dir_exists(self):
        d = os.path.dirname(self._path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    def save(self):
        _save_config(self._data, self._path)

    # --- Convenience accessors ---

    @property
    def input_dir(self):
        return self._data.get("input_dir", "")

    @input_dir.setter
    def input_dir(self, value):
        self._data["input_dir"] = value
        self.save()

    @property
    def output_dir(self):
        return self._data.get("output_dir", "")

    @output_dir.setter
    def output_dir(self, value):
        self._data["output_dir"] = value
        self.save()

    @property
    def logo_dir(self):
        return self._data.get("logo_dir", "")

    @logo_dir.setter
    def logo_dir(self, value):
        self._data["logo_dir"] = value
        self.save()

    @property
    def author_name(self):
        return self._data.get("author_name", "")

    @author_name.setter
    def author_name(self, value):
        self._data["author_name"] = value
        self.save()

    @property
    def border(self):
        return self._data.get("border", {})

    @border.setter
    def border(self, value):
        self._data["border"] = value
        self.save()

    @property
    def exif(self):
        return self._data.get("exif", {})

    @exif.setter
    def exif(self, value):
        self._data["exif"] = value
        self.save()

    @property
    def logos(self):
        return self._data.get("logos", [])

    @logos.setter
    def logos(self, value):
        self._data["logos"] = value
        self.save()

    @property
    def output(self):
        return self._data.get("output", {})

    @output.setter
    def output(self, value):
        self._data["output"] = value
        self.save()

    def get_border_pixels(self, img_width=None, img_height=None):
        """Return {top, bottom, left, right} pixel values for the current border config.

        If use_fixed_ratio is True, img_width and img_height are required to
        compute the auto-calculated parameter from the aspect-ratio constraint:
            2*a*H = W*(b+c)   where a=left=right, b=top, c=bottom
        """
        b = self.border
        if b.get("use_fixed_ratio"):
            return self._compute_fixed_ratio_border(img_width, img_height)
        if b.get("use_custom"):
            return dict(b["custom"])
        preset_name = b.get("preset", "medium")
        return dict(BORDER_PRESETS.get(preset_name, BORDER_PRESETS["medium"]))

    def _compute_fixed_ratio_border(self, W, H):
        """Compute border pixels from the fixed-ratio constraint 2*a*H = W*(b+c)."""
        fr = self.border.get("fixed_ratio", {})
        a = fr.get("a", 0)
        b = fr.get("b", 0)
        c_val = fr.get("c", 0)
        auto = fr.get("auto_param", "c")

        if W is None or H is None or W <= 0 or H <= 0:
            return {"top": b, "bottom": c_val, "left": a, "right": a}

        if auto == "a":
            a = max(0, int(W * (b + c_val) / (2 * H)))
        elif auto == "b":
            b = max(0, int(2 * a * H / W - c_val))
        else:  # auto == "c"
            c_val = max(0, int(2 * a * H / W - b))

        return {"top": b, "bottom": c_val, "left": a, "right": a}

    def get_all(self):
        return dict(self._data)

    def update(self, data):
        self._data = _deep_merge(self._data, data)
        self.save()

    def reset(self):
        self._data = dict(DEFAULT_CONFIG)
        self.save()
