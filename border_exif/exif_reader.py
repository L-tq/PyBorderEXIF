"""EXIF metadata extraction for JPEG and RAW (including .ARW) files."""

import io
from PIL import Image
from PIL.ExifTags import Base as ExifBaseTags


# Comprehensive EXIF tag name mapping
_TAG_NAMES = {}
for tag_id, tag_name in ExifBaseTags.__dict__.items():
    if isinstance(tag_name, str) and not tag_id.startswith("_"):
        _TAG_NAMES[int(tag_id)] = tag_name

# Add common MakerNote / extra tags we care about
_EXTRA_TAGS = {
    0x920A: "FocalLength",
    0x829A: "ExposureTime",
    0x829D: "FNumber",
    0x8827: "ISO",
    0x8833: "ISOSpeedRatings",
    0x9204: "ExposureBiasValue",
    0x9207: "MeteringMode",
    0x9208: "LightSource",
    0x9209: "Flash",
    0xA402: "ExposureMode",
    0xA403: "WhiteBalance",
    0xA406: "SceneCaptureType",
    0xA40A: "Sharpness",
    0xA40C: "SubjectDistanceRange",
    0x0110: "CameraModel",
    0x0112: "Orientation",
    0x0131: "Software",
    0xA434: "LensModel",
    0xA405: "FocalLengthIn35mmFilm",
    0xA433: "LensMake",
    0x0132: "DateTime",
    0x9003: "DateTimeOriginal",
    0x9004: "DateTimeDigitized",
    0x013B: "Artist",
    0x8298: "Copyright",
    0x8769: "ExifIFD",
    0x010F: "Make",
    0x011A: "XResolution",
    0x011B: "YResolution",
    0xA20E: "FocalPlaneXResolution",
    0xA20F: "FocalPlaneYResolution",
    0xA210: "FocalPlaneResolutionUnit",
    0xA217: "SensingMethod",
    0xA300: "FileSource",
    0xA301: "SceneType",
    0xA401: "CustomRendered",
    0x0212: "YCbCrSubSampling",
    0x0213: "YCbCrPositioning",
    0x0214: "ReferenceBlackWhite",
    0x828D: "CFARepeatPatternDim",
    0x828E: "CFAPattern",
    0x828F: "BatteryLevel",
    0x9010: "OffsetTime",
    0x9011: "OffsetTimeOriginal",
    0x9012: "OffsetTimeDigitized",
    0x9201: "ShutterSpeedValue",
    0x9202: "ApertureValue",
    0x9203: "BrightnessValue",
    0x9206: "SubjectDistance",
    0x9214: "SubjectArea",
    0xA000: "FlashpixVersion",
    0xA001: "ColorSpace",
    0xA002: "PixelXDimension",
    0xA003: "PixelYDimension",
    0xA004: "RelatedSoundFile",
    0xA005: "InteroperabilityIFD",
    0xA20B: "FlashEnergy",
    0xA20C: "SpatialFrequencyResponse",
    0xA214: "SubjectLocation",
    0xA215: "ExposureIndex",
    0xA302: "CFAPattern",
    0xA420: "ImageUniqueID",
    0xA430: "CameraOwnerName",
    0xA431: "BodySerialNumber",
    0xA432: "LensSpecification",
    0xA435: "LensSerialNumber",
}

_TAG_NAMES.update(_EXTRA_TAGS)

# Friendly labels for display
_FIELD_LABELS = {
    "camera_model": "Camera",
    "lens_model": "Lens",
    "focal_length_35mm": "Focal Length (35mm)",
    "aperture": "Aperture",
    "iso": "ISO",
    "exposure_time": "Shutter",
    "datetime_original": "Date",
    "make": "Make",
    "artist": "Artist",
    "copyright": "Copyright",
    "software": "Software",
    "flash": "Flash",
    "white_balance": "White Balance",
    "metering_mode": "Metering",
    "exposure_bias": "Exp. Bias",
    "orientation": "Orientation",
    "image_unique_id": "Image ID",
    "body_serial_number": "Body Serial",
    "lens_serial_number": "Lens Serial",
}


