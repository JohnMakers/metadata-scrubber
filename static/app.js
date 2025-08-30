const drop = document.getElementById('drop');
const input = document.getElementById('file');
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

const inspectPane = document.getElementById('inspectPane');
const inspectBefore = document.getElementById('inspectBefore');
const inspectAfter = document.getElementById('inspectAfter');
const inspectDiff = document.getElementById('inspectDiff');

let selection = [];     // File[] currently selected
let lastCleaned = null; // { download, suggested_filename, items, zip_download }

function chooseFiles(){ input.click(); }
drop.addEventListener('click', chooseFiles);

drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('dragover'); });
drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
drop.addEventListener('drop', (e) => {
  e.preventDefault(); drop.classList.remove('dragover');
  if (e.dataTransfer.files.length) setSelection([...e.dataTransfer.files]);
});
input.addEventListener('change', () => {
  if (input.files.length) setSelection([...input.files]);
});

function setSelection(files){
  selection = files;
  statusEl.textContent = `${selection.length} file(s) selected.`;
  btnInspect.disabled = selection.length === 0;
  btnClean.disabled = selection.length === 0;
  result.classList.add('hidden');
  inspectPane.classList.add('hidden');
  inspectBefore.textContent = '';
  inspectAfter.textContent = '';
  inspectDiff.textContent = '';
}

btnInspect.addEventListener('click', async () => {
  if (selection.length === 0) return;
  statusEl.textContent = `Inspecting ${selection.length} file(s)...`;
  inspectPane.classList.remove('hidden');
  const text = await inspectFiles(selection);
  inspectBefore.textContent = text;
  inspectAfter.textContent = '';
  inspectDiff.textContent = '';
  statusEl.textContent = '';
});

btnClean.addEventListener('click', async () => {
  if (selection.length === 0) return;
  statusEl.textContent = `Cleaning ${selection.length} file(s)...`;
  result.classList.add('hidden');

  const data = new FormData();
  for (const f of selection) data.append('uploads', f);

  try {
    const res = await fetch('/clean-batch', { method: 'POST', body: data });
    if (!res.ok) throw new Error((await res.json()).detail || `Server error (${res.status})`);
    const json = await res.json();
    lastCleaned = json;

    // Single-file case
    if (json.download) {
      singleResult.classList.remove('hidden');
      batchResult.classList.add('hidden');
      downloadLink.href = json.download;
      downloadLink.setAttribute('download', json.suggested_filename || 'clean_file');
      result.classList.remove('hidden');
      statusEl.textContent = '';
    } else {
      // Batch
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
    statusEl.textContent = `❌ ${err.message}`;
  }
});

// Inspect AFTER (only for single-file flow)
btnInspectAfter.addEventListener('click', async () => {
  if (!lastCleaned || !lastCleaned.items || lastCleaned.items.length !== 1) return;
  const item = lastCleaned.items[0];
  const after = await fetch(`/inspect-output/${encodeURIComponent(item.cleaned_name)}`).then(r => r.json());
  inspectAfter.textContent = after.report || '(no report)';
  // build diff vs current "before"
  inspectDiff.textContent = diffReports(inspectBefore.textContent, inspectAfter.textContent);
  inspectPane.classList.remove('hidden');
});

// Helpers
async function inspectFiles(files){
  // For now, if many files selected, we concatenate reports for a quick overview.
  let out = '';
  for (const f of files) {
    const d = new FormData(); d.append('upload', f);
    try {
      const res = await fetch('/inspect', { method: 'POST', body: d });
      const json = await res.json();
      out += `# ${f.name}\n${json.report}\n\n`;
    } catch(e) {
      out += `# ${f.name}\n<inspect failed: ${e.message}>\n\n`;
    }
  }
  return out;
}

function diffReports(before, after){
  const b = new Set(before.split(/\r?\n/).filter(Boolean));
  const a = new Set(after.split(/\r?\n/).filter(Boolean));
  const removed = [...b].filter(line => !a.has(line));
  if (removed.length === 0) return '(no differences found)';
  return removed.join('\n');
}
