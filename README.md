# PyBorderEXIF

Add customizable borders, EXIF metadata, and logos to images.

## Features

- Customizable image borders (preset or custom dimensions)
- EXIF metadata overlay (author, camera model, date, etc.)
- Logo placement at four positions
- Multiple interfaces: CLI, TUI, GUI

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Command-line interface
python main.py cli photo.jpg
python main.py cli --dir ./photos/

# Text User Interface
python main.py tui

# Graphical User Interface
python main.py gui
```

## Configuration

Edit `config.yaml` to customize:
- Border style and dimensions
- EXIF fields to display
- Logo placement
- Output format and quality

## Requirements

- Python 3.8+
- Pillow>=10.0.0
- rawpy>=0.18.0
- PyYAML>=6.0
- textual>=0.40.0