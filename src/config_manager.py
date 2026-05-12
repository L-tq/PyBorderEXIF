import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')

DEFAULT_CONFIG = {
    'last_input_dir': '',
    'last_output_dir': '',
    'border': {
        'mode': 'custom',
        'top': 100,
        'bottom': 200,
        'left': 80,
        'right': 80,
        'color': '#FFFFFF',
        'auto_param': 'c'
    },
    'logos': [],
    'text_lines': [
        {
            'left': '',
            'center': '',
            'right': '',
            'font_family': 'Roboto',
            'font_size': 28,
            'font_color': '#333333',
            'font_weight': 'bold',
            'font_style': 'normal',
        },
        {
            'left': '{Camera Model}',
            'center': '',
            'right': '{Lens Model}',
            'font_family': 'Roboto',
            'font_size': 20,
            'font_color': '#555555',
            'font_weight': 'normal',
            'font_style': 'normal',
        },
        {
            'left': '',
            'center': '{Focal Length}    {Aperture}    {ISO}    {Exposure Time}',
            'right': '',
            'font_family': 'Roboto',
            'font_size': 18,
            'font_color': '#777777',
            'font_weight': 'normal',
            'font_style': 'normal',
        },
    ],
    'line_spacing': 1.3,
    'text_margin_left': 40,
    'text_margin_right': 40,
    'text_margin_bottom': 30,
    'text_lines_spacing': 8,
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            deep_merge(merged, config)
            _migrate_old_format(merged)
            return merged
        except (json.JSONDecodeError, IOError):
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def deep_merge(base, override):
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value


def _migrate_old_format(config):
    """Convert old text_elements format to new text_lines format."""
    if 'text_elements' in config and config['text_elements']:
        old = config.pop('text_elements')
        old.sort(key=lambda e: e.get('order', 0))
        # Only migrate if text_lines is empty or default
        if not config.get('text_lines') or config['text_lines'] == DEFAULT_CONFIG.get('text_lines'):
            new_lines = []
            for elem in old:
                if not elem.get('visible', True):
                    continue
                value = elem.get('value', '')
                label = elem.get('label', '')
                if not value and label:
                    value = '{' + label + '}'
                new_lines.append({
                    'left': value,
                    'center': '',
                    'right': '',
                    'font_family': elem.get('font_family', 'Roboto'),
                    'font_size': elem.get('font_size', 22),
                    'font_color': elem.get('font_color', '#333333'),
                    'font_weight': elem.get('font_weight', 'normal'),
                    'font_style': elem.get('font_style', 'normal'),
                })
            if new_lines:
                config['text_lines'] = new_lines
