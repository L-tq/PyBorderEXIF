/* Step 1: File selection and EXIF summary */

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const tableWrapper = document.getElementById('tableWrapper');
const tableBody = document.getElementById('imagesTableBody');
const imageCount = document.getElementById('imageCount');
const exifDetail = document.getElementById('exifDetail');
const exifDetailName = document.getElementById('exifDetailName');
const exifDetailContent = document.getElementById('exifDetailContent');
const btnNext = document.getElementById('btnNext');

let uploadedImages = [];

// Drop zone click
dropZone.addEventListener('click', () => fileInput.click());

// Drag & drop
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
        uploadFiles(e.dataTransfer.files);
    }
});

// File input change
fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
        uploadFiles(fileInput.files);
    }
});

async function uploadFiles(fileList) {
    const formData = new FormData();
    for (const f of fileList) {
        formData.append('files', f);
    }

    dropZone.textContent = 'Uploading...';

    try {
        const resp = await fetch('/api/images', { method: 'POST', body: formData });
        const data = await resp.json();
        if (data.images) {
            uploadedImages = data.images;
            renderTable();
        }
    } catch (err) {
        alert('Upload failed: ' + err.message);
    } finally {
        dropZone.innerHTML = '<h2>Drop images here</h2><p>or click to browse — JPEG, ARW supported</p>';
    }
}

function renderTable() {
    tableBody.innerHTML = '';
    if (uploadedImages.length === 0) {
        tableWrapper.style.display = 'none';
        btnNext.disabled = true;
        return;
    }

    tableWrapper.style.display = 'block';
    btnNext.disabled = false;
    imageCount.textContent = uploadedImages.length + ' image(s) loaded';

    for (const img of uploadedImages) {
        const tr = document.createElement('tr');
        tr.innerHTML = [
            `<td><strong>${esc(img.filename)}</strong></td>`,
            `<td>${img.width}×${img.height}</td>`,
            `<td>${esc(img.camera_model || '—')}</td>`,
            `<td>${esc(img.lens_model || '—')}</td>`,
            `<td>${esc(img.focal_length || '—')}</td>`,
            `<td>${esc(img.aperture || '—')}</td>`,
            `<td>${esc(img.iso || '—')}</td>`,
            `<td>${esc(img.exposure_time || '—')}</td>`,
            `<td>
                <button class="btn-danger" onclick="deleteImage('${esc(img.filename)}')">✕</button>
                <button class="btn btn-sm btn-secondary" style="margin-left:4px;" onclick="showExif('${esc(img.filename)}')">EXIF</button>
            </td>`,
        ].join('');
        tableBody.appendChild(tr);
    }
}

async function deleteImage(filename) {
    try {
        await fetch(`/api/images/${encodeURIComponent(filename)}`, { method: 'DELETE' });
        uploadedImages = uploadedImages.filter(i => i.filename !== filename);
        renderTable();
    } catch (err) {
        alert('Failed to delete: ' + err.message);
    }
}

async function showExif(filename) {
    try {
        const resp = await fetch(`/api/images/${encodeURIComponent(filename)}/exif`);
        const data = await resp.json();
        exifDetailName.textContent = filename;
        exifDetailContent.innerHTML = renderExifTable(data.all_tags || {});
        exifDetail.style.display = 'block';
    } catch (err) {
        alert('Failed to load EXIF: ' + err.message);
    }
}

function renderExifTable(tags) {
    const rows = Object.entries(tags).map(([k, v]) =>
        `<tr><td>${esc(String(k))}</td><td>${esc(String(v))}</td></tr>`
    ).join('');
    return `<table>${rows}</table>`;
}

function clearAll() {
    for (const img of uploadedImages) {
        fetch(`/api/images/${encodeURIComponent(img.filename)}`, { method: 'DELETE' }).catch(()=>{});
    }
    uploadedImages = [];
    renderTable();
}

function esc(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
