"""Border calculation for image framing."""


def calculate_border_custom(top, bottom, left, right):
    """Return border dimensions for custom mode."""
    return {
        'top': max(0, int(top)),
        'bottom': max(0, int(bottom)),
        'left': max(0, int(left)),
        'right': max(0, int(right)),
    }


def calculate_border_aspect_ratio(img_w, img_h, auto_param, a=None, b=None, c=None):
    """
    Calculate border dimensions that preserve the original aspect ratio.

    Formula: 2 * a * H = W * (b + c)

    User provides two of (a, b, c) and selects which one to auto-calculate.

    Args:
        img_w: Original image width
        img_h: Original image height
        auto_param: 'a', 'b', or 'c' - which parameter to auto-calculate
        a: Left/right border width (same on both sides)
        b: Top border height
        c: Bottom border height

    Returns:
        dict with 'top', 'bottom', 'left', 'right'
    """
    if auto_param == 'a':
        # Calculate a from b and c
        if b is None or c is None:
            raise ValueError('b and c are required when auto-calculating a')
        b_val, c_val = float(b), float(c)
        if img_h == 0:
            a_val = 0
        else:
            a_val = (img_w * (b_val + c_val)) / (2 * img_h)
        return {
            'top': max(0, int(b_val)),
            'bottom': max(0, int(c_val)),
            'left': max(0, int(a_val)),
            'right': max(0, int(a_val)),
        }

    elif auto_param == 'b':
        # Calculate b from a and c
        if a is None or c is None:
            raise ValueError('a and c are required when auto-calculating b')
        a_val, c_val = float(a), float(c)
        if img_w == 0:
            b_val = 0
        else:
            b_val = (2 * a_val * img_h) / img_w - c_val
        return {
            'top': max(0, int(b_val)),
            'bottom': max(0, int(c_val)),
            'left': max(0, int(a_val)),
            'right': max(0, int(a_val)),
        }

    elif auto_param == 'c':
        # Calculate c from a and b
        if a is None or b is None:
            raise ValueError('a and b are required when auto-calculating c')
        a_val, b_val = float(a), float(b)
        if img_w == 0:
            c_val = 0
        else:
            c_val = (2 * a_val * img_h) / img_w - b_val
        return {
            'top': max(0, int(b_val)),
            'bottom': max(0, int(c_val)),
            'left': max(0, int(a_val)),
            'right': max(0, int(a_val)),
        }

    else:
        raise ValueError(f'Invalid auto_param: {auto_param}. Must be a, b, or c.')


def get_final_dimensions(img_w, img_h, border):
    """Get the final image dimensions after adding borders."""
    return (
        img_w + border['left'] + border['right'],
        img_h + border['top'] + border['bottom']
    )


def get_image_area(border):
    """Get the (x, y, width, height) of the image area within the bordered canvas."""
    return (
        border['left'],
        border['top'],
    )
