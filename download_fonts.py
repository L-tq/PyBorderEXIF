#!/usr/bin/env python3
"""Download fonts for ExifBorder with China-accessible mirrors.

Downloads Roboto (Latin) and Noto Sans CJK SC (Simplified Chinese).
Tries Google Fonts first, then falls back to mirrors accessible from
mainland China.

Usage:
    python download_fonts.py          # download all missing fonts
    python download_fonts.py --force  # re-download even if present
"""

import argparse
import io
import os
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

FONTS_DIR = Path(__file__).resolve().parent / "static" / "fonts"
FONTS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ── Roboto ──────────────────────────────────────────────────────────────────
# Google Fonts ZIP (all variants in one download), then individual-file mirrors.

ROBOTO_ZIP_URLS = [
    "https://fonts.google.com/download?family=Roboto",
    "https://fonts.googlecn.com/download?family=Roboto",
]

ROBOTO_VARIANTS = [
    "Roboto-Regular.ttf",
    "Roboto-Bold.ttf",
    "Roboto-Italic.ttf",
    "Roboto-BoldItalic.ttf",
    "Roboto-Thin.ttf",
    "Roboto-ThinItalic.ttf",
    "Roboto-Light.ttf",
    "Roboto-LightItalic.ttf",
    "Roboto-Medium.ttf",
    "Roboto-MediumItalic.ttf",
]

# Per-file fallback when the ZIP approach fails.
ROBOTO_FALLBACK_URLS = {
    fname: [
        f"https://raw.githubusercontent.com/google/fonts/main/ofl/roboto/static/{fname}",
        f"https://ghproxy.com/https://raw.githubusercontent.com/google/fonts/main/ofl/roboto/static/{fname}",
    ]
    for fname in ROBOTO_VARIANTS
}

# ── Noto Sans CJK SC ────────────────────────────────────────────────────────

NOTO_CJK_SC_ZIP_URLS = [
    "https://github.com/googlefonts/noto-cjk/releases/download/Sans2.004/03_NotoSansCJKsc.zip",
    "https://ghproxy.com/https://github.com/googlefonts/noto-cjk/releases/download/Sans2.004/03_NotoSansCJKsc.zip",
]

NOTO_CJK_SC_FILES = {
    "NotoSansCJKsc-Regular.otf": "NotoSansSC-Regular.ttf",
    "NotoSansCJKsc-Bold.otf": "NotoSansSC-Bold.ttf",
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def _download_url(url, timeout=30):
    """Download a URL and return bytes. Returns None on failure."""
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except URLError as e:
        print(f"    ✗ {url.split('/')[2]}: {e.reason}")
        return None


def _try_urls(url_list, label, timeout=30):
    """Try each URL in order.  Returns bytes from the first one that succeeds."""
    for url in url_list:
        host = url.split("/")[2]
        print(f"  {label}: trying {host} ...", end=" ", flush=True)
        data = _download_url(url, timeout=timeout)
        if data:
            print(f"✓ ({len(data):,} bytes)")
            return data
        print()
    return None


def _find_files_in_zip(zf, targets):
    """Search a ZIP for target filenames regardless of directory structure.

    Returns dict {target_name: data_bytes} for each match found.
    """
    found = {}
    for name in zf.namelist():
        basename = os.path.basename(name)
        if basename in targets:
            found[basename] = zf.read(name)
    return found


# ── Roboto ──────────────────────────────────────────────────────────────────

def download_roboto(force=False):
    """Download Roboto via Google Fonts ZIP, falling back to individual files."""
    missing = [f for f in ROBOTO_VARIANTS if force or not (FONTS_DIR / f).exists()]

    if not missing:
        print("Roboto: all files present.\n")
        return True

    print(f"Roboto: {len(missing)} file(s) needed.\n")

    # ── Primary: Google Fonts ZIP ────────────────────────────────────────
    zip_data = _try_urls(ROBOTO_ZIP_URLS, "Google Fonts ZIP", timeout=60)
    if zip_data:
        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                found = _find_files_in_zip(zf, set(missing))
            if found:
                for fname, data in found.items():
                    (FONTS_DIR / fname).write_bytes(data)
                    print(f"    ✓ {fname} ({len(data):,} bytes)")
                    missing.remove(fname)
            else:
                print("    ZIP did not contain expected font files")
        except zipfile.BadZipFile:
            print("    ✗ Bad ZIP — falling back to individual downloads")

    # ── Fallback: individual files ───────────────────────────────────────
    if missing:
        print(f"\n  Fallback: downloading {len(missing)} file(s) individually ...")
        ok = True
        for fname in missing:
            print(f"    {fname}")
            data = _try_urls(ROBOTO_FALLBACK_URLS[fname], "  ", timeout=30)
            if data:
                (FONTS_DIR / fname).write_bytes(data)
            else:
                print(f"      ✗ All mirrors failed for {fname}")
                ok = False
        if not ok:
            print()
            return False

    print()
    return True


# ── Noto Sans CJK SC ────────────────────────────────────────────────────────

def download_noto_cjk_sc(force=False):
    """Download Noto Sans CJK SC OTF files from GitHub release ZIP."""
    existing = all((FONTS_DIR / t).exists() for t in NOTO_CJK_SC_FILES.values())
    if existing and not force:
        print("Noto Sans CJK SC: all files present.\n")
        return True

    print("Noto Sans CJK SC: downloading release ZIP ...")
    zip_data = _try_urls(NOTO_CJK_SC_ZIP_URLS, "GitHub release", timeout=120)

    if not zip_data:
        print("  ✗ All mirrors failed for Noto Sans CJK SC\n")
        return False

    print("  Extracting ...")
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            for name_in_zip, target_name in NOTO_CJK_SC_FILES.items():
                if name_in_zip in zf.namelist():
                    data = zf.read(name_in_zip)
                    (FONTS_DIR / target_name).write_bytes(data)
                    print(f"    ✓ {target_name} ({len(data):,} bytes)")
                else:
                    print(f"    ✗ {name_in_zip} not found in ZIP")
                    return False
    except zipfile.BadZipFile:
        print("  ✗ Downloaded file is not a valid ZIP")
        return False

    print()
    return True


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Download ExifBorder fonts")
    parser.add_argument("--force", action="store_true", help="Re-download even if files exist")
    args = parser.parse_args()

    print(f"Font directory: {FONTS_DIR}\n")

    roboto_ok = download_roboto(force=args.force)
    noto_ok = download_noto_cjk_sc(force=args.force)

    if roboto_ok and noto_ok:
        print("All fonts ready.")
    else:
        print("Some fonts could not be downloaded.", file=sys.stderr)
        print(
            "See https://github.com/googlefonts/noto-cjk/releases for manual downloads.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
