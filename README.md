# ExifBorder

Web app for framing photos with EXIF metadata overlays. Upload JPEG or Sony ARW images, configure borders with camera/lens info text, add logos, and batch-render the output.

## Requirements

- Python 3.10+

### Linux

```bash
# Ubuntu/Debian
sudo apt install libraw-dev fonts-noto-cjk fonts-roboto

# Fedora
sudo dnf install LibRaw-devel google-noto-sans-cjk-fonts google-roboto-fonts
```

`libraw-dev` is needed to build `rawpy` for ARW raw file support. `fonts-noto-cjk` provides Chinese/Japanese/Korean glyphs for border text overlays.

### macOS

```bash
brew install libraw
```

`rawpy` provides pre-built wheels for macOS, but libraw must be present at runtime. Fonts are bundled with macOS (PingFang SC covers CJK) — no extra font packages needed.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Fonts

The app needs fonts that cover both Latin and CJK characters for border text:

| Package | Provides |
|---------|----------|
| Roboto | Default border text (Latin) |
| Noto Sans CJK | Chinese/Japanese/Korean glyphs |

If system packages aren't available (offline, or no root), run the bundled download script:

```bash
python download_fonts.py
python download_fonts.py --force  # re-download all
```

This downloads Roboto and Noto Sans CJK SC into `static/fonts/`. Download order: Google Fonts → `fonts.googlecn.com` (China mirror) → GitHub raw → `ghproxy.com` (GitHub proxy). Without Noto Sans CJK, CJK text in borders renders as blank squares.

## Run

### Development

```bash
flask run --host 127.0.0.1 --port 5000
# or
python app.py
```

The dev server opens a browser automatically at `http://127.0.0.1:5000`.


## Directory layout

```
exifborder/
├── app.py              # Flask application entry point
├── requirements.txt
├── download_fonts.py   # Font downloader (multi-mirror)
├── config.json         # Persistent user settings (auto-created)
├── src/
│   ├── border.py       # Border dimension calculation
│   ├── config_manager.py
│   ├── exif_reader.py  # EXIF parsing (JPEG + ARW)
│   └── image_processor.py  # Rendering engine
├── static/
│   ├── css/
│   ├── js/
│   └── fonts/          # Bundled .ttf fonts (optional)
├── templates/          # Jinja2 HTML templates
├── uploads/            # Session-scoped uploaded images (runtime)
└── temp/               # Session-scoped previews & renders (runtime)
```

`uploads/` and `temp/` are created automatically and gitignored. Each browser session gets its own subdirectory.

## API overview

| Endpoint | Description |
|----------|-------------|
| `POST /api/images` | Upload images, returns EXIF metadata |
| `GET /api/images` | List uploaded images |
| `POST /api/preview` | Generate downsized preview with current settings |
| `POST /api/render` | Full-resolution render of all images |
| `GET /api/download/<id>/<file>` | Download single rendered image |
| `GET /api/download-all/<id>` | Download all renders as ZIP |
| `GET/POST /api/config` | Load/save persistent settings |
| `POST /api/cleanup` | Clear session data |
