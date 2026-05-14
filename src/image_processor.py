"""Image processor - renders borders, logos, and text onto images."""

import io
import math
import os
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageOps

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'fonts')

FONT_FAMILY_MAP = {
    'Roboto': {
        'normal': 'Roboto-Regular.ttf',
        'bold': 'Roboto-Bold.ttf',
        'italic': 'Roboto-Italic.ttf',
        'bold italic': 'Roboto-BoldItalic.ttf',
        'thin': 'Roboto-Thin.ttf',
        'thin italic': 'Roboto-ThinItalic.ttf',
        'light': 'Roboto-Light.ttf',
        'light italic': 'Roboto-LightItalic.ttf',
        'medium': 'Roboto-Medium.ttf',
        'medium italic': 'Roboto-MediumItalic.ttf',
    },
    'Source Han Sans': {
        'normal': 'NotoSansSC-Regular.ttf',
        'bold': 'NotoSansSC-Bold.ttf',
        'italic': 'NotoSansSC-Regular.ttf',
        'bold italic': 'NotoSansSC-Bold.ttf',
    },
}

# System font fallbacks: (font_file, family, weight_str, ttc_index)
# Noto Sans CJK is tried FIRST because it covers Latin + CJK. DejaVu is good
# for Latin but lacks CJK glyphs, so CJK text would render as tofu.
_SYSTEM_FONT_FALLBACKS = [
    # Noto Sans CJK — best all-around fallback (covers Latin + CJK). Index 3 = SC.
    ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'Roboto', 'normal', 3),
    ('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 'Roboto', 'bold', 3),
    ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'Roboto', 'thin', 3),
    ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'Roboto', 'light', 3),
    ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'Roboto', 'medium', 3),
    # DejaVu Sans (good Latin coverage)
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'Roboto', 'normal', 0),
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'Roboto', 'bold', 0),
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf', 'Roboto', 'italic', 0),
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf', 'Roboto', 'bold italic', 0),
    # Liberation Sans
    ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', 'Roboto', 'normal', 0),
    ('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', 'Roboto', 'bold', 0),
    ('/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf', 'Roboto', 'italic', 0),
    ('/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf', 'Roboto', 'bold italic', 0),
    # Noto Sans CJK for Source Han Sans family
    ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'Source Han Sans', 'normal', 3),
    ('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 'Source Han Sans', 'bold', 3),
]


def _get_font_path(family, weight, style):
    """Resolve font file path and TTC index. Returns (path, ttc_index) or (None, 0)."""
    family_key = family
    if family not in FONT_FAMILY_MAP:
        family_key = 'Roboto'

    variant_map = FONT_FAMILY_MAP[family_key]
    style_key = 'normal'
    if weight == 'bold' and style == 'italic':
        style_key = 'bold italic'
    elif weight == 'bold':
        style_key = 'bold'
    elif style == 'italic':
        style_key = 'italic'
    elif weight == 'thin' and style == 'italic':
        style_key = 'thin italic'
    elif weight == 'thin':
        style_key = 'thin'
    elif weight == 'light' and style == 'italic':
        style_key = 'light italic'
    elif weight == 'light':
        style_key = 'light'
    elif weight == 'medium' and style == 'italic':
        style_key = 'medium italic'
    elif weight == 'medium':
        style_key = 'medium'

    filename = variant_map.get(style_key, variant_map.get('normal', 'Roboto-Regular.ttf'))
    font_path = os.path.join(FONTS_DIR, filename)

    if os.path.exists(font_path):
        return font_path, 0

    # Fall back to system fonts: try exact family + weight match first
    for sys_path, sys_family, sys_weight, ttc_idx in _SYSTEM_FONT_FALLBACKS:
        if sys_family == family_key and sys_weight == style_key and os.path.exists(sys_path):
            return sys_path, ttc_idx

    # Broader fallback: any font matching the family
    for sys_path, sys_family, _, ttc_idx in _SYSTEM_FONT_FALLBACKS:
        if sys_family == family_key and os.path.exists(sys_path):
            return sys_path, ttc_idx

    # Ultimate fallback: any available system font (CJK fonts are listed first)
    for sys_path, _, _, ttc_idx in _SYSTEM_FONT_FALLBACKS:
        if os.path.exists(sys_path):
            return sys_path, ttc_idx

    return None, 0


