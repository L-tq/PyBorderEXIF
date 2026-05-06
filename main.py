#!/usr/bin/env python3
"""
PyBorderEXIF - Add customizable borders, EXIF metadata, and logos to images.

Usage:
    python main.py cli [options]           Command-line interface
    python main.py tui                      Text User Interface
    python main.py gui                      Graphical User Interface
"""

import sys


def main():
    if len(sys.argv) < 2:
        print("PyBorderEXIF - Image Border & EXIF Tool")
        print()
        print("Usage: python main.py <mode> [options]")
        print()
        print("Modes:")
        print("  cli     Command-line interface (scriptable)")
        print("  tui     Text User Interface (interactive terminal)")
        print("  gui     Graphical User Interface (visual)")
        print()
        print("Examples:")
        print("  python main.py cli photo.jpg")
        print("  python main.py cli --dir ./photos/")
        print("  python main.py tui")
        print("  python main.py gui")
        sys.exit(0)

    mode = sys.argv[1].lower()
    # Remove 'main.py mode' from argv so sub-modules see clean args
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if mode == "cli":
        from cli import main as cli_main
        cli_main()
    elif mode == "tui":
        from tui import main as tui_main
        tui_main()
    elif mode == "gui":
        from gui import main as gui_main
        gui_main()
    else:
        print(f"Unknown mode: {mode}")
        print("Valid modes: cli, tui, gui")
        sys.exit(1)


if __name__ == "__main__":
    main()
