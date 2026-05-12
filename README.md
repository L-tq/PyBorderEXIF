# ExifBorder

Web app for framing photos with EXIF metadata overlays. Upload JPEG or Sony ARW images, configure borders with camera/lens info text, add logos, and batch-render the output.

## Requirements

- Python 3.10+
- System libraries: `libraw` (for ARW support)

```bash
# Ubuntu/Debian
sudo apt install libraw-dev fonts-noto-cjk fonts-roboto

# Fedora
sudo dnf install LibRaw-devel google-noto-sans-cjk-fonts google-roboto-fonts
```

## Install

```bash
git clone <repo-url> exifborder
cd exifborder
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Fonts

The app needs fonts that cover both Latin and CJK characters:

| Package | Provides |
|---------|----------|
| `fonts-roboto` | UI and default border text (Latin) |
| `fonts-noto-cjk` | Chinese/Japanese/Korean glyphs in rendered borders |

If Roboto isn't installed as a system package, run `python setup_fonts.py` for alternative setup instructions. Without Noto Sans CJK, CJK text in borders will render as blank squares.

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
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:8000 app:app
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
├── setup_fonts.py      # Font setup helper
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
