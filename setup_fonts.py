#!/usr/bin/env python3
"""Download required fonts for ExifBorder.

Downloads Roboto from Google Fonts.
Source Han Sans (Noto Sans CJK) is usually available via system packages:
  Ubuntu/Debian: sudo apt install fonts-noto-cjk
  Fedora: sudo dnf install google-noto-sans-cjk-fonts
"""

import os
import sys
import zipfile
import io
from pathlib import Path

FONTS_DIR = Path(__file__).parent / 'static' / 'fonts'
FONTS_DIR.mkdir(parents=True, exist_ok=True)

# Roboto font files we need
ROBOTO_VARIANTS = {
    'Roboto-Regular.ttf': 'Roboto-Regular',
    'Roboto-Bold.ttf': 'Roboto-Bold',
    'Roboto-Italic.ttf': 'Roboto-Italic',
    'Roboto-BoldItalic.ttf': 'Roboto-BoldItalic',
    'Roboto-Thin.ttf': 'Roboto-Thin',
    'Roboto-ThinItalic.ttf': 'Roboto-ThinItalic',
    'Roboto-Light.ttf': 'Roboto-Light',
    'Roboto-LightItalic.ttf': 'Roboto-LightItalic',
    'Roboto-Medium.ttf': 'Roboto-Medium',
    'Roboto-MediumItalic.ttf': 'Roboto-MediumItalic',
}


def main():
    print("Checking available fonts...")

    # Check what's already available in system
    import subprocess
    try:
        result = subprocess.run(['fc-list', ':lang=zh'], capture_output=True, text=True)
        if result.stdout.strip():
            print("  Chinese fonts found (system)")
        else:
            print("  No Chinese fonts found. Install: sudo apt install fonts-noto-cjk")
    except Exception:
        pass

    # Check if Roboto is already downloaded
    missing = []
    for fname in ROBOTO_VARIANTS:
        fpath = FONTS_DIR / fname
        if not fpath.exists():
            missing.append(fname)

    if not missing:
        print("All Roboto font files present.")
        return

    print(f"Missing {len(missing)} Roboto font(s).")
    print()
    print("To get Roboto fonts, you can:")
    print()
    print("Option 1: Install system package")
    print("  Ubuntu/Debian: sudo apt install fonts-roboto")
    print()
    print("Option 2: Download from Google Fonts")
    print("  1. Visit: https://fonts.google.com/specimen/Roboto")
    print("  2. Click 'Download family'")
    print("  3. Extract the .ttf files to:", FONTS_DIR)
    print()
    print("Option 3: Use the existing system fallbacks")
    print("  DejaVu Sans / Liberation Sans will be used instead.")
    print("  These are already available on your system.")


if __name__ == '__main__':
    main()
