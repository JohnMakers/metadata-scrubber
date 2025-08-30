// ---------- Elements ----------
const dropZone = document.getElementById('drop');
const fileInput = document.getElementById('file-input');
const fileListEl = document.getElementById('file-list');
const statusEl = document.getElementById('status');

const btnInspect = document.getElementById('btn-inspect');
const btnClean = document.getElementById('btn-clean');
const btnReset = document.getElementById('btn-reset');

const outputSection = document.getElementById('output-section');
const resultDownloads = document.getElementById('result-downloads');
const singleResult = document.getElementById('single-result');
const batchResult = document.getElementById('batch-result');
const downloadLink = document.getElementById('download-link');
const zipLink = document.getElementById('zip-link');

const inspectPane = document.getElementById('inspect-pane');
const inspectSelect = document.getElementById('inspect-select');
const inspectBefore = document.getElementById('inspect-before');
const inspectAfter = document.getElementById('inspect-after');
const inspectDiff = document.getElementById('inspect-diff');
const wrapToggle = document.getElementById('wrap-toggle');
const tabs = document.querySelectorAll('.tab');
const panels = {
    before: document.getElementById('panel-before'),
    after: document.getElementById('panel-after'),
    diff: document.getElementById('panel-diff'),
};

// ---------- State ----------
let selection = [];
let beforeReports = new Map();
let afterReports = new Map();
let cleanedMap = new Map();
let hasCleaned = false; // **NEW**: Track cleaning status

// ---------- Helper Functions ----------
const fmtBytes = (n) => {
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    while (n >= 1024 && i < units.length - 1) {
        n /= 1024;
        i++;
    }
    return `${n.toFixed(n < 10 && i > 0 ? 1 : 0)} ${units[i]}`;
};

const inferKind = (file) => {
    const ext = file.name.split('.').pop().toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif', 'tif', 'tiff', 'webp', 'bmp'].includes(ext)) return 'image';
    if (['mp4', 'mov', 'm4v', 'avi', 'mkv', 'webm'].includes(ext)) return 'video';
    return 'other';
};

const iconFor = (kind) => (kind === 'image' ? '🖼️' : kind === 'video' ? '🎬' : '📁');

const revokeURLs = (items) => {
    items.forEach(item => {
        if (item.thumbUrl) URL.revokeObjectURL(item.thumbUrl);
    });
};

// ---------- Thumbnail Generation ----------
async function buildThumb(item) {
    if (item.kind === 'image') {
        item.thumbUrl = URL.createObjectURL(item.file);
        item.thumb = `<img class="thumb" src="${item.thumbUrl}" alt="preview">`;
    } else if (item.kind === 'video') {
        item.thumbUrl = URL.createObjectURL(item.file);
        try {
            const thumbDataUrl = await captureVideoFrame(item.thumbUrl);
            item.thumb = `<img class="thumb video" src="${thumbDataUrl}" alt="preview">`;
        } catch {
            item.thumb = `<span class="thumb">${iconFor(item.kind)}</span>`;
        }
    } else {
        item.thumb = `<span class="thumb">${iconFor(item.kind)}</span>`;
    }
}

function captureVideoFrame(objectURL) {
    return new Promise((resolve, reject) => {
        const video = document.createElement('video');
        video.preload = 'metadata';
        video.muted = true;
        video.src = objectURL;
        video.crossOrigin = 'anonymous';
        video.addEventListener('loadeddata', () => { video.currentTime = 0.1; }, { once: true });
        video.addEventListener('seeked', () => {
            const canvas = document.createElement('canvas');
            const aspectRatio = video.videoWidth / video.videoHeight;
            canvas.width = 80;
            canvas.height = 80 / aspectRatio;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            resolve(canvas.toDataURL('image/jpeg'));
            URL.revokeObjectURL(video.src);
        }, { once: true });
        video.addEventListener('error', (e) => reject(e), { once: true });
    });
}

// ---------- UI Update Functions ----------
const setButtonsEnabled = () => {
    const hasSelection = selection.length > 0;
    btnInspect.disabled = !hasSelection;
    btnClean.disabled = !hasSelection;
    btnReset.disabled = !hasSelection;
};

