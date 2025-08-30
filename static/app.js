// Elements
const drop = document.getElementById('drop');
const input = document.getElementById('file');
const fileList = document.getElementById('fileList');

const statusEl = document.getElementById('status');
const result = document.getElementById('result');
const singleResult = document.getElementById('singleResult');
const downloadLink = document.getElementById('downloadLink');
const btnInspectAfter = document.getElementById('btnInspectAfter');
const batchResult = document.getElementById('batchResult');
const zipLink = document.getElementById('zipLink');
const listEl = document.getElementById('list');

const btnInspect = document.getElementById('btnInspect');
const btnClean = document.getElementById('btnClean');
const btnReset = document.getElementById('btnReset');

const inspectPane = document.getElementById('inspectPane');
const inspectSelect = document.getElementById('inspectSelect');
const inspectBefore = document.getElementById('inspectBefore');
const inspectAfter = document.getElementById('inspectAfter');
const inspectDiff = document.getElementById('inspectDiff');
const wrapToggle = document.getElementById('wrapToggle');

// Tabs (for mobile)
const tabs = document.querySelectorAll('.tab');
const panels = {
  before: document.getElementById('panel-before'),
  after: document.getElementById('panel-after'),
  diff: document.getElementById('panel-diff'),
};

// ---------- State ----------
let selection = [];
let beforeReports = new Map(); // name -> text
let afterReports  = new Map(); // cleaned_name -> text
let lastCleaned = null;
let cleanedMap = new Map();    // orig -> cleaned_name

// ---------- Helpers ----------
function chooseFiles(){ input.click(); }

function fmtBytes(n){
  const u = ['B','KB','MB','GB']; let i=0; let x = n;
  while (x >= 1024 && i<u.length-1){ x/=1024; i++; }
  return `${x.toFixed(x<10&&i>0?1:0)} ${u[i]}`;
}

function inferKind(file){
  const ext = file.name.split('.').pop().toLowerCase();
  if (['jpg','jpeg','png','gif','tif','tiff','webp','bmp'].includes(ext)) return 'image';
  if (['mp4','mov','m4v','avi','mkv','webm'].includes(ext)) return 'video';
  if (ext === 'pdf') return 'pdf';
  if (['docx','xlsx'].includes(ext)) return 'doc';
  return 'other';
}

function iconFor(kind){
  if (kind === 'image') return '🖼️';
  if (kind === 'video') return '🎬';
  if (kind === 'pdf')   return '📄';
  if (kind === 'doc')   return '📑';
  return '📁';
}

function setButtonsEnabled(){
  const has = selection.length > 0;
  btnInspect.disabled = !has;
  btnClean.disabled   = !has;
  btnReset.disabled   = !has;
}

function revokeURLs(items){
  for (const s of items){
    if (s.url)   URL.revokeObjectURL(s.url);
  }
}

function renderFileList(){
  fileList.innerHTML = selection.map((s,i) => {
    const thumb = s.thumb
      ? `<img class="thumb${s.kind==='video' ? ' video play' : ''}" src="${s.thumb}" alt="">`
      : `<span class="thumb" aria-hidden="true" style="display:inline-grid;place-items:center;font-size:14px;">${iconFor(s.kind)}</span>`;
    return `
      <li class="filechip" data-idx="${i}">
        ${thumb}
        <span class="meta" title="${s.file.name} – ${fmtBytes(s.file.size)}">${s.file.name} • ${fmtBytes(s.file.size)}</span>
        <button class="remove" title="Remove" aria-label="Remove ${s.file.name}">&times;</button>
      </li>`;
  }).join('');
}

function clearUI(){
  result.classList.add('hidden');
  singleResult.classList.add('hidden');
  batchResult.classList.add('hidden');
  inspectPane.classList.add('hidden');
  listEl.innerHTML = '';
  downloadLink.removeAttribute('href');
  zipLink.removeAttribute('href');
  inspectBefore.textContent = '';
  inspectAfter.textContent = '';
  inspectDiff.textContent = '';
  beforeReports.clear();
  afterReports.clear();
  lastCleaned = null;
  cleanedMap.clear();
}

// ---------- Thumbnail generation ----------
async function buildThumb(item){
  if (item.kind === 'image'){
    item.url = URL.createObjectURL(item.file);
    item.thumb = item.url;
    return;
  }
  if (item.kind === 'video'){
    item.url = URL.createObjectURL(item.file);
    try{
      item.thumb = await captureVideoFrame(item.url);
    }catch{
      item.thumb = ''; 
    }
  }
}

function captureVideoFrame(objectURL){
  return new Promise((resolve, reject) => {
    const v = document.createElement('video');
    v.preload = 'metadata';
    v.muted = true; v.src = objectURL; v.crossOrigin = 'anonymous';

    const toImage = () => {
      const c = document.createElement('canvas');
      const w = 160, h = Math.max(90, Math.floor((v.videoHeight/v.videoWidth) * 160)) || 90;
      c.width = 160; c.height = h;
      const ctx = c.getContext('2d');
      ctx.drawImage(v, 0, 0, 160, h);
      try { resolve(c.toDataURL('image/jpeg', 0.7)); } catch(e){ reject(e); }
      v.pause(); v.src = ''; v.load();
    };

    v.addEventListener('loadedmetadata', () => {
      if (isNaN(v.duration) || v.duration === Infinity) { v.currentTime = 0; }
      else v.currentTime = Math.min(0.1, v.duration / 2);
    }, { once:true });

    v.addEventListener('seeked', toImage, { once:true });
    v.addEventListener('error', () => reject(new Error('video decode error')), { once:true });
  });
}