def _load_font(family, size, weight='normal', style='normal'):
    """Load a font with the specified parameters."""
    font_path, ttc_index = _get_font_path(family, weight, style)
    if font_path:
        try:
            return ImageFont.truetype(font_path, int(size), index=ttc_index)
        except Exception:
            pass
    # Ultimate fallback
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def _hex_to_rgb(hex_color):
    """Convert hex color string to RGB tuple."""
    try:
        return ImageColor.getrgb(hex_color)
    except Exception:
        return (255, 255, 255)


def _is_cjk(ch):
    """Check if a character is in a CJK Unicode block."""
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF or    # CJK Unified Ideographs
            0x3400 <= cp <= 0x4DBF or    # CJK Unified Ideographs Extension A
            0x20000 <= cp <= 0x2A6DF or  # CJK Unified Ideographs Extension B
            0xF900 <= cp <= 0xFAFF or    # CJK Compatibility Ideographs
            0x3040 <= cp <= 0x309F or    # Hiragana
            0x30A0 <= cp <= 0x30FF or    # Katakana
            0xAC00 <= cp <= 0xD7AF)      # Hangul Syllables


def _text_width(text, font):
    """Measure text width in pixels."""
    if not text:
        return 0
    try:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]
    except Exception:
        return font.getsize(text)[0]


def _wrap_text_lines(text, font, max_width):
    """Wrap text to fit within max_width. Handles both Latin (word-wrap)
    and CJK (character-wrap) scripts.

    NOTE: For single-line parts (left/center/right), pass max_width=None to disable wrapping."""
    if not text:
        return []
    # If max_width is None, don't wrap - return all text as single line
    if max_width is None:
        return [text]
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append('')
            continue
        words = paragraph.split(' ')
        current_line = words[0]
        for word in words[1:]:
            test_line = current_line + ' ' + word
            if _text_width(test_line, font) <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)

    # Second pass: if any line is still too wide (e.g., CJK without spaces),
    # break it character by character
    result = []
    for line in lines:
        if _text_width(line, font) <= max_width:
            result.append(line)
            continue
        # Character-level wrapping for lines without word breaks
        char_line = ''
        for ch in line:
            test = char_line + ch
            if _text_width(test, font) <= max_width:
                char_line = test
            else:
                if char_line:
                    result.append(char_line)
                char_line = ch
        if char_line:
            result.append(char_line)
    return result


def process_image(image_path, border_config, logos_config, text_lines,
                  global_text_config, exif_data, output_path=None):
    """
    Render the full image with borders, logos, and text.

    Args:
        image_path: Path to input image
        border_config: dict with border dimensions & color
        logos_config: list of logo dicts (path, offset_x, offset_y, width, height)
        text_lines: list of text line dicts (left, center, right, font settings)
        global_text_config: dict with line_spacing, margins
        exif_data: dict of EXIF tag values
        output_path: If provided, save to this path

    Returns:
        PIL.Image object
    """
    # Open original image
    if image_path.lower().endswith('.arw'):
        import rawpy
        with rawpy.imread(image_path) as raw:
            rgb = raw.postprocess()
            original = Image.fromarray(rgb)
    else:
        original = ImageOps.exif_transpose(Image.open(image_path))
        if original.mode != 'RGB':
            original = original.convert('RGB')

    img_w, img_h = original.size

    # Calculate border
    b = border_config
    border = {
        'top': int(b.get('top', 0)),
        'bottom': int(b.get('bottom', 0)),
        'left': int(b.get('left', 0)),
        'right': int(b.get('right', 0)),
    }

    final_w = img_w + border['left'] + border['right']
    final_h = img_h + border['top'] + border['bottom']

    # Create canvas
    border_color = _hex_to_rgb(b.get('color', '#FFFFFF'))
    canvas = Image.new('RGB', (final_w, final_h), border_color)

    # Paste original image
    canvas.paste(original, (border['left'], border['top']))

    # Draw logos
    for logo_cfg in logos_config:
        _draw_logo(canvas, logo_cfg, border)

    # Draw text in bottom border area
    _draw_text_overlays(canvas, img_w, img_h, border, text_lines,
                        global_text_config, exif_data)

    if output_path:
        canvas.save(output_path, quality=95)

    return canvas