const clearUI = () => {
    outputSection.classList.add('hidden');
    resultDownloads.classList.add('hidden');
    inspectPane.classList.add('hidden');
    singleResult.classList.add('hidden');
    batchResult.classList.add('hidden');
    
    inspectBefore.textContent = '';
    inspectAfter.textContent = '';
    inspectDiff.textContent = '';
    inspectSelect.innerHTML = '';
    
    if (downloadLink.href) URL.revokeObjectURL(downloadLink.href);
    if (zipLink.href) URL.revokeObjectURL(zipLink.href);

    beforeReports.clear();
    afterReports.clear();
    cleanedMap.clear();
    hasCleaned = false; // Reset state

    btnInspect.textContent = 'Inspect Original';
};

const renderFileList = () => {
    fileListEl.innerHTML = selection.map((s, i) => `
        <li class="file-chip" data-idx="${i}">
            ${s.thumb || `<span class="thumb">${iconFor(s.kind)}</span>`}
            <span class="meta" title="${s.file.name}">${s.file.name} • ${fmtBytes(s.file.size)}</span>
            <button class="remove" title="Remove" aria-label="Remove ${s.file.name}">&times;</button>
        </li>`
    ).join('');
};

const updateInspectView = async (switchToTab = 'before') => {
    const selectedFile = inspectSelect.value;
    if (!selectedFile) return;

    if (beforeReports.size === 0) {
        statusEl.textContent = 'Fetching original reports...';
        await Promise.all(selection.map(async s => {
            const formData = new FormData();
            formData.append('upload', s.file);
            try {
                const res = await fetch('/inspect', { method: 'POST', body: formData });
                const json = await res.json();
                beforeReports.set(s.file.name, json.report || '');
            } catch (e) {
                beforeReports.set(s.file.name, `<Inspect failed: ${e.message}>`);
            }
        }));
        statusEl.textContent = '';
    }
    inspectBefore.textContent = beforeReports.get(selectedFile) || 'Report not available.';
    
    const cleanedName = cleanedMap.get(selectedFile);
    const afterTab = document.querySelector('.tab[data-tab="after"]');
    const diffTab = document.querySelector('.tab[data-tab="diff"]');

    if (cleanedName) {
        if (!afterReports.has(cleanedName)) {
            statusEl.textContent = `Fetching report for ${cleanedName}...`;
            try {
                const res = await fetch(`/inspect-output/${encodeURIComponent(cleanedName)}`);
                const json = await res.json();
                afterReports.set(cleanedName, json.report || 'Failed to load report.');
            } catch (e) {
                afterReports.set(cleanedName, `<Inspect failed: ${e.message}>`);
            }
            statusEl.textContent = '';
        }
        
        const beforeText = inspectBefore.textContent;
        const afterText = afterReports.get(cleanedName) || '';
        inspectAfter.textContent = afterText;
        generateDiff(beforeText, afterText);
        
        afterTab.disabled = false;
        diffTab.disabled = false;
    } else {
        inspectAfter.textContent = '';
        inspectDiff.textContent = '';
        afterTab.disabled = true;
        diffTab.disabled = true;
    }

    const targetTab = document.querySelector(`.tab[data-tab="${switchToTab}"]`);
    if (targetTab && !targetTab.disabled) {
        tabs.forEach(t => t.classList.remove('active'));
        targetTab.classList.add('active');
        Object.values(panels).forEach(p => p.classList.remove('show'));
        panels[switchToTab].classList.add('show');
    }
};

const generateDiff = (before, after) => {
    const beforeLines = new Set(before.split('\n'));
    const afterLines = new Set(after.split('\n'));
    let diffHtml = '';
    beforeLines.forEach(line => {
        if (line.trim() && !afterLines.has(line)) {
            diffHtml += `<span class="diff-line-removed">- ${line}</span>\n`;
        }
    });
    if (!diffHtml) diffHtml = 'No metadata was removed.';
    inspectDiff.innerHTML = diffHtml;
};

