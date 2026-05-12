/* Step 3: Review and download */

let renderedImages = [];
let currentSessionId = '';

document.addEventListener('DOMContentLoaded', async () => {
    await loadImagesForReview();
});

async function loadImagesForReview() {
    try {
        const resp = await fetch('/api/images');
        const data = await resp.json();
        const grid = document.getElementById('reviewGrid');
        grid.innerHTML = '';

        if (!data.images || data.images.length === 0) {
            grid.innerHTML = '<p style="color:#888;">No images uploaded. Go back to Step 1 to select images.</p>';
            document.getElementById('btnRender').disabled = true;
            return;
        }

        for (const img of data.images) {
            const card = document.createElement('div');
            card.className = 'review-card';
            card.id = 'card-' + img.filename.replace(/[^a-zA-Z0-9]/g, '_');
            card.innerHTML = `
                <div style="background:#f5f5f5; min-height:150px; display:flex; align-items:center; justify-content:center; border-radius:4px; color:#aaa; font-size:0.9rem;">
                    Pending render
                </div>
                <div class="info">
                    <strong>${esc(img.filename)}</strong><br>
                    ${img.width}×${img.height} | ${esc(img.camera_model || '—')}<br>
                    ${esc(img.lens_model || '')} ${esc(img.focal_length || '')} ${esc(img.aperture || '')}
                </div>
            `;
            grid.appendChild(card);
        }
    } catch (e) {
        console.error('Failed to load images', e);
    }
}

async function renderAll() {
    const btnRender = document.getElementById('btnRender');
    const btnDownloadAll = document.getElementById('btnDownloadAll');
    const progressBar = document.getElementById('progressBar');
    const progressFill = document.getElementById('progressFill');
    const statusMsg = document.getElementById('statusMsg');

    btnRender.disabled = true;
    progressBar.style.display = 'block';
    progressFill.style.width = '10%';
    statusMsg.textContent = 'Loading configuration...';

    // Load config
    let config;
    try {
        const resp = await fetch('/api/config');
        config = await resp.json();
    } catch (e) {
        statusMsg.textContent = 'Failed to load config.';
        btnRender.disabled = false;
        return;
    }

    progressFill.style.width = '20%';
    statusMsg.textContent = 'Rendering images...';

    const payload = {
        border: config.border || {},
        logos: config.logos || [],
        text_lines: config.text_lines || [],
        global_text: {
            line_spacing: config.line_spacing || 1.3,
            text_margin_left: config.text_margin_left || 40,
            text_margin_right: config.text_margin_right || 40,
            text_margin_bottom: config.text_margin_bottom || 30,
            text_lines_spacing: config.text_lines_spacing || 8,
        }
    };

    try {
        const resp = await fetch('/api/render', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json();
        renderedImages = data.rendered || [];

        progressFill.style.width = '100%';

        if (renderedImages.length === 0) {
            statusMsg.textContent = 'No images were rendered.';
            btnRender.disabled = false;
            progressBar.style.display = 'none';
            return;
        }

        statusMsg.textContent = `Rendered ${renderedImages.length} image(s).`;

        // Update review grid
        const grid = document.getElementById('reviewGrid');
        grid.innerHTML = '';

        for (const img of renderedImages) {
            const card = document.createElement('div');
            card.className = 'review-card';
            if (img.error) {
                card.innerHTML = `
                    <div style="color:#e74c3c; padding:20px; text-align:center;">
                        Error: ${esc(img.error)}
                    </div>
                    <div class="info"><strong>${esc(img.original)}</strong></div>
                `;
            } else {
                card.innerHTML = `
                    <img src="${img.download_url}" alt="${esc(img.original)}" loading="lazy">
                    <div class="info">
                        <strong>${esc(img.original)}</strong>
                        <br>
                        <a href="${img.download_url}" class="download-btn" download>Download</a>
                    </div>
                `;
            }
            grid.appendChild(card);
        }

        btnDownloadAll.style.display = 'inline-block';
        btnRender.disabled = false;
        progressBar.style.display = 'none';

    } catch (err) {
        statusMsg.textContent = 'Render failed: ' + err.message;
        btnRender.disabled = false;
        progressBar.style.display = 'none';
    }
}

function downloadAll() {
    // Extract session ID from the first download URL
    if (renderedImages.length > 0 && renderedImages[0].download_url) {
        const match = renderedImages[0].download_url.match(/\/api\/download\/([^/]+)\//);
        if (match) {
            window.location.href = `/api/download-all/${match[1]}`;
            return;
        }
    }
    // Fallback
    alert('Please render images first.');
}

function esc(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