def _draw_logo(canvas, logo_cfg, border):
    """Draw a single logo onto the canvas."""
    logo_path = logo_cfg.get('path', '')
    if not logo_path or not os.path.exists(logo_path):
        return

    try:
        if logo_path.lower().endswith('.svg'):
            try:
                import cairosvg
                png_data = cairosvg.svg2png(
                    url=logo_path,
                    output_width=int(logo_cfg.get('width', 200)),
                    output_height=int(logo_cfg.get('height', 200)),
                )
                logo_img = Image.open(io.BytesIO(png_data))
            except Exception:
                return
        else:
            logo_img = Image.open(logo_path)

        if logo_img.mode == 'RGBA':
            pass  # Keep alpha
        elif logo_img.mode != 'RGB':
            logo_img = logo_img.convert('RGBA')

        # Scale logo
        target_w = int(logo_cfg.get('width', logo_img.width))
        target_h = int(logo_cfg.get('height', logo_img.height))
        if (target_w, target_h) != (logo_img.width, logo_img.height):
            logo_img = logo_img.resize((target_w, target_h), Image.LANCZOS)

        # Calculate position — offset_x/offset_y from bottom-left of canvas
        # to bottom-left of logo
        offset_x = int(logo_cfg.get('offset_x', 0))
        offset_y = int(logo_cfg.get('offset_y', 0))

        pos_x = offset_x
        pos_y = canvas.height - offset_y - logo_img.height

        # Paste with alpha
        if logo_img.mode == 'RGBA':
            canvas.paste(logo_img, (pos_x, pos_y), logo_img)
        else:
            canvas.paste(logo_img, (pos_x, pos_y))

    except Exception as e:
        # Silently skip failed logos
        pass


def _get_line_height(font, line_spacing):
    """Get line height for a font."""
    try:
        bbox = font.getbbox('Ag')
        return (bbox[3] - bbox[1]) * line_spacing
    except Exception:
        return font.size * 1.2 * line_spacing


# Mapping from user-friendly placeholder names to exif_data keys
_PLACEHOLDER_MAP = {
    'Camera Make': 'camera_make',
    'Camera Model': 'camera_model',
    'Lens Make': 'lens_make',
    'Lens Model': 'lens_model',
    'Focal Length': 'focal_length',
    'Aperture': 'aperture',
    'ISO': 'iso',
    'Exposure Time': 'exposure_time',
    'F-Number': 'fnumber',
    'Date/Time': 'datetime',
    'Artist': 'artist',
    'Software': 'software',
    'GPS': 'gps',
}


def _resolve_placeholders(text, exif_data):
    """Replace {Tag Name} placeholders with actual EXIF values."""
    if not text:
        return ''
    result = text
    all_tags = exif_data.get('all_tags', {})

    # Find all {placeholders}
    import re
    def replace_tag(match):
        tag_name = match.group(1).strip()
        # Check simplified fields first
        if tag_name in _PLACEHOLDER_MAP:
            val = exif_data.get(_PLACEHOLDER_MAP[tag_name], '')
            if val:
                return str(val)
        # Check all_tags
        if tag_name in all_tags:
            return str(all_tags[tag_name])
        # Try case-insensitive match in all_tags
        for k, v in all_tags.items():
            if k.lower() == tag_name.lower():
                return str(v)
        return match.group(0)  # Keep placeholder if not found

    result = re.sub(r'\{([^}]+)\}', replace_tag, result)
    return result


def _resolve_part_font(part, exif_data):
    """Resolve text, font, and color from a part config.

    A part can be a plain string (old format) or a dict with font settings
    (new format).
    """
    if isinstance(part, dict):
        text = part.get('text', '')
        font_family = part.get('font_family', 'Roboto')
        font_size = int(part.get('font_size', 22))
        font_weight = part.get('font_weight', 'normal')
        font_style = part.get('font_style', 'normal')
        font_color = part.get('font_color', '#333333')
    else:
        text = str(part) if part else ''
        font_family = 'Roboto'
        font_size = 22
        font_weight = 'normal'
        font_style = 'normal'
        font_color = '#333333'

    text = _resolve_placeholders(text, exif_data)
    font = _load_font(font_family, font_size, font_weight, font_style)
    color = _hex_to_rgb(font_color)
    return text, font, color


