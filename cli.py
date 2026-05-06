#!/usr/bin/env python3
"""CLI interface for PyBorderEXIF."""

import argparse
import os
import sys

from border_exif.config import Config, BORDER_PRESETS
from border_exif.core import process_image, process_images, get_supported_images_from_dir
from border_exif.exif_reader import get_all_field_names, get_field_label


def main():
    parser = argparse.ArgumentParser(
        description="PyBorderEXIF - Add borders, EXIF metadata, and logos to images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s photo.jpg                                    Process a single image
  %(prog)s photo1.jpg photo2.jpg                        Process multiple images
  %(prog)s --dir ./photos/                              Process all images in a folder
  %(prog)s photo.jpg --border preset=polaroid           Use Polaroid preset
  %(prog)s photo.jpg --border custom=20,80,20,80        Custom border (top,bottom,left,right)
  %(prog)s photo.jpg --exif-fields camera_model,iso     Select specific EXIF fields
  %(prog)s photo.jpg --author "Jane Doe"                Add author name
  %(prog)s photo.jpg --logo logo.png                    Add a logo
  %(prog)s photo.jpg --list-fields                      List all available EXIF fields
        """,
    )

    parser.add_argument("images", nargs="*", help="Image file(s) to process")
    parser.add_argument("--dir", help="Process all supported images in directory (non-recursive)")
    parser.add_argument("--output-dir", "-o", help="Output directory for processed images")
    parser.add_argument("--suffix", default="_bordered", help="Suffix for output files (default: _bordered)")

    # Border options
    border_group = parser.add_argument_group("Border Options")
    border_group.add_argument("--border", action="append", default=[],
                              help="Border specification. Use 'preset=NAME' (small/medium/large/polaroid) "
                                   "or 'custom=TOP,BOTTOM,LEFT,RIGHT' or 'color=R,G,B'")
    border_group.add_argument("--border-color", default="255,255,255",
                              help="Border color as R,G,B (default: 255,255,255)")

    # EXIF options
    exif_group = parser.add_argument_group("EXIF Metadata Options")
    exif_group.add_argument("--no-exif", action="store_true", help="Disable EXIF metadata display")
    exif_group.add_argument("--exif-fields", default=None,
                            help="Comma-separated list of EXIF fields to display (default: camera,lens,focal length,aperture,ISO)")
    exif_group.add_argument("--author", default=None, help="Author name to display")
    exif_group.add_argument("--font-size", type=int, default=24, help="Font size for text (default: 24)")
    exif_group.add_argument("--font-color", default="0,0,0", help="Font color as R,G,B (default: 0,0,0)")
    exif_group.add_argument("--text-position", choices=["top", "bottom", "left", "right"], default="bottom",
                            help="Position of metadata text (default: bottom)")
    exif_group.add_argument("--text-align", choices=["left", "center", "right"], default="left",
                            help="Text alignment (default: left)")
    exif_group.add_argument("--list-fields", action="store_true", help="List all available EXIF fields and exit")

    # Logo options
    logo_group = parser.add_argument_group("Logo Options")
    logo_group.add_argument("--logo", action="append", default=[],
                            help="Logo file path (can be specified up to 4 times)")
    logo_group.add_argument("--logo-position", action="append", default=[],
                            help="Logo position (top-left, top-right, bottom-left, bottom-right). "
                                 "Specify once per logo.")

    # Output options
    out_group = parser.add_argument_group("Output Options")
    out_group.add_argument("--format", choices=["JPEG", "PNG"], default="JPEG",
                           help="Output format (default: JPEG)")
    out_group.add_argument("--quality", type=int, default=95,
                           help="JPEG quality 1-100 (default: 95)")

    # Config
    parser.add_argument("--config", default=None, help="Path to config file")
    parser.add_argument("--reset-config", action="store_true", help="Reset config to defaults")

    args = parser.parse_args()

    config = Config(args.config)

    if args.reset_config:
        config.reset()
        print("Configuration reset to defaults.")
        return

    # List fields
    if args.list_fields:
        print("Available EXIF fields:")
        for f in get_all_field_names():
            print(f"  {f}: {get_field_label(f)}")
        return

    # Determine image list
    images = []
    if args.dir:
        images = get_supported_images_from_dir(args.dir)
        if not images:
            print(f"No supported images found in: {args.dir}")
            return
    elif args.images:
        images = list(args.images)
    else:
        parser.print_help()
        return

    # Apply CLI overrides to config
    _apply_cli_overrides(config, args)

    # Update last-used values
    if args.dir:
        config.input_dir = os.path.abspath(args.dir)
    elif images:
        config.input_dir = os.path.abspath(os.path.dirname(images[0]))
    if args.output_dir:
        config.output_dir = os.path.abspath(args.output_dir)
    if args.author:
        config.author_name = args.author

    # Process
    print(f"Processing {len(images)} image(s)...")

    def progress(current, total, path):
        print(f"  [{current}/{total}] {os.path.basename(path)}")

    results = process_images(images, config, progress_callback=progress)

    # Summary
    success = 0
    failures = 0
    for in_path, out_path, error in results:
        if error:
            print(f"  FAILED: {os.path.basename(in_path)} - {error}")
            failures += 1
        else:
            print(f"  OK: {os.path.basename(in_path)} -> {os.path.basename(out_path)}")
            success += 1

    print(f"\nDone: {success} succeeded, {failures} failed.")


def _apply_cli_overrides(config, args):
    """Apply CLI arguments to config."""
    out = config.output
    if args.suffix:
        out["suffix"] = args.suffix
    if args.format:
        out["format"] = args.format
    if args.quality:
        out["jpeg_quality"] = args.quality
    config.output = out

    # Border
    border = config.border
    try:
        border["color"] = [int(x) for x in args.border_color.split(",")]
    except ValueError:
        pass

    for bspec in args.border:
        if "=" not in bspec:
            continue
        key, value = bspec.split("=", 1)
        if key == "preset" and value in BORDER_PRESETS:
            border["preset"] = value
            border["use_custom"] = False
        elif key == "custom":
            parts = [int(x.strip()) for x in value.split(",")]
            if len(parts) == 4:
                border["custom"] = {"top": parts[0], "bottom": parts[1], "left": parts[2], "right": parts[3]}
                border["use_custom"] = True
        elif key == "color":
            try:
                border["color"] = [int(x) for x in value.split(",")]
            except ValueError:
                pass
    config.border = border

    # EXIF
    exif = config.exif
    exif["enabled"] = not args.no_exif
    if args.exif_fields:
        exif["fields"] = [f.strip() for f in args.exif_fields.split(",")]
    if args.author:
        exif["author_name"] = args.author
    exif["font_size"] = args.font_size
    try:
        exif["font_color"] = [int(x) for x in args.font_color.split(",")]
    except ValueError:
        pass
    exif["position"] = args.text_position
    exif["alignment"] = args.text_align
    config.exif = exif

    # Logos
    if args.logo:
        logos = config.logos
        for i, logo_path in enumerate(args.logo[:4]):
            if i < len(logos):
                logos[i]["enabled"] = True
                logos[i]["path"] = os.path.abspath(logo_path)
                logos[i]["scale"] = 0.5
            else:
                logos.append({
                    "enabled": True,
                    "path": os.path.abspath(logo_path),
                    "position": "bottom-left",
                    "scale": 0.5,
                    "offset_x": 0,
                    "offset_y": 0,
                })
        # Apply positions
        for i, pos in enumerate(args.logo_position[:4]):
            if i < len(logos):
                logos[i]["position"] = pos
        config.logos = logos[:4]

    # Logo dir tracking
    if args.logo:
        config.logo_dir = os.path.abspath(os.path.dirname(args.logo[0]))


if __name__ == "__main__":
    main()
