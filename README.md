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

### Windows

No system dependencies required. `rawpy` ships pre-built wheels for 64-bit Windows (Python 3.10–3.14).

Run the font download script — it tries Google Fonts first, then falls back to GitHub mirrors for users in China:

```powershell
python download_fonts.py
```

This downloads Roboto (Latin) and Noto Sans CJK SC (Simplified Chinese) into `static/fonts/`. Pass `--force` to re-download.

SVG logo support (`cairosvg`) needs the Cairo C library on Windows. If you don't need SVG logos, this is optional. To enable it, install via Conda:

```powershell
conda install -c conda-forge cairo cairosvg
```

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### Fonts

The app needs fonts that cover both Latin and CJK characters for border text:

| Package | Provides |
|---------|----------|
| Roboto | Default border text (Latin) |
| Noto Sans CJK | Chinese/Japanese/Korean glyphs |

If system packages aren't available (Windows, offline, or no root), run the bundled download script:

```bash
python download_fonts.py      # Linux / macOS / Windows
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

### Production

Flask's built-in server is not suitable for production. Use a WSGI server:

```bash
# Linux / macOS
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:8000 app:app

# Windows (gunicorn is Unix-only)
pip install waitress
waitress-serve --host 127.0.0.1 --port 8000 app:app
```

For a full production setup, place gunicorn behind a reverse proxy (nginx, Caddy) that handles TLS and serves static files:

```nginx
# Example nginx config
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate     /etc/ssl/certs/example.com.pem;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # Static files served directly
    location /static/ {
        alias /opt/exifborder/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Set a persistent secret key for sessions:

```bash
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

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