// ---------- Selection handling ----------
function setSelection(files){
  revokeURLs(selection); // Clean up old URLs
  selection.push(...files.map(f => ({ file: f, id: crypto.randomUUID(), kind: inferKind(f) }))); // Append new files
  renderFileList();
  statusEl.textContent = `${selection.length} file(s) selected.`;
  setButtonsEnabled();
  clearUI();
  input.value = ''; // allow reselecting same files later

  selection.forEach(async (item, idx) => {
    await buildThumb(item);
    const li = fileList.querySelector(`li[data-idx="${idx}"]`);
    if (li) renderFileList();
  });
}

fileList.addEventListener('click', (e) => {
  if (e.target.classList.contains('remove')){
    const li = e.target.closest('.filechip');
    const idx = Number(li.dataset.idx);
    revokeURLs([selection[idx]]);
    selection.splice(idx, 1);
    renderFileList();
    statusEl.textContent = `${selection.length} file(s) selected.`;
    setButtonsEnabled();
    if (selection.length === 0) clearUI();
  }
});

// ---------- Reset ----------
btnReset.addEventListener('click', () => {
  revokeURLs(selection);
  selection = [];
  renderFileList();
  setButtonsEnabled();
  clearUI();
  statusEl.textContent = 'Selection cleared.';
});

// ---------- Inspect (Before, After, Diff) ----------
function setTabs() {
  tabs.forEach(btn => {
    btn.classList.remove('active');
    const tab = btn.dataset.tab;
    if (tab === "before") {
      btn.classList.add('active');
      panels.before.classList.add('show');
      panels.after.classList.remove('show');
      panels.diff.classList.remove('show');
    } else if (tab === "after" && inspectAfter.textContent) {
      btn.classList.add('active');
      panels.before.classList.remove('show');
      panels.after.classList.add('show');
      panels.diff.classList.remove('show');
    } else if (tab === "diff" && inspectDiff.textContent) {
      btn.classList.add('active');
      panels.before.classList.remove('show');
      panels.after.classList.remove('show');
      panels.diff.classList.add('show');
    }
  });
}

// "Inspect Before" behavior
btnInspect.addEventListener('click', async () => {
  if (!selection.length) return;
  statusEl.textContent = `Inspecting ${selection.length} file(s) ...`;
  beforeReports.clear();

  // Fetch reports per file (and populate selector)
  inspectSelect.innerHTML = '';
  for (const s of selection) {
    const d = new FormData();
    d.append('upload', s.file);
    try {
      const res = await fetch('/inspect', { method: 'POST', body: d });
      const json = await res.json();
      beforeReports.set(s.file.name, json.report || '');
      const opt = document.createElement('option');
      opt.value = s.file.name;
      opt.textContent = s.file.name;
      inspectSelect.appendChild(opt);
    } catch (e) {
      beforeReports.set(s.file.name, `<inspect failed: ${e.message}>`);
    }
  }

  // Show first file’s report
  inspectBefore.textContent = beforeReports.get(inspectSelect.value) || '';
  inspectAfter.textContent = '';
  inspectDiff.textContent = ''; // Don't show Diff initially
  inspectPane.classList.remove('hidden');
  setTabs();
  statusEl.textContent = '';
});

// eta

let progressInterval;

function startProgressTimer() {
  let minutesRemaining = 5; // Example ETA, can be adjusted dynamically
  let progress = 0;
  statusEl.innerHTML = `⏳ Cleaning in progress... (${minutesRemaining} mins remaining)`;

  progressInterval = setInterval(() => {
    progress += 10;
    statusEl.innerHTML = `⏳ Cleaning... ${progress}% complete. ${minutesRemaining} min remaining`;

    if (progress >= 100) {
      clearInterval(progressInterval);
      statusEl.innerHTML = `✅ Cleaning complete!`;
    }

    minutesRemaining--;
    if (minutesRemaining < 1) {
      clearInterval(progressInterval);
      statusEl.innerHTML = `❌ Cleaning failed (timeout).`;
    }
  }, 60000); // Update every minute for ETA
}

function stopProgressTimer() {
  clearInterval(progressInterval);
}

btnClean.addEventListener('click', async () => {
  if (!selection.length) return;
  startProgressTimer();  // Start the progress animation
  statusEl.textContent = `Cleaning ${selection.length} file(s)...`;

  const data = new FormData();
  for (const s of selection) data.append('uploads', s.file);

  try {
    const res = await fetch('/clean-batch', { method: 'POST', body: data });
    if (!res.ok) throw new Error((await res.json()).detail || `Server error (${res.status})`);
    const json = await res.json();
    stopProgressTimer(); // Stop timer on completion

    cleanedMap.clear();
    if (json.items) {
      for (const it of json.items) cleanedMap.set(it.orig, it.cleaned_name);
    }

    // Handle single file/batch output as before
    if (json.download) {
      singleResult.classList.remove('hidden');
      batchResult.classList.add('hidden');
      downloadLink.href = json.download;
      downloadLink.setAttribute('download', json.suggested_filename || 'clean_file');
      result.classList.remove('hidden');
      statusEl.textContent = '';
    } else {
      batchResult.classList.remove('hidden');
      singleResult.classList.add('hidden');
      zipLink.href = json.zip_download;
      listEl.innerHTML = json.items.map(it =>
        `<div>• ${it.orig} → <a href="${it.download}">${it.cleaned_name}</a></div>`
      ).join('');
      result.classList.remove('hidden');
      statusEl.textContent = '';
    }
  } catch (err) {
    stopProgressTimer(); // Stop on error
    statusEl.textContent = `❌ ${err.message}`;
  }
});
