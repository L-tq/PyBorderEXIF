"""Logo placement on bordered images."""

import os
import logging
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)


def _load_svg_logo(logo_path, max_width=None, max_height=None):
    """Render an SVG logo to a PIL Image, preserving aspect ratio."""
    import cairosvg
    kwargs = {}
    if max_width is not None:
        kwargs["output_width"] = max_width
    if max_height is not None:
        kwargs["output_height"] = max_height
    png_bytes = cairosvg.svg2png(url=logo_path, **kwargs)
    return Image.open(BytesIO(png_bytes)).convert("RGBA")


def _load_logo(logo_path, max_width=None, max_height=None):
    """Load a logo image, fit within max dimensions preserving aspect ratio."""
    img = Image.open(logo_path)
    if img.mode not in ("RGBA", "RGB"):
        img = img.convert("RGBA")
    if max_width and img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    if max_height and img.height > max_height:
        ratio = max_height / img.height
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    return img


def _get_logo_position(image_size, border_pixels, logo, position, offset_x, offset_y):
    """
    Calculate the (x, y) paste position for a logo.
    position: "top-left", "top-right", "bottom-left", "bottom-right"
    """
    img_w, img_h = image_size
    lw, lh = logo.size

    # Positions are relative to the outer image edges; offset pushes inward.
    # The logo is already sized to fit within the border strip at its position.
    if position == "top-left":
        x = offset_x
        y = offset_y
    elif position == "top-right":
        x = img_w - lw - offset_x
        y = offset_y
    elif position == "bottom-left":
        x = offset_x
        y = img_h - lh - offset_y
    elif position == "bottom-right":
        x = img_w - lw - offset_x
        y = img_h - lh - offset_y
    elif position == "center-top":
        x = (img_w - lw) // 2 + offset_x
        y = offset_y
    elif position == "center-bottom":
        x = (img_w - lw) // 2 + offset_x
        y = img_h - lh - offset_y
    elif position == "left-center":
        x = offset_x
        y = (img_h - lh) // 2 + offset_y
    elif position == "right-center":
        x = img_w - lw - offset_x
        y = (img_h - lh) // 2 + offset_y
    else:
        # Default: bottom-left
        x = offset_x
        y = img_h - lh - offset_y

    # Clamp to image bounds
    x = max(0, min(x, img_w - lw))
    y = max(0, min(y, img_h - lh))

    return x, y


def _get_logo_max_dims(position, border_pixels, image_size, scale, margin_ratio=0.85):
    """Compute max width/height for a logo based on its border position.

    The logo is sized to fit within the border at its position (e.g. a
    bottom-left logo fits the bottom border height). *margin_ratio* reserves a
    fraction of the border for padding (0.85 = 7.5% margin on each side).
    """
    top = border_pixels.get("top", 0)
    bottom = border_pixels.get("bottom", 0)
    left = border_pixels.get("left", 0)
    right = border_pixels.get("right", 0)

    max_w = None
    max_h = None

    if position in ("top-left", "top-right", "center-top"):
        avail = top
        if avail > 0:
            max_h = int(avail * margin_ratio * scale)
    elif position in ("bottom-left", "bottom-right", "center-bottom"):
        avail = bottom
        if avail > 0:
            max_h = int(avail * margin_ratio * scale)
    elif position in ("left-center",):
        avail = left
        if avail > 0:
            max_w = int(avail * margin_ratio * scale)
    elif position in ("right-center",):
        avail = right
        if avail > 0:
            max_w = int(avail * margin_ratio * scale)

    # If the primary border dimension is zero (or position is unknown),
    # fall back to the smallest non-zero border.
    if max_h is None and max_w is None:
        nonzero = [v for v in (top, bottom, left, right) if v > 0]
        fallback = min(nonzero) if nonzero else int(min(image_size) * 0.05)
        max_h = int(fallback * margin_ratio * scale)

    return max_w, max_h


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

    any_enabled = any(logo.get("enabled") for logo in logos_config)
    if not any_enabled:
        return image

    # Ensure RGBA for logo compositing
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    for logo_cfg in logos_config:
        if not logo_cfg.get("enabled"):
            continue
        path = logo_cfg.get("path", "")
        if not path:
            continue
        if not os.path.exists(path):
            logger.warning("Logo file not found: %s", path)
            continue

        try:
            position = logo_cfg.get("position", "bottom-left")
            scale = logo_cfg.get("scale", 0.5)

            max_w, max_h = _get_logo_max_dims(position, border_pixels, image.size, scale)

            # Detect SVG and use appropriate loader
            if path.lower().endswith(".svg"):
                logo = _load_svg_logo(path, max_width=max_w, max_height=max_h)
            else:
                logo = _load_logo(path, max_width=max_w, max_height=max_h)

            offset_x = logo_cfg.get("offset_x", 0)
            offset_y = logo_cfg.get("offset_y", 0)

            x, y = _get_logo_position(image.size, border_pixels, logo, position, offset_x, offset_y)

            # Create a temporary layer for proper alpha compositing
            layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            layer.paste(logo, (x, y))
            image = Image.alpha_composite(image, layer)
        except Exception as e:
            logger.warning("Failed to place logo %s: %s", path, e)

    return image
