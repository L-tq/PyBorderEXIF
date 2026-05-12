"""EXIF reader for JPEG and Sony ARW files."""

import io
import struct
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# Common EXIF tag IDs we care about
EXIF_TAG_IDS = {
    'Make': 0x010F,
    'Model': 0x0110,
    'Software': 0x0131,
    'DateTime': 0x0132,
    'Artist': 0x013B,
    'Copyright': 0x8298,
    'ExposureTime': 0x829A,
    'FNumber': 0x829D,
    'ISOSpeedRatings': 0x8827,
    'ShutterSpeedValue': 0x9201,
    'ApertureValue': 0x9202,
    'BrightnessValue': 0x9203,
    'FocalLength': 0x920A,
    'LensMake': 0xA433,
    'LensModel': 0xA434,
    'BodySerialNumber': 0xA431,
    'LensSerialNumber': 0xA435,
    'GPSLatitudeRef': 0x0001,
    'GPSLatitude': 0x0002,
    'GPSLongitudeRef': 0x0003,
    'GPSLongitude': 0x0004,
    'GPSAltitudeRef': 0x0005,
    'GPSAltitude': 0x0006,
}


def _to_float(val):
    """Convert EXIF value (possibly IFDRational) to float."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _to_float_pair(val):
    """Convert EXIF value to (float, float) tuple regardless of type."""
    if val is None:
        return None
    try:
        if isinstance(val, tuple) and len(val) == 2:
            return (float(val[0]), float(val[1]))
        return (float(val), 1.0)
    except (ValueError, TypeError):
        return None


def _format_exposure_time(value):
    """Format exposure time as a readable fraction."""
    if value is None:
        return None
    f = _to_float(value)
    if f is not None:
        if f >= 1:
            return f'{f:.0f}s'
        else:
            denom = round(1 / f)
            return f'1/{denom}s'
    pair = _to_float_pair(value)
    if pair:
        num, den = pair
        val_f = den / num if num != 0 else 0
        if val_f >= 1:
            return f'{val_f:.0f}s'
        else:
            return f'{int(num)}/{int(den)}s'
    return str(value)


def _format_fnumber(value):
    """Format F-number as f/X."""
    if value is None:
        return None
    f = _to_float(value)
    if f is not None:
        return f'f/{f:.1f}'
    pair = _to_float_pair(value)
    if pair and pair[1] != 0:
        return f'f/{pair[0] / pair[1]:.1f}'
    return str(value)


def _format_focal_length(value):
    """Format focal length in mm."""
    if value is None:
        return None
    f = _to_float(value)
    if f is not None:
        return f'{f:.0f}mm'
    pair = _to_float_pair(value)
    if pair and pair[1] != 0:
        return f'{pair[0] / pair[1]:.0f}mm'
    return str(value)


def _format_iso(value):
    """Format ISO value."""
    if value is None:
        return None
    if isinstance(value, int):
        return f'ISO {value}'
    if isinstance(value, tuple):
        return f'ISO {value[0]}'
    return str(value)


def _format_gps(value):
    """Format GPS coordinate."""
    if value is None:
        return None
    if isinstance(value, tuple) and len(value) == 3:
        deg = float(value[0])
        min_val = float(value[1])
        sec = float(value[2])
        return deg + min_val / 60 + sec / 3600
    return value


def _convert_gps_to_decimal(gps_coord, gps_ref):
    """Convert GPS coordinates from EXIF format to decimal degrees."""
    if gps_coord is None or gps_ref is None:
        return None
    decimal = _format_gps(gps_coord)
    if decimal is None:
        return None
    if gps_ref in ('S', 'W'):
        decimal = -decimal
    return round(decimal, 6)


def read_exif_from_jpeg(filepath):
    """Read EXIF data from a JPEG file."""
    try:
        img = Image.open(filepath)
        exif_data = img._getexif()
        if exif_data is None:
            return _empty_exif_data()

        result = _empty_exif_data()
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            result['all_tags'][tag_name] = str(value)

        result.update({
            'camera_make': exif_data.get(0x010F, ''),
            'camera_model': exif_data.get(0x0110, ''),
            'software': exif_data.get(0x0131, ''),
            'datetime': exif_data.get(0x0132, ''),
            'artist': exif_data.get(0x013B, ''),
            'exposure_time': _format_exposure_time(exif_data.get(0x829A)),
            'fnumber': _format_fnumber(exif_data.get(0x829D)),
            'iso': _format_iso(exif_data.get(0x8827)),
            'focal_length': _format_focal_length(exif_data.get(0x920A)),
            'lens_make': exif_data.get(0xA433, ''),
            'lens_model': exif_data.get(0xA434, ''),
            'aperture': exif_data.get(0x9202, ''),
        })
        if result['aperture']:
            f = _to_float(result['aperture'])
            if f is not None:
                result['aperture'] = f'f/{f:.1f}'
            else:
                pair = _to_float_pair(result['aperture'])
                if pair and pair[1] != 0:
                    result['aperture'] = f'f/{pair[0] / pair[1]:.1f}'
        elif result['fnumber']:
            # Most cameras use FNumber, not ApertureValue
            result['aperture'] = result['fnumber']

        # GPS
        gps_info = exif_data.get(0x8825)
        if gps_info:
            lat = _convert_gps_to_decimal(
                gps_info.get(0x0002),
                gps_info.get(0x0001)
            )
            lon = _convert_gps_to_decimal(
                gps_info.get(0x0004),
                gps_info.get(0x0003)
            )
            if lat is not None and lon is not None:
                result['gps'] = f'{lat:.6f}, {lon:.6f}'

        return result
    except Exception as e:
        return _empty_exif_data(error=str(e))


def read_exif_from_arw(filepath):
    """Read EXIF data from a Sony ARW raw file."""
    try:
        import rawpy
        import exifread

        result = _empty_exif_data()

        # Use exifread to get metadata (it handles ARW better for EXIF)
        with open(filepath, 'rb') as f:
            tags = exifread.process_file(f, details=False)

        # Map common tags
        tag_map = {
            'Image Make': ('camera_make', str),
            'Image Model': ('camera_model', str),
            'Image Software': ('software', str),
            'Image DateTime': ('datetime', str),
            'Image Artist': ('artist', str),
            'EXIF ExposureTime': ('exposure_time_raw', None),
            'EXIF FNumber': ('fnumber_raw', None),
            'EXIF ISOSpeedRatings': ('iso_raw', None),
            'EXIF FocalLength': ('focal_length_raw', None),
            'EXIF LensMake': ('lens_make', str),
            'EXIF LensModel': ('lens_model', str),
            'EXIF ApertureValue': ('aperture', None),
        }

        for exif_key, (result_key, _) in tag_map.items():
            if exif_key in tags:
                result[result_key] = str(tags[exif_key])

        # Format values
        if 'exposure_time_raw' in result:
            val = result.pop('exposure_time_raw')
            result['exposure_time'] = _format_exposure_time(_parse_exifread_ratio(val))
        if 'fnumber_raw' in result:
            val = result.pop('fnumber_raw')
            result['fnumber'] = _format_fnumber(_parse_exifread_ratio(val))
        if 'iso_raw' in result:
            result['iso'] = f'ISO {result.pop("iso_raw")}'
        if 'focal_length_raw' in result:
            val = result.pop('focal_length_raw')
            result['focal_length'] = _format_focal_length(_parse_exifread_ratio(val))
        if 'aperture' in result:
            val = _parse_exifread_ratio(result['aperture'])
            if val:
                result['aperture'] = f'f/{val:.1f}'
            elif result.get('fnumber'):
                result['aperture'] = result['fnumber']
        elif result.get('fnumber'):
            result['aperture'] = result['fnumber']

        # Store all tags
        for key, tag in tags.items():
            result['all_tags'][key] = str(tag)

        # Try to get image dimensions via rawpy
        try:
            with rawpy.imread(filepath) as raw:
                result['image_width'] = raw.sizes.raw_width
                result['image_height'] = raw.sizes.raw_height
        except Exception:
            pass

        return result
    except Exception as e:
        return _empty_exif_data(error=str(e))


def _parse_exifread_ratio(val_str):
    """Parse an exifread rational value string like '1/250'."""
    if val_str is None:
        return None
    s = str(val_str)
    if '/' in s:
        parts = s.split('/')
        try:
            return float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(s)
    except ValueError:
        return None


def read_exif(filepath):
    """Read EXIF data from an image file (JPEG or ARW)."""
    ext = filepath.lower().split('.')[-1] if '.' in filepath else ''
    if ext in ('jpg', 'jpeg'):
        return read_exif_from_jpeg(filepath)
    elif ext == 'arw':
        return read_exif_from_arw(filepath)
    else:
        return _empty_exif_data(error=f'Unsupported format: {ext}')


def _empty_exif_data(error=None):
    return {
        'camera_make': '',
        'camera_model': '',
        'software': '',
        'datetime': '',
        'artist': '',
        'exposure_time': '',
        'fnumber': '',
        'iso': '',
        'focal_length': '',
        'lens_make': '',
        'lens_model': '',
        'aperture': '',
        'gps': '',
        'image_width': 0,
        'image_height': 0,
        'all_tags': {},
        'error': error
    }
