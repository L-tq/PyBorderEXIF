/* Step 2: Layout setup and preview */

let config = null;
let images = [];
let previewTimer = null;
let availableExifTags = [];

const COMMON_EXIF_TAGS = [
    'Camera Make', 'Camera Model', 'Lens Make', 'Lens Model',
    'Focal Length', 'Aperture', 'ISO', 'Exposure Time', 'F-Number',
    'Date/Time', 'Artist', 'Software', 'GPS'
];

const FONT_FAMILIES = ['Roboto', 'Source Han Sans'];
const FONT_WEIGHTS = ['normal', 'bold', 'thin', 'light', 'medium'];
const FONT_STYLES = ['normal', 'italic'];

// --- Init ---
document.addEventListener('DOMContentLoaded', async () => {
    await loadConfig();
    await loadImages();
    populateImageSelector();
    initBorderMode();
    renderLogos();
    renderTextLines();
});

async function loadConfig() {
    try {
        const resp = await fetch('/api/config');
        config = await resp.json();
        // Migrate old format if needed
        if (!config.text_lines && config.text_elements) {
            config.text_lines = migrateOldElements(config.text_elements);
        }
        // Migrate old line-level font settings to per-part format
        if (config.text_lines) {
            config.text_lines = config.text_lines.map(migrateTextLine);
        }
    } catch (e) {
        console.error('Failed to load config', e);
    }
}

async function loadImages() {
    try {
        const resp = await fetch('/api/images');
        const data = await resp.json();
        images = data.images || [];
        const tagSet = new Set(COMMON_EXIF_TAGS);
        for (const img of images) {
            if (img.all_tags) {
                Object.keys(img.all_tags).forEach(t => tagSet.add(t));
            }
        }
        availableExifTags = Array.from(tagSet).sort();
    } catch (e) {
        console.error('Failed to load images', e);
    }
}

function migrateOldElements(elements) {
    // Convert old text_elements to new text_lines format
    const sorted = [...elements].sort((a, b) => (a.order || 0) - (b.order || 0));
    const lines = [];
    for (const elem of sorted) {
        if (!elem.visible) continue;
        let text = elem.value || '';
        if (!text && elem.label) {
            text = '{' + elem.label + '}';
        }
        const part = {
            text: text,
            font_family: elem.font_family || 'Roboto',
            font_size: elem.font_size || 22,
            font_color: elem.font_color || '#333333',
            font_weight: elem.font_weight || 'normal',
            font_style: elem.font_style || 'normal',
        };
        lines.push({
            left: { ...part, text: text },
            center: { ...part, text: '' },
            right: { ...part, text: '' },
        });
    }
    return lines.length > 0 ? lines : null;
}

function migrateTextLine(line) {
    // Convert old-format line (string parts + line-level font) to new format
    // where each part is an object with its own font settings.
    if (line.left !== null && line.left !== undefined && typeof line.left === 'object') {
        return line;
    }
    const defaults = {
        font_family: line.font_family || 'Roboto',
        font_size: line.font_size || 22,
        font_color: line.font_color || '#333333',
        font_weight: line.font_weight || 'normal',
        font_style: line.font_style || 'normal',
    };
    return {
        left: { text: line.left || '', ...defaults },
        center: { text: line.center || '', ...defaults },
        right: { text: line.right || '', ...defaults },
    };
}

// --- Border ---
function initBorderMode() {
    if (!config || !config.border) return;
    const b = config.border;
    const mode = b.mode || 'custom';
    const radio = document.querySelector(`input[name="borderMode"][value="${mode}"]`);
    if (radio) radio.checked = true;

    document.getElementById('borderTop').value = (b.top != null) ? b.top : 100;
    document.getElementById('borderBottom').value = (b.bottom != null) ? b.bottom : 200;
    document.getElementById('borderLeft').value = (b.left != null) ? b.left : 80;
    document.getElementById('borderRight').value = (b.right != null) ? b.right : 80;
    document.getElementById('borderColor').value = b.color || '#FFFFFF';
    document.getElementById('autoParam').value = b.auto_param || 'c';
    document.getElementById('aspectA').value = (b.a != null) ? b.a : ((b.left != null) ? b.left : 80);
    document.getElementById('aspectB').value = (b.b != null) ? b.b : ((b.top != null) ? b.top : 100);
    document.getElementById('aspectC').value = (b.c != null) ? b.c : ((b.bottom != null) ? b.bottom : 200);

    document.getElementById('lineSpacing').value = config.line_spacing || 1.3;
    document.getElementById('textMarginLeft').value = config.text_margin_left || 40;
    document.getElementById('textMarginRight').value = config.text_margin_right || 40;
    document.getElementById('textMarginBottom').value = config.text_margin_bottom || 30;
    document.getElementById('linesGap').value = config.text_lines_spacing || 8;

    onBorderModeChange();
}

