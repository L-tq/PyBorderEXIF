"""Core image processing: load, border, EXIF text rendering, and save."""

import os
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .exif_reader import extract_exif, exif_to_display_lines, get_field_label
from .logo import place_logos


def load_image(image_path):
    """
    Load an image file. Handles JPEG and RAW formats.
    RAW files are developed to RGB using rawpy.
    Returns a PIL Image in RGB mode.
    """
    ext = image_path.lower().rsplit(".", 1)[-1] if "." in image_path else ""

    raw_extensions = {"arw", "nef", "cr2", "cr3", "dng", "rw2", "orf", "raf", "pef", "srf", "raw"}

    if ext in raw_extensions:
        try:
            import rawpy
            import numpy as np
            with rawpy.imread(image_path) as raw:
                rgb = raw.postprocess()
            return Image.fromarray(rgb)
        except ImportError:
            raise RuntimeError("rawpy is required to process RAW files. Install with: pip install rawpy")
        except Exception as e:
            raise RuntimeError(f"Failed to process RAW file {image_path}: {e}")
    else:
        img = Image.open(image_path)
        # Handle orientation for JPEG
        img = ImageOps.exif_transpose(img)
        if img.mode == "RGBA":
            # Composite onto white background
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        return img


def add_border(image, border_pixels, color=(255, 255, 255)):
    """
    Add a border around an image.

    Args:
        image: PIL Image
        border_pixels: dict with top, bottom, left, right pixel values
        color: RGB tuple for border color

    Returns:
        PIL Image with border added
    """
    top = border_pixels.get("top", 0)
    bottom = border_pixels.get("bottom", 0)
    left = border_pixels.get("left", 0)
    right = border_pixels.get("right", 0)

    new_width = image.width + left + right
    new_height = image.height + top + bottom

    # Create new canvas
    bordered = Image.new("RGB", (new_width, new_height), tuple(color))
    bordered.paste(image, (left, top))

    return bordered


def _load_font(size):
    """Load a font at the given size. Falls back to default."""
    try:
        font_paths = [
            # English fonts
            "C:\\Windows\\Fonts\\roboto.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
            "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
            "/System/Library/Fonts/Roboto.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            # Chinese fonts - 思源黑体 (Source Han Sans / Noto Sans CJK)
            "C:\\Windows\\Fonts\\notosanscjk.ttc",
            "C:\\Windows\\Fonts\\msyh.ttc",
            "C:\\Windows\\Fonts\\msyhbd.ttc",
            "/System/Library/Fonts/NotoSansCJK-Regular.ttc",
            "/System/Library/Fonts/NotoSansCJK.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "C:\\Windows\\Fonts\\simsun.ttc",
            "C:\\Windows\\Fonts\\simhei.ttf",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                return ImageFont.truetype(fp, size)
    except Exception:
        pass
    return ImageFont.load_default()


def _get_text_position(image_size, border_pixels, text_bbox, position, alignment, margin):
    """
    Calculate x, y position for rendering text on the border.

    Args:
        image_size: (width, height) of the full bordered image
        border_pixels: dict of top, bottom, left, right
        text_bbox: (width, height) of the text block
        position: "top", "bottom", "left", "right"
        alignment: "left", "center", "right" (for top/bottom) or "top", "center", "bottom" (for left/right)
        margin: pixel margin from edge
    """
    img_w, img_h = image_size
    tw, th = text_bbox
    top = border_pixels.get("top", 0)
    bottom = border_pixels.get("bottom", 0)
    left = border_pixels.get("left", 0)
    right = border_pixels.get("right", 0)

    if position == "bottom":
        y = img_h - bottom + margin
        if alignment == "center":
            x = (img_w - tw) // 2
        elif alignment == "right":
            x = img_w - right - margin - tw
        else:
            x = left + margin
        return x, y

    elif position == "top":
        y = margin
        if alignment == "center":
            x = (img_w - tw) // 2
        elif alignment == "right":
            x = img_w - right - margin - tw
        else:
            x = left + margin
        return x, y

    elif position == "left":
        x = margin
        if alignment == "center":
            y = (img_h - th) // 2
        elif alignment == "bottom":
            y = img_h - bottom - margin - th
        else:
            y = top + margin
        return x, y

    elif position == "right":
        x = img_w - right - tw - margin
        if alignment == "center":
            y = (img_h - th) // 2
        elif alignment == "bottom":
            y = img_h - bottom - margin - th
        else:
            y = top + margin
        return x, y

    # Default fallback
    return left + margin, img_h - bottom + margin


def _render_text_block(image, lines, font, font_color, border_pixels, position, alignment, margin, line_spacing):
    """
    Render a block of text onto the image border area.

    Returns the modified image.
    """
    draw = ImageDraw.Draw(image)

    # Measure total text block size
    line_heights = []
    total_height = 0
    max_width = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        line_heights.append(lh)
        max_width = max(max_width, lw)
        total_height += lh + line_spacing

    if lines:
        total_height -= line_spacing  # remove trailing spacing

    # Calculate start position
    x, y = _get_text_position(
        image.size, border_pixels, (max_width, total_height),
        position, alignment, margin
    )

    # Draw each line
    current_y = y
    for i, line in enumerate(lines):
        # Re-calculate x for each line if center/right aligned
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]

        if alignment == "center":
            lx = (image.size[0] - lw) // 2
        elif alignment == "right":
            lx = image.size[0] - border_pixels.get("right", 0) - margin - lw
        else:
            lx = x

        if position == "left" or position == "right":
            lx = x
            if alignment == "center":
                lx = x
            elif alignment == "bottom":
                lx = x

        draw.text((lx, current_y), line, font=font, fill=tuple(font_color))
        current_y += line_heights[i] + line_spacing

    return image


