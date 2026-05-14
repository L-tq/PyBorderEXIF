"""ExifBorder - Image framing tool with EXIF overlays."""

import io
import os
import uuid
import zipfile
import json
import time
from pathlib import Path

from flask import (
    Flask, render_template, request, jsonify, session,
    send_file, url_for
)
import re


def safe_filename(filename):
    """Sanitize a filename while preserving Unicode characters.

    Unlike werkzeug's secure_filename, this keeps Chinese and other non-ASCII
    characters intact. Only truly dangerous characters are removed/replaced.
    """
    # Strip path separators and null bytes
    name = filename.replace('\x00', '').replace('/', '_').replace('\\', '_')
    # Strip leading dots (hidden files) and whitespace
    name = name.lstrip('.').strip()
    # Keep only printable characters that aren't path separators
    name = re.sub(r'[\x00-\x1f\x7f]', '', name)
    return name or 'unnamed'

from src.config_manager import load_config, save_config
from src.exif_reader import read_exif
from src.border import calculate_border_custom, calculate_border_aspect_ratio
from src.image_processor import process_image, generate_preview

def _get_secret_key():
    """Get a persistent secret key shared across all workers.

    Priority: SECRET_KEY env var > key file on disk > generate and persist.
    """
    env_key = os.environ.get('SECRET_KEY')
    if env_key:
        return env_key

    key_file = os.path.join(BASE_DIR, '.secret_key')
    try:
        if os.path.exists(key_file):
            with open(key_file, 'r') as f:
                return f.read().strip()
    except Exception:
        pass

    new_key = 'exifborder-' + uuid.uuid4().hex
    try:
        with open(key_file, 'w') as f:
            f.write(new_key)
    except Exception:
        pass
    return new_key


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = _get_secret_key()
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'arw'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_session_dir():
    """Get or create a session-specific directory for uploaded files."""
    if 'session_id' not in session:
        session['session_id'] = uuid.uuid4().hex[:12]
    session_dir = os.path.join(UPLOADS_DIR, session['session_id'])
    os.makedirs(session_dir, exist_ok=True)
    return session_dir


def get_temp_dir():
    """Get or create a session-specific temp directory for previews."""
    if 'session_id' not in session:
        session['session_id'] = uuid.uuid4().hex[:12]
    temp_dir = os.path.join(TEMP_DIR, session['session_id'])
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def _resolve_logo_path(logo_path, session_dir):
    """Resolve a logo path to an absolute file path.

    Checks multiple locations in order:
    1. Absolute path that exists
    2. Relative to BASE_DIR (for built-in logos)
    3. Relative to session_dir (for user-uploaded logos)
    4. Falls back to session_dir join (preserves backward compat)
    """
    if not logo_path:
        return logo_path

    # Already absolute and exists
    if os.path.isabs(logo_path) and os.path.exists(logo_path):
        return logo_path

    # Try relative to BASE_DIR (static/logos/ etc.)
    base_relative = os.path.join(BASE_DIR, logo_path)
    if os.path.exists(base_relative):
        return base_relative

    # Try session_dir
    session_relative = os.path.join(session_dir, safe_filename(os.path.basename(logo_path)))
    if os.path.exists(session_relative):
        return session_relative

    # Fallback: return session_dir path for backward compat
    return session_relative


def get_image_metadata(image_path):
    """Get metadata for an uploaded image."""
    exif = read_exif(image_path)
    fname = os.path.basename(image_path)
    # Also read image dimensions
    img_w, img_h = 0, 0
    ext = fname.lower().rsplit('.', 1)[-1] if '.' in fname else ''
    if ext in ('jpg', 'jpeg'):
        from PIL import Image, ImageOps
        try:
            with ImageOps.exif_transpose(Image.open(image_path)) as im:
                img_w, img_h = im.size
        except Exception:
            pass
    elif ext == 'arw':
        try:
            import rawpy
            with rawpy.imread(image_path) as raw:
                img_w = raw.sizes.raw_width
                img_h = raw.sizes.raw_height
        except Exception:
            pass

    return {
        'filename': fname,
        'width': img_w,
        'height': img_h,
        'camera_make': exif.get('camera_make', ''),
        'camera_model': exif.get('camera_model', ''),
        'lens_make': exif.get('lens_make', ''),
        'lens_model': exif.get('lens_model', ''),
        'focal_length': exif.get('focal_length', ''),
        'aperture': exif.get('aperture', ''),
        'iso': exif.get('iso', ''),
        'exposure_time': exif.get('exposure_time', ''),
        'fnumber': exif.get('fnumber', ''),
        'datetime': exif.get('datetime', ''),
        'artist': exif.get('artist', ''),
        'software': exif.get('software', ''),
        'gps': exif.get('gps', ''),
        'all_tags': exif.get('all_tags', {}),
        'error': exif.get('error'),
    }


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route('/')
def step1():
    """Step 1: File selection and EXIF summary."""
    config = load_config()
    return render_template('step1.html', config=config, step=1)