function onBorderModeChange() {
    const mode = document.querySelector('input[name="borderMode"]:checked').value;
    document.getElementById('borderCustom').style.display = mode === 'custom' ? 'block' : 'none';
    document.getElementById('borderAspect').style.display = mode === 'aspect_ratio' ? 'block' : 'none';
    config.border.mode = mode;
    updateAutoParamState();
    debouncePreview();
}

function updateAutoParamState() {
    const autoParam = document.getElementById('autoParam').value;
    document.getElementById('aspectA').disabled = autoParam === 'a';
    document.getElementById('aspectB').disabled = autoParam === 'b';
    document.getElementById('aspectC').disabled = autoParam === 'c';
}

document.getElementById('autoParam').addEventListener('change', () => {
    updateAutoParamState();
    debouncePreview();
});

// --- Logos ---
function renderLogos() {
    const container = document.getElementById('logosList');
    const logos = config?.logos || [];
    container.innerHTML = '';

    logos.forEach((logo, idx) => {
        const div = document.createElement('div');
        div.className = 'logo-item';
        div.innerHTML = [
            '<div class="logo-header">',
            `<span class="logo-name">Logo ${idx + 1}: ${esc(logo.filename || '—')}</span>`,
            `<button class="btn-danger btn-xs" onclick="removeLogo(${idx})">✕</button>`,
            '</div>',
            `<div class="te-row"><label>File</label><span style="font-size:0.8rem;">${esc(logo.filename || '')}</span></div>`,
            `<div class="te-row"><label>Width</label><input type="number" value="${logo.width || 200}" min="10" onchange="updateLogo(${idx},'width',this.value)"></div>`,
            `<div class="te-row"><label>Height</label><input type="number" value="${logo.height || 60}" min="10" onchange="updateLogo(${idx},'height',this.value)"></div>`,
            `<div class="te-row"><label>rel_x</label><input type="number" value="${logo.rel_x || 0}" step="0.01" min="0" max="1" onchange="updateLogo(${idx},'rel_x',this.value)"></div>`,
            `<div class="te-row"><label>rel_y</label><input type="number" value="${logo.rel_y || 0}" step="0.01" min="0" max="1" onchange="updateLogo(${idx},'rel_y',this.value)"></div>`,
            `<div class="te-row"><label>offset_x</label><input type="number" value="${logo.offset_x || 0}" onchange="updateLogo(${idx},'offset_x',this.value)"></div>`,
            `<div class="te-row"><label>offset_y</label><input type="number" value="${logo.offset_y || 0}" onchange="updateLogo(${idx},'offset_y',this.value)"></div>`,
        ].join('');
        container.appendChild(div);
    });
}

function addLogo() {
    const input = document.getElementById('logoFileInput');
    input.click();
    input.onchange = async () => {
        if (!input.files.length) return;
        const formData = new FormData();
        formData.append('file', input.files[0]);
        try {
            const resp = await fetch('/api/logos', { method: 'POST', body: formData });
            const data = await resp.json();
            if (data.error) { alert(data.error); return; }
            if (!config.logos) config.logos = [];
            config.logos.push({
                filename: data.filename, path: data.path,
                width: data.width, height: data.height,
                rel_x: 0.05, rel_y: 0.05, offset_x: 0, offset_y: 0
            });
            await saveConfig();
            renderLogos();
            debouncePreview();
        } catch (err) {
            alert('Logo upload failed: ' + err.message);
        }
        input.value = '';
    };
}

function updateLogo(idx, field, value) {
    config.logos[idx][field] = field.includes('rel') ? parseFloat(value) : parseInt(value) || 0;
    saveConfig();
    debouncePreview();
}

function removeLogo(idx) {
    config.logos.splice(idx, 1);
    saveConfig();
    renderLogos();
    debouncePreview();
}

// --- Text Lines ---
function renderTextLines() {
    const container = document.getElementById('textLinesList');
    const lines = config?.text_lines || [];
    container.innerHTML = '';

    lines.forEach((line, idx) => {
        const div = document.createElement('div');
        div.className = 'text-line';
        div.draggable = true;
        div.dataset.idx = idx;

        div.innerHTML = [
            '<div class="tl-header">',
            `<span class="tl-name">Line ${idx + 1}</span>`,
            `<button class="btn-danger btn-xs" onclick="event.stopPropagation(); removeTextLine(${idx})">✕</button>`,
            '</div>',
            '<div class="tl-parts">',
            _renderPart(idx, 'left', line.left),
            _renderPart(idx, 'center', line.center),
            _renderPart(idx, 'right', line.right),
            '</div>',
            '<div class="tl-tag-hint">',
            '<span style="font-size:0.72rem; color:#888;">Insert tag into </span>',
            `<select id="tl_part_sel_${idx}" style="font-size:0.72rem; padding:1px 2px; border:1px solid #ddd; border-radius:3px;">`,
            '<option value="left">Left</option><option value="center">Center</option><option value="right">Right</option>',
            '</select>',
            '<span style="font-size:0.72rem; color:#888;">: </span>',
            COMMON_EXIF_TAGS.slice(0, 8).map(t =>
                `<span onclick="insertTag(${idx},document.getElementById('tl_part_sel_${idx}').value,'${esc(t)}')" title="Insert tag">${esc(t)}</span>`
            ).join(' · '),
            '</div>',
        ].join('');

        // Drag events
        div.addEventListener('dragstart', onDragStart);
        div.addEventListener('dragover', onDragOver);
        div.addEventListener('drop', onDrop);
        div.addEventListener('dragend', onDragEnd);

        container.appendChild(div);
    });
}

