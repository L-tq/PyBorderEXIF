"""Logo placement on bordered images."""

import os
from io import BytesIO
from PIL import Image


def _load_svg_logo(logo_path, max_size):
    """Render an SVG logo to a PIL Image."""
    import cairosvg
    png_bytes = cairosvg.svg2png(url=logo_path, output_width=max_size, output_height=max_size)
    return Image.open(BytesIO(png_bytes)).convert("RGBA")


def _load_logo(logo_path, max_size=None):
    """Load a logo image, preserving transparency."""
    img = Image.open(logo_path)
    if img.mode not in ("RGBA", "RGB"):
        img = img.convert("RGBA")
    if max_size and (img.width > max_size or img.height > max_size):
        ratio = min(max_size / img.width, max_size / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    return img


def _get_logo_position(image_size, border_pixels, logo, position, offset_x, offset_y):
    """
    Calculate the (x, y) paste position for a logo.
    position: "top-left", "top-right", "bottom-left", "bottom-right"
    """
    img_w, img_h = image_size
    top = border_pixels.get("top", 0)
    bottom = border_pixels.get("bottom", 0)
    left = border_pixels.get("left", 0)
    right = border_pixels.get("right", 0)

    lw, lh = logo.size

    # Base positions (in border area)
    if position == "top-left":
        x = offset_x
        y = offset_y
    elif position == "top-right":
        x = img_w - right - lw - offset_x
        y = offset_y
    elif position == "bottom-left":
        x = offset_x
        y = img_h - bottom - lh - offset_y
    elif position == "bottom-right":
        x = img_w - right - lw - offset_x
        y = img_h - bottom - lh - offset_y
    elif position == "center-top":
        x = (img_w - lw) // 2 + offset_x
        y = offset_y
    elif position == "center-bottom":
        x = (img_w - lw) // 2 + offset_x
        y = img_h - bottom - lh - offset_y
    elif position == "left-center":
        x = offset_x
        y = (img_h - lh) // 2 + offset_y
    elif position == "right-center":
        x = img_w - right - lw - offset_x
        y = (img_h - lh) // 2 + offset_y
    else:
        # Default: bottom-left
        x = offset_x
        y = img_h - bottom - lh - offset_y

    # Clamp to image bounds
    x = max(0, min(x, img_w - lw))
    y = max(0, min(y, img_h - lh))

    return x, y


def place_logos(image, logos_config, border_pixels):
    """
    Place logos on a bordered image.

    Args:
        image: PIL Image with border
        logos_config: list of logo config dicts
        border_pixels: dict of border pixel values (for positioning context)

    Returns:
        PIL Image with logos pasted
    """
    if not logos_config:
        return image

    # Ensure RGBA for logo compositing
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # Calculate max logo size based on smallest border dimension
    top = border_pixels.get("top", 0)
    bottom = border_pixels.get("bottom", 0)
    left = border_pixels.get("left", 0)
    right = border_pixels.get("right", 0)
    min_border = min(top, bottom, left, right) if any([top, bottom, left, right]) else 50
    max_logo_dim = int(min_border * 0.9)

    for logo_cfg in logos_config:
        if not logo_cfg.get("enabled"):
            continue
        path = logo_cfg.get("path", "")
        if not path or not os.path.exists(path):
            continue

        try:
            scale = logo_cfg.get("scale", 0.5)
            max_size = int(max_logo_dim * scale * 2)

            # Detect SVG and use appropriate loader
            if path.lower().endswith(".svg"):
                logo = _load_svg_logo(path, max_size)
            else:
                logo = _load_logo(path, max_size=max_size)

            position = logo_cfg.get("position", "bottom-left")
            offset_x = logo_cfg.get("offset_x", 0)
            offset_y = logo_cfg.get("offset_y", 0)

            x, y = _get_logo_position(image.size, border_pixels, logo, position, offset_x, offset_y)

            # Create a temporary layer for proper alpha compositing
            layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            layer.paste(logo, (x, y))
            image = Image.alpha_composite(image, layer)
        except Exception:
            continue

    return image