@app.route('/step2')
def step2():
    """Step 2: Layout setup and preview."""
    config = load_config()
    session_dir = get_session_dir()
    images = []
    for fname in os.listdir(session_dir):
        if allowed_file(fname):
            fpath = os.path.join(session_dir, fname)
            images.append(get_image_metadata(fpath))
    return render_template('step2.html', config=config, images=images, step=2)


@app.route('/step3')
def step3():
    """Step 3: Review and download."""
    return render_template('step3.html', config=load_config(), step=3)


# ---------------------------------------------------------------------------
# API – Image Upload & EXIF
# ---------------------------------------------------------------------------

@app.route('/api/images', methods=['POST'])
def upload_images():
    """Upload one or more images and return their EXIF metadata."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    session_dir = get_session_dir()
    results = []

    for f in files:
        if f.filename == '':
            continue
        if not allowed_file(f.filename):
            continue
        filename = safe_filename(f.filename)
        filepath = os.path.join(session_dir, filename)
        f.save(filepath)
        results.append(get_image_metadata(filepath))

    return jsonify({'images': results})


@app.route('/api/images', methods=['GET'])
def list_images():
    """List all uploaded images with metadata."""
    session_dir = get_session_dir()
    images = []
    if os.path.exists(session_dir):
        for fname in sorted(os.listdir(session_dir)):
            if allowed_file(fname):
                fpath = os.path.join(session_dir, fname)
                images.append(get_image_metadata(fpath))
    return jsonify({'images': images})


@app.route('/api/images/<filename>/exif', methods=['GET'])
def get_image_exif(filename):
    """Get full EXIF data for a specific image."""
    session_dir = get_session_dir()
    safe_name = safe_filename(filename)
    filepath = os.path.join(session_dir, safe_name)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    exif = read_exif(filepath)
    return jsonify(exif)


@app.route('/api/images/<filename>', methods=['DELETE'])
def delete_image(filename):
    """Remove an uploaded image."""
    session_dir = get_session_dir()
    safe_name = safe_filename(filename)
    filepath = os.path.join(session_dir, safe_name)
    if os.path.exists(filepath):
        os.remove(filepath)
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# API – Preview Generation
# ---------------------------------------------------------------------------

@app.route('/api/preview', methods=['POST'])
def generate_preview_api():
    """Generate a preview image with current settings."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No config provided'}), 400

    filename = data.get('filename')
    border_cfg = data.get('border', {})
    logos_cfg = data.get('logos', [])
    text_lines = data.get('text_lines', data.get('text_elements', []))
    global_text_cfg = data.get('global_text', {})

    session_dir = get_session_dir()
    temp_dir = get_temp_dir()

    safe_name = safe_filename(filename)
    image_path = os.path.join(session_dir, safe_name)
    if not os.path.exists(image_path):
        return jsonify({'error': 'Image not found'}), 404

    # Resolve logo paths
    resolved_logos = []
    for logo in logos_cfg:
        logo_copy = dict(logo)
        logo_path = logo.get('path', '')
        if logo_path:
            logo_copy['path'] = _resolve_logo_path(logo_path, session_dir)
        resolved_logos.append(logo_copy)

    # Calculate border if using aspect ratio mode
    border_final = _resolve_border(border_cfg, image_path)

    # Read EXIF for text resolution
    exif = read_exif(image_path)

    try:
        preview = generate_preview(
            image_path, border_final, resolved_logos,
            text_lines, global_text_cfg, exif,
            max_dim=900
        )
        preview_id = uuid.uuid4().hex[:8]
        preview_path = os.path.join(temp_dir, f'preview_{preview_id}_{safe_name}')
        preview.save(preview_path, quality=85)
        return jsonify({
            'preview_url': f'/api/preview-image/{session["session_id"]}/preview_{preview_id}_{safe_name}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/preview-image/<session_id>/<filename>')
def serve_preview(session_id, filename):
    """Serve a generated preview image."""
    safe_name = safe_filename(filename)
    filepath = os.path.join(TEMP_DIR, session_id, safe_name)
    if not os.path.exists(filepath):
        # Fallback: try current session temp dir
        filepath = os.path.join(get_temp_dir(), safe_name)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Preview not found'}), 404
    return send_file(filepath, mimetype='image/jpeg')


def _resolve_border(border_cfg, image_path):
    """Calculate final border dimensions from config."""
    mode = border_cfg.get('mode', 'custom')
    color = border_cfg.get('color', '#FFFFFF')

    if mode == 'custom':
        result = calculate_border_custom(
            border_cfg.get('top', 0),
            border_cfg.get('bottom', 0),
            border_cfg.get('left', 0),
            border_cfg.get('right', 0),
        )
        result['color'] = color
        result['mode'] = 'custom'
        return result

    elif mode == 'aspect_ratio':
        from PIL import Image as PILImage, ImageOps
        with ImageOps.exif_transpose(PILImage.open(image_path)) as im:
            img_w, img_h = im.size

        auto_param = border_cfg.get('auto_param', 'c')
        a = border_cfg.get('a')
        b = border_cfg.get('b')
        c = border_cfg.get('c')

        try:
            result = calculate_border_aspect_ratio(img_w, img_h, auto_param, a, b, c)
            result['color'] = color
            result['mode'] = 'aspect_ratio'
            return result
        except ValueError:
            return {'top': 0, 'bottom': 0, 'left': 0, 'right': 0, 'color': color, 'mode': 'custom'}
    else:
        return {'top': 0, 'bottom': 0, 'left': 0, 'right': 0, 'color': color, 'mode': 'custom'}


# ---------------------------------------------------------------------------
# API – Logo Upload
# ---------------------------------------------------------------------------

@app.route('/api/logos', methods=['POST'])
def upload_logo():
    """Upload a logo file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    f = request.files['file']
    if f.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    allowed_logo = {'png', 'jpg', 'jpeg', 'svg'}
    ext = f.filename.rsplit('.', 1)[1].lower() if '.' in f.filename else ''
    if ext not in allowed_logo:
        return jsonify({'error': f'Unsupported format: {ext}'}), 400

    session_dir = get_session_dir()
    filename = safe_filename(f.filename)
    filepath = os.path.join(session_dir, filename)
    f.save(filepath)

    # Get dimensions
    from PIL import Image
    try:
        with Image.open(filepath) as im:
            w, h = im.size
    except Exception:
        w, h = 200, 60

    return jsonify({
        'filename': filename,
        'path': filename,
        'width': w,
        'height': h
    })


# ---------------------------------------------------------------------------
# API – Config Persistence
# ---------------------------------------------------------------------------

@app.route('/api/config', methods=['GET'])
def api_load_config():
    """Load saved configuration."""
    config = load_config()
    return jsonify(config)


@app.route('/api/config', methods=['POST'])
def api_save_config():
    """Save configuration."""
    data = request.get_json()
    if data:
        existing = load_config()
        for key in data:
            existing[key] = data[key]
        save_config(existing)
        return jsonify({'ok': True})
    return jsonify({'error': 'No data'}), 400


# ---------------------------------------------------------------------------
# API – Render & Download
# ---------------------------------------------------------------------------

@app.route('/api/render', methods=['POST'])
def render_images():
    """Render all images with current settings."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No config provided'}), 400

    border_cfg = data.get('border', {})
    logos_cfg = data.get('logos', [])
    text_lines = data.get('text_lines', data.get('text_elements', []))
    global_text_cfg = data.get('global_text', {})

    session_dir = get_session_dir()
    temp_dir = get_temp_dir()

    rendered = []
    for fname in sorted(os.listdir(session_dir)):
        if not allowed_file(fname):
            continue

        image_path = os.path.join(session_dir, fname)

        # Resolve logos
        resolved_logos = []
        for logo in logos_cfg:
            logo_copy = dict(logo)
            logo_path = logo.get('path', '')
            if logo_path:
                logo_copy['path'] = _resolve_logo_path(logo_path, session_dir)
            resolved_logos.append(logo_copy)

        border_final = _resolve_border(border_cfg, image_path)
        exif = read_exif(image_path)

        output_name = f'rendered_{fname}'
        output_path = os.path.join(temp_dir, output_name)

        try:
            process_image(
                image_path, border_final, resolved_logos,
                text_lines, global_text_cfg, exif,
                output_path=output_path
            )
            rendered.append({
                'filename': output_name,
                'original': fname,
                'download_url': f'/api/download/{session["session_id"]}/{output_name}'
            })
        except Exception as e:
            rendered.append({
                'filename': fname,
                'original': fname,
                'error': str(e)
            })

    return jsonify({'rendered': rendered})


@app.route('/api/download/<session_id>/<filename>')
def download_image(session_id, filename):
    """Download a rendered image."""
    safe_name = safe_filename(filename)
    filepath = os.path.join(TEMP_DIR, session_id, safe_name)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    return send_file(filepath, as_attachment=True, download_name=safe_name)


@app.route('/api/download-all/<session_id>')
def download_all(session_id):
    """Download all rendered images as a ZIP."""
    temp_dir_path = os.path.join(TEMP_DIR, session_id)
    if not os.path.exists(temp_dir_path):
        return jsonify({'error': 'No rendered images found'}), 404

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in sorted(os.listdir(temp_dir_path)):
            if fname.startswith('rendered_'):
                filepath = os.path.join(temp_dir_path, fname)
                zf.write(filepath, fname)
    zip_buf.seek(0)

    return send_file(
        zip_buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name='exifborder_output.zip'
    )


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    """Clean up session files."""
    session_dir = get_session_dir()
    temp_dir = get_temp_dir()
    for d in (session_dir, temp_dir):
        if os.path.exists(d):
            import shutil
            shutil.rmtree(d)
    session.clear()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    import webbrowser
    import threading

    host = '127.0.0.1'
    port = 5000

    # Open browser after a short delay
    def open_browser():
        time.sleep(1.0)
        webbrowser.open(f'http://{host}:{port}')

    threading.Thread(target=open_browser, daemon=True).start()

    print(f'\n  ExifBorder running at http://{host}:{port}\n')
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    main()