def get_all_field_names():
    """Return list of all supported EXIF field IDs."""
    return sorted(_FIELD_LABELS.keys())


def get_field_label(field_id):
    """Return human-readable label for a field ID."""
    return _FIELD_LABELS.get(field_id, field_id.replace("_", " ").title())


def _raw_tag_id_to_name(tag_id):
    return _TAG_NAMES.get(tag_id, f"Tag_{tag_id}")


def _extract_pil_exif(image_path):
    """Extract EXIF from JPEG/TIFF using Pillow. Returns flat dict of {name: raw_value}."""
    try:
        img = Image.open(image_path)
        exif_data = img.getexif()
        if not exif_data:
            return {}
        result = {}
        for tag_id, value in exif_data.items():
            name = _raw_tag_id_to_name(tag_id)
            # Handle IFD sub-dicts
            if isinstance(value, dict):
                for sub_id, sub_val in value.items():
                    sub_name = _raw_tag_id_to_name(sub_id)
                    result[f"{name}_{sub_name}"] = sub_val
            else:
                result[name] = value
        return result
    except Exception:
        return {}


def _resolve_ifd_value(ifd_dict, tag_id):
    """Resolve a value from an IFD dict, handling bytes and IFDRational."""
    try:
        value = ifd_dict.get(tag_id)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("ascii", errors="replace").strip("\x00").strip()
        if hasattr(value, "numerator") and hasattr(value, "denominator"):
            return float(value)
        if isinstance(value, tuple) and len(value) == 2:
            try:
                return float(value[0]) / float(value[1])
            except (TypeError, ZeroDivisionError):
                return str(value)
        return value
    except Exception:
        return None


def extract_exif(image_path):
    """
    Extract EXIF data from image (JPEG or RAW/ARW).

    Returns a dict with standardized keys:
        camera_model, lens_model, focal_length_35mm, aperture, iso,
        exposure_time, datetime_original, make, artist, copyright,
        software, flash, white_balance, metering_mode, exposure_bias,
        orientation, image_unique_id, body_serial_number, lens_serial_number,
        and a _raw dict with all extracted tags.
    """
    ext = image_path.lower().rsplit(".", 1)[-1] if "." in image_path else ""

    raw_exif = {}

    if ext in ("arw", "nef", "cr2", "cr3", "dng", "rw2", "orf", "raf", "pef", "srf", "raw"):
        raw_exif = _extract_raw_exif(image_path)
    else:
        raw_exif = _extract_pil_exif(image_path)

    return _normalize_exif(raw_exif)


def _extract_raw_exif(image_path):
    """Extract EXIF from RAW files using rawpy."""
    try:
        import rawpy
        with rawpy.imread(image_path) as raw:
            return _extract_pil_exif(image_path)
    except ImportError:
        return _extract_pil_exif(image_path)
    except Exception:
        return {}