// ---------- File Selection & Handling ----------
const handleFiles = (files) => {
    clearUI();
    const newItems = [...files].map(file => ({ 
        file, id: crypto.randomUUID(), kind: inferKind(file),
        thumb: `<span class="thumb">${iconFor(inferKind(file))}</span>`
    }));
    selection.push(...newItems);
    renderFileList();
    statusEl.textContent = `${selection.length} file(s) selected.`;
    setButtonsEnabled();
    fileInput.value = '';
    newItems.forEach(async (item) => {
        await buildThumb(item);
        renderFileList();
    });
};

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
});
fileInput.addEventListener('change', () => { if (fileInput.files.length) handleFiles(fileInput.files); });
fileListEl.addEventListener('click', (e) => {
    if (e.target.classList.contains('remove')) {
        const idx = Number(e.target.closest('.file-chip').dataset.idx);
        revokeURLs([selection[idx]]);
        selection.splice(idx, 1);
        renderFileList();
        statusEl.textContent = `${selection.length} file(s) selected.`;
        setButtonsEnabled();
        if (selection.length === 0) {
            clearUI();
            statusEl.textContent = 'No files selected.';
        }
    }
});

// ---------- Action Button Handlers ----------
btnReset.addEventListener('click', () => {
    revokeURLs(selection);
    selection = [];
    renderFileList();
    setButtonsEnabled();
    clearUI();
    statusEl.textContent = 'No files selected.';
});

btnInspect.addEventListener('click', async () => {
    if (!selection.length) return;
    statusEl.textContent = 'Inspecting files...';
    btnInspect.disabled = true;

    // Populate the dropdown if it's empty
    if (inspectSelect.options.length === 0) {
        selection.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.file.name;
            opt.textContent = s.file.name;
            inspectSelect.appendChild(opt);
        });
    }

    // Always show downloads if they exist
    if (hasCleaned) {
        resultDownloads.classList.remove('hidden');
    } else {
        resultDownloads.classList.add('hidden');
    }

    outputSection.classList.remove('hidden');
    inspectPane.classList.remove('hidden');
    
    // Switch to diff tab if cleaned, otherwise before
    await updateInspectView(hasCleaned ? 'diff' : 'before');
    
    statusEl.textContent = 'Inspection complete.';
    btnInspect.disabled = false;
});

btnClean.addEventListener('click', async () => {
    if (selection.length === 0) return;
    statusEl.textContent = `Cleaning ${selection.length} file(s)...`;
    btnClean.disabled = true;

    const formData = new FormData();
    selection.forEach(s => formData.append('uploads', s.file));
    
    try {
        const response = await fetch('/clean-batch', { method: 'POST', body: formData });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || `Server error: ${response.statusText}`);
        }
        
        const result = await response.json();
        result.items.forEach(item => cleanedMap.set(item.orig, item.cleaned_name));

        // **FIX**: Correctly show single vs. batch download links
        if (selection.length > 1) {
            zipLink.href = result.zip_download;
            zipLink.download = result.zip_download.split('/').pop();
            singleResult.classList.add('hidden');
            batchResult.classList.remove('hidden');
        } else {
            downloadLink.href = result.download;
            downloadLink.download = result.suggested_filename;
            singleResult.classList.remove('hidden');
            batchResult.classList.add('hidden');
        }
        
        outputSection.classList.remove('hidden');
        resultDownloads.classList.remove('hidden');
        inspectPane.classList.add('hidden'); // Hide inspect by default after cleaning

        hasCleaned = true; // **FIX**: Set clean status
        btnInspect.textContent = 'Inspect Results'; // **FIX**: Update button text

        statusEl.textContent = 'Cleaning complete!';

    } catch (error) {
        statusEl.textContent = `Error: ${error.message}`;
    } finally {
        btnClean.disabled = false;
    }
});

// ---------- Inspect Panel Event Listeners ----------
inspectSelect.addEventListener('change', () => updateInspectView(hasCleaned ? 'diff' : 'before'));

tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        if (tab.disabled) return;
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        Object.values(panels).forEach(p => p.classList.remove('show'));
        panels[tab.dataset.tab].classList.add('show');
    });
});

wrapToggle.addEventListener('change', () => {
    document.querySelectorAll('.panel pre').forEach(pre => {
        pre.classList.toggle('wrap', wrapToggle.checked);
    });
});