function _renderPart(idx, name, part) {
    const p = (part && typeof part === 'object') ? part : { text: part || '' };
    const text = esc(p.text || '');
    const family = p.font_family || 'Roboto';
    const weight = p.font_weight || 'normal';
    const style = p.font_style || 'normal';
    const size = p.font_size || 22;
    const color = p.font_color || '#333333';

    const familyOpts = FONT_FAMILIES.map(f =>
        `<option value="${f}" ${family === f ? 'selected' : ''}>${f}</option>`
    ).join('');
    const weightOpts = FONT_WEIGHTS.map(w =>
        `<option value="${w}" ${weight === w ? 'selected' : ''}>${w}</option>`
    ).join('');
    const styleOpts = FONT_STYLES.map(s =>
        `<option value="${s}" ${style === s ? 'selected' : ''}>${s}</option>`
    ).join('');

    const capName = name.charAt(0).toUpperCase() + name.slice(1);
    return [
        `<div class="tl-part">`,
        `<label>${capName}</label>`,
        `<input type="text" value="${text}" onchange="updatePartText(${idx},'${name}',this.value)" id="tl_${name}_${idx}">`,
        `<div class="tl-part-font">`,
        `<select onchange="updatePartFont(${idx},'${name}','font_family',this.value)">${familyOpts}</select>`,
        `<select onchange="updatePartFont(${idx},'${name}','font_weight',this.value)">${weightOpts}</select>`,
        `<select onchange="updatePartFont(${idx},'${name}','font_style',this.value)">${styleOpts}</select>`,
        `<input type="number" value="${size}" min="8" max="200" onchange="updatePartFont(${idx},'${name}','font_size',this.value)">`,
        `<input type="color" value="${color}" onchange="updatePartFont(${idx},'${name}','font_color',this.value)">`,
        `</div>`,
        `</div>`,
    ].join('');
}

function addTextLine() {
    if (!config.text_lines) config.text_lines = [];
    const defaultPart = {
        text: '',
        font_family: 'Roboto',
        font_size: 20,
        font_color: '#777777',
        font_weight: 'normal',
        font_style: 'normal',
    };
    config.text_lines.push({
        left: { ...defaultPart },
        center: { ...defaultPart },
        right: { ...defaultPart },
    });
    saveConfig();
    renderTextLines();
    debouncePreview();
}

function removeTextLine(idx) {
    config.text_lines.splice(idx, 1);
    saveConfig();
    renderTextLines();
    debouncePreview();
}

function updatePartText(idx, part, value) {
    if (typeof config.text_lines[idx][part] !== 'object') {
        config.text_lines[idx][part] = { text: '' };
    }
    config.text_lines[idx][part].text = value;
    saveConfig();
    debouncePreview();
}

function updatePartFont(idx, part, field, value) {
    const numFields = ['font_size'];
    if (typeof config.text_lines[idx][part] !== 'object') {
        config.text_lines[idx][part] = { text: config.text_lines[idx][part] || '' };
    }
    config.text_lines[idx][part][field] = numFields.includes(field) ? (parseInt(value) || 18) : value;
    saveConfig();
    debouncePreview();
}

function insertTag(idx, part, tagName) {
    const inputId = `tl_${part}_${idx}`;
    const input = document.getElementById(inputId);
    if (!input) return;

    const tagPlaceholder = '{' + tagName + '}';
    const cursorPos = input.selectionStart || input.value.length;
    const before = input.value.substring(0, cursorPos);
    const after = input.value.substring(cursorPos);
    input.value = before + tagPlaceholder + after;
    input.focus();
    input.selectionStart = input.selectionEnd = cursorPos + tagPlaceholder.length;

    if (typeof config.text_lines[idx][part] !== 'object') {
        config.text_lines[idx][part] = { text: '' };
    }
    config.text_lines[idx][part].text = input.value;
    saveConfig();
    debouncePreview();
}