def _normalize_exif(raw_exif):
    """Convert raw EXIF dict to standardized key-value pairs."""
    result = {"_raw": dict(raw_exif)}

    # Camera model
    cam = raw_exif.get("CameraModel") or raw_exif.get("Model")
    if cam and isinstance(cam, str):
        result["camera_model"] = cam.strip("\x00").strip()

    # Lens model
    lens = raw_exif.get("LensModel") or raw_exif.get("LensSpecification")
    if lens and isinstance(lens, str):
        result["lens_model"] = lens.strip("\x00").strip()

    # Focal length (35mm equivalent)
    fl35 = raw_exif.get("FocalLengthIn35mmFilm")
    if fl35 is not None:
        try:
            result["focal_length_35mm"] = f"{int(fl35)}mm"
        except (ValueError, TypeError):
            result["focal_length_35mm"] = str(fl35)
    else:
        fl = raw_exif.get("FocalLength")
        if fl is not None:
            try:
                result["focal_length_35mm"] = f"{float(fl):.0f}mm"
            except (ValueError, TypeError):
                pass

    # Aperture
    fnum = raw_exif.get("FNumber") or raw_exif.get("ApertureValue")
    if fnum is not None:
        try:
            result["aperture"] = f"f/{float(fnum):.1f}"
        except (ValueError, TypeError):
            result["aperture"] = str(fnum)

    # ISO
    iso = raw_exif.get("ISO") or raw_exif.get("ISOSpeedRatings") or raw_exif.get("PhotographicSensitivity")
    if iso is not None:
        try:
            result["iso"] = f"ISO {int(iso)}"
        except (ValueError, TypeError):
            result["iso"] = str(iso)

    # Exposure time
    et = raw_exif.get("ExposureTime")
    if et is not None:
        try:
            val = float(et)
            if val < 1:
                result["exposure_time"] = f"1/{1/val:.0f}s"
            else:
                result["exposure_time"] = f"{val:.1f}s"
        except (ValueError, TypeError):
            result["exposure_time"] = str(et)

    # Date
    dt = raw_exif.get("DateTimeOriginal") or raw_exif.get("DateTime")
    if dt:
        result["datetime_original"] = str(dt).strip("\x00")

    # Make
    make = raw_exif.get("Make")
    if make and isinstance(make, str):
        result["make"] = make.strip("\x00").strip()

    # Artist
    artist = raw_exif.get("Artist")
    if artist and isinstance(artist, str):
        result["artist"] = artist.strip("\x00").strip()

    # Copyright
    cp = raw_exif.get("Copyright")
    if cp and isinstance(cp, str):
        result["copyright"] = cp.strip("\x00").strip()

    # Software
    sw = raw_exif.get("Software")
    if sw and isinstance(sw, str):
        result["software"] = sw.strip("\x00").strip()

    # Flash
    flash = raw_exif.get("Flash")
    if flash is not None:
        flash_map = {0: "No Flash", 1: "Fired", 5: "Fired, No Return", 7: "Fired, Return",
                     8: "On, No Flash", 9: "On, Fired", 13: "On, No Return", 15: "On, Return",
                     16: "Off", 24: "Auto, No Flash", 25: "Auto, Fired",
                     29: "Auto, No Return", 31: "Auto, Return"}
        try:
            result["flash"] = flash_map.get(int(flash), str(flash))
        except (ValueError, TypeError):
            result["flash"] = str(flash)

    # White balance
    wb = raw_exif.get("WhiteBalance")
    if wb is not None:
        try:
            result["white_balance"] = "Auto" if int(wb) == 0 else "Manual"
        except (ValueError, TypeError):
            result["white_balance"] = str(wb)

    # Metering mode
    mm = raw_exif.get("MeteringMode")
    if mm is not None:
        mm_map = {0: "Unknown", 1: "Average", 2: "Center-weighted", 3: "Spot",
                  4: "Multi-spot", 5: "Pattern", 6: "Partial"}
        try:
            result["metering_mode"] = mm_map.get(int(mm), str(mm))
        except (ValueError, TypeError):
            result["metering_mode"] = str(mm)

    # Exposure bias
    eb = raw_exif.get("ExposureBiasValue")
    if eb is not None:
        try:
            result["exposure_bias"] = f"{float(eb):+.1f} EV"
        except (ValueError, TypeError):
            result["exposure_bias"] = str(eb)

    # Orientation
    orient = raw_exif.get("Orientation")
    if orient is not None:
        try:
            orient_map = {1: "Normal", 3: "Rotated 180°", 6: "Rotated 90° CW", 8: "Rotated 90° CCW"}
            result["orientation"] = orient_map.get(int(orient), str(orient))
        except (ValueError, TypeError):
            result["orientation"] = str(orient)

    # Serial numbers
    for src, dst in [("BodySerialNumber", "body_serial_number"),
                     ("LensSerialNumber", "lens_serial_number"),
                     ("ImageUniqueID", "image_unique_id")]:
        v = raw_exif.get(src)
        if v:
            result[dst] = str(v).strip("\x00")

    return result


def exif_to_display_lines(exif_data, fields, author_name=""):
    """
    Convert extracted EXIF data into display text lines.
    Returns list of strings ready for rendering.
    """
    lines = []
    if author_name:
        lines.append(author_name)

    for field_id in fields:
        value = exif_data.get(field_id)
        if value:
            label = get_field_label(field_id)
            lines.append(f"{label}: {value}")

    return lines