def _position_alignment_vertical(position, alignment):
    """For left/right positions, alignment becomes top/center/bottom."""
    if position in ("left", "right"):
        if alignment in ("left", "right"):
            return {
                "left": "top",
                "center": "center",
                "right": "bottom",
            }.get(alignment, "center")
    return alignment


def add_exif_text(image, exif_data, exif_config):
    """
    Render EXIF metadata text on the image border.

    Args:
        image: PIL Image with border already added
        exif_data: dict from extract_exif()
        exif_config: dict with fields, font_size, font_color, position, alignment, margin, line_spacing

    Returns:
        PIL Image with text rendered
    """
    if not exif_config.get("enabled", True):
        return image

    fields = exif_config.get("fields", [])
    font_size = exif_config.get("font_size", 24)
    font_color = exif_config.get("font_color", [0, 0, 0])
    position = exif_config.get("position", "bottom")
    alignment = exif_config.get("alignment", "left")
    margin = exif_config.get("margin", 10)
    line_spacing = exif_config.get("line_spacing", 4)

    author_name = exif_config.get("author_name", "")

    lines = exif_to_display_lines(exif_data, fields, author_name)
    if not lines:
        return image

    font = _load_font(font_size)
    vert_align = _position_alignment_vertical(position, alignment)

    # We need border pixel info for positioning. Infer from image dimensions
    # vs original - but we don't have original here. The calling code must pass
    # border config separately. We'll use a dummy (0 border) which means text
    # renders at the very edge. This is called from process_image which has
    # the border info.

    return image


def render_text_on_border(image, lines, font_size, font_color, border_pixels,
                          position, alignment, margin, line_spacing):
    """Render text lines on the border area of an already-bordered image."""
    if not lines:
        return image

    font = _load_font(font_size)
    vert_align = _position_alignment_vertical(position, alignment)

    return _render_text_block(
        image, lines, font, font_color, border_pixels,
        position, vert_align, margin, line_spacing
    )


def process_image(image_path, config, output_path=None):
    """
    Full image processing pipeline.

    Args:
        image_path: Path to source image
        config: Config object
        output_path: Optional output path. If None, generates from input name.

    Returns:
        Path to saved output image
    """
    # 1. Load
    img = load_image(image_path)

    # 2. Extract EXIF (do this before adding border in case RAW processing loses it)
    exif_data = {}
    exif_cfg = config.exif
    if exif_cfg.get("enabled", True):
        exif_data = extract_exif(image_path)

    # 3. Add border
    border_px = config.get_border_pixels()
    border_color = tuple(config.border.get("color", [255, 255, 255]))
    img = add_border(img, border_px, border_color)

    # 4. Add EXIF text
    if exif_cfg.get("enabled", True):
        fields = exif_cfg.get("fields", [])
        font_size = exif_cfg.get("font_size", 24)
        font_color = exif_cfg.get("font_color", [0, 0, 0])
        position = exif_cfg.get("position", "bottom")
        alignment = exif_cfg.get("alignment", "left")
        margin = exif_cfg.get("margin", 10)
        line_spacing = exif_cfg.get("line_spacing", 4)
        author = config.author_name

        lines = exif_to_display_lines(exif_data, fields, author)
        img = render_text_on_border(
            img, lines, font_size, font_color, border_px,
            position, alignment, margin, line_spacing
        )

    # 5. Add logos
    logos = config.logos
    if logos:
        img = place_logos(img, logos, border_px)

    # 6. Save
    if output_path is None:
        base, ext = os.path.splitext(os.path.basename(image_path))
        suffix = config.output.get("suffix", "_bordered")
        fmt = config.output.get("format", "JPEG")
        if fmt.upper() == "JPEG":
            ext = ".jpg"
        else:
            ext = ".png" if fmt.upper() == "PNG" else f".{fmt.lower()}"
        out_dir = config.output_dir or os.path.dirname(image_path) or "."
        output_path = os.path.join(out_dir, f"{base}{suffix}{ext}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    save_kwargs = {}
    fmt = config.output.get("format", "JPEG").upper()
    if fmt == "JPEG":
        save_kwargs["quality"] = config.output.get("jpeg_quality", 95)
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, border_color)
            bg.paste(img, mask=img.split()[3] if len(img.split()) > 3 else None)
            img = bg
        img.save(output_path, "JPEG", **save_kwargs)
    elif fmt == "PNG":
        img.save(output_path, "PNG")
    else:
        img.save(output_path, fmt)

    return output_path


def process_images(image_paths, config, progress_callback=None):
    """
    Process multiple images.

    Args:
        image_paths: List of image paths
        config: Config object
        progress_callback: Optional callable(current, total, path)

    Returns:
        List of output paths
    """
    results = []
    total = len(image_paths)
    for i, path in enumerate(image_paths):
        try:
            out = process_image(path, config)
            results.append((path, out, None))
        except Exception as e:
            results.append((path, None, str(e)))
        if progress_callback:
            progress_callback(i + 1, total, path)
    return results


def get_supported_images_from_dir(directory):
    """Get all supported image files from a directory (non-recursive)."""
    supported = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp",
                 ".arw", ".nef", ".cr2", ".cr3", ".dng", ".rw2", ".orf",
                 ".raf", ".pef", ".srf", ".raw"}
    files = []
    for f in sorted(os.listdir(directory)):
        ext = os.path.splitext(f)[1].lower()
        if ext in supported:
            files.append(os.path.join(directory, f))
    return files