// --- Drag & Drop for Text Lines ---
let dragIdx = null;

function onDragStart(e) {
    dragIdx = parseInt(e.target.closest('.text-line').dataset.idx);
    e.target.closest('.text-line').classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
}

function onDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
}

function onDrop(e) {
    e.preventDefault();
    const target = e.target.closest('.text-line');
    if (!target || dragIdx === null) return;
    const dropIdx = parseInt(target.dataset.idx);
    if (dragIdx !== dropIdx) {
        const moved = config.text_lines.splice(dragIdx, 1)[0];
        config.text_lines.splice(dropIdx, 0, moved);
        saveConfig();
        renderTextLines();
        debouncePreview();
    }
    dragIdx = null;
}

function onDragEnd(e) {
    const el = e.target.closest('.text-line');
    if (el) el.classList.remove('dragging');
}

// --- Preview ---
function populateImageSelector() {
    const select = document.getElementById('previewImageSelect');
    select.innerHTML = images.map((img, i) =>
        `<option value="${esc(img.filename)}" ${i === 0 ? 'selected' : ''}>${esc(img.filename)}</option>`
    ).join('');
    if (images.length > 0) {
        setTimeout(() => debouncePreview(), 200);
    }
}

function getCurrentBorderConfig() {
    const mode = document.querySelector('input[name="borderMode"]:checked')?.value || 'custom';
    const top = parseInt(document.getElementById('borderTop').value);
    const bottom = parseInt(document.getElementById('borderBottom').value);
    const left = parseInt(document.getElementById('borderLeft').value);
    const right = parseInt(document.getElementById('borderRight').value);
    const a = parseInt(document.getElementById('aspectA').value);
    const b = parseInt(document.getElementById('aspectB').value);
    const c = parseInt(document.getElementById('aspectC').value);
    return {
        mode: mode,
        top: isNaN(top) ? 0 : top,
        bottom: isNaN(bottom) ? 0 : bottom,
        left: isNaN(left) ? 0 : left,
        right: isNaN(right) ? 0 : right,
        color: document.getElementById('borderColor').value,
        auto_param: document.getElementById('autoParam').value,
        a: isNaN(a) ? 0 : a,
        b: isNaN(b) ? 0 : b,
        c: isNaN(c) ? 0 : c,
    };
}

function getGlobalTextConfig() {
    return {
        line_spacing: parseFloat(document.getElementById('lineSpacing').value) || 1.3,
        text_margin_left: parseInt(document.getElementById('textMarginLeft').value) || 0,
        text_margin_right: parseInt(document.getElementById('textMarginRight').value) || 0,
        text_margin_bottom: parseInt(document.getElementById('textMarginBottom').value) || 0,
        text_lines_spacing: parseInt(document.getElementById('linesGap').value) || 8,
    };
}

function debouncePreview() {
    if (previewTimer) clearTimeout(previewTimer);
    previewTimer = setTimeout(() => {
        saveConfig();
        generatePreview();
    }, 400);
}

async function generatePreview() {
    const select = document.getElementById('previewImageSelect');
    const filename = select?.value;
    if (!filename) return;

    const payload = {
        filename: filename,
        border: getCurrentBorderConfig(),
        logos: config?.logos || [],
        text_lines: config?.text_lines || [],
        global_text: getGlobalTextConfig()
    };

    try {
        const resp = await fetch('/api/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json();
        if (data.error) {
            console.error('Preview error:', data.error);
            return;
        }
        const previewImg = document.getElementById('previewImage');
        const placeholder = document.getElementById('previewPlaceholder');
        previewImg.src = data.preview_url + '?t=' + Date.now();
        previewImg.style.display = 'block';
        placeholder.style.display = 'none';
    } catch (err) {
        console.error('Preview failed:', err);
    }
}

// --- Helpers ---
function _intVal(id, fallback) {
    const v = parseInt(document.getElementById(id).value);
    return isNaN(v) ? fallback : v;
}
function _floatVal(id, fallback) {
    const v = parseFloat(document.getElementById(id).value);
    return isNaN(v) ? fallback : v;
}

// --- Navigation ---
async function saveConfig() {
    try {
        if (!config.border) config.border = {};
        Object.assign(config.border, getCurrentBorderConfig());
        config.line_spacing = _floatVal('lineSpacing', 1.3);
        config.text_margin_left = _intVal('textMarginLeft', 40);
        config.text_margin_right = _intVal('textMarginRight', 40);
        config.text_margin_bottom = _intVal('textMarginBottom', 30);
        config.text_lines_spacing = _intVal('linesGap', 8);

        await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
    } catch (e) {
        console.error('Failed to save config', e);
    }
}

function goToStep3() {
    saveConfig().then(() => {
        window.location.href = '/step3';
    });
}

function esc(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