def _draw_text_overlays(canvas, img_w, img_h, border, text_lines,
                        global_config, exif_data):
    """Draw text lines with left/center/right alignment in the bottom border area.

    Each part (left/center/right) can have its own font family, size, weight,
    style, and color. Old-style string parts fall back to defaults.
    """
    bottom_h = border['bottom']
    if bottom_h <= 0 or not text_lines:
        return

    left_margin = int(global_config.get('text_margin_left', 40))
    right_margin = int(global_config.get('text_margin_right', 40))
    bottom_margin = int(global_config.get('text_margin_bottom', 30))
    line_spacing = float(global_config.get('line_spacing', 1.3))
    lines_gap = int(global_config.get('text_lines_spacing', 8))

    center_x = canvas.width / 2
    available_w = canvas.width - left_margin - right_margin
    part_w = int(available_w * 0.42)

    draw = ImageDraw.Draw(canvas)

    # First pass: resolve text, wrap, and calculate total height
    line_layouts = []
    total_h = 0

    for line_cfg in text_lines:
        left_text, left_font, left_color = _resolve_part_font(
            line_cfg.get('left', ''), exif_data)
        center_text, center_font, center_color = _resolve_part_font(
            line_cfg.get('center', ''), exif_data)
        right_text, right_font, right_color = _resolve_part_font(
            line_cfg.get('right', ''), exif_data)

        # Each part - no wrapping, allow overlay on other parts
        left_lines = _wrap_text_lines(left_text, left_font, None)
        center_lines = _wrap_text_lines(center_text, center_font, None)
        right_lines = _wrap_text_lines(right_text, right_font, None)

        # Use the max line height across the three fonts for vertical rhythm
        lh_left = _get_line_height(left_font, line_spacing)
        lh_center = _get_line_height(center_font, line_spacing)
        lh_right = _get_line_height(right_font, line_spacing)
        lh = max(lh_left, lh_center, lh_right)

        max_subs = max(len(left_lines), len(center_lines), len(right_lines), 1)
        line_total_h = max_subs * lh + lines_gap

        line_layouts.append({
            'left_lines': left_lines,
            'left_font': left_font,
            'left_color': left_color,
            'center_lines': center_lines,
            'center_font': center_font,
            'center_color': center_color,
            'right_lines': right_lines,
            'right_font': right_font,
            'right_color': right_color,
            'line_height': lh,
            'total_h': line_total_h,
            'max_subs': max_subs,
        })
        total_h += line_total_h

    if not line_layouts:
        return

    # Remove trailing gap
    total_h -= lines_gap

    # Start Y position (from bottom of border area)
    current_y = canvas.height - bottom_margin - total_h

    for layout in line_layouts:
        for i in range(layout['max_subs']):
            y = current_y + i * layout['line_height']

            # Left-aligned — vertically centered within the line height
            if i < len(layout['left_lines']) and layout['left_lines'][i]:
                y_off = (layout['line_height'] - _get_line_height(layout['left_font'], line_spacing)) / 2
                draw.text((left_margin, y + y_off), layout['left_lines'][i],
                          fill=layout['left_color'], font=layout['left_font'])

            # Center-aligned
            if i < len(layout['center_lines']) and layout['center_lines'][i]:
                y_off = (layout['line_height'] - _get_line_height(layout['center_font'], line_spacing)) / 2
                tw = _text_width(layout['center_lines'][i], layout['center_font'])
                draw.text((center_x - tw / 2, y + y_off), layout['center_lines'][i],
                          fill=layout['center_color'], font=layout['center_font'])

            # Right-aligned
            if i < len(layout['right_lines']) and layout['right_lines'][i]:
                y_off = (layout['line_height'] - _get_line_height(layout['right_font'], line_spacing)) / 2
                tw = _text_width(layout['right_lines'][i], layout['right_font'])
                draw.text((canvas.width - right_margin - tw, y + y_off),
                          layout['right_lines'][i],
                          fill=layout['right_color'], font=layout['right_font'])

        current_y += layout['total_h']


def generate_preview(image_path, border_config, logos_config, text_lines,
                     global_text_config, exif_data, max_dim=1200):
    """Generate a low-resolution preview image."""
    img = process_image(
        image_path, border_config, logos_config, text_lines,
        global_text_config, exif_data
    )
    # Resize for preview
    w, h = img.size
    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    return img
