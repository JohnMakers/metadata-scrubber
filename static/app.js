const drop = document.getElementById('drop');
const input = document.getElementById('file');
const statusEl = document.getElementById('status');
const result = document.getElementById('result');
const downloadLink = document.getElementById('downloadLink');

function chooseFile() { input.click(); }

drop.addEventListener('click', chooseFile);
drop.addEventListener('dragover', (e) => {
  e.preventDefault(); drop.classList.add('dragover');
});
drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
drop.addEventListener('drop', (e) => {
  e.preventDefault(); drop.classList.remove('dragover');
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
input.addEventListener('change', () => {
  if (input.files.length) handleFile(input.files[0]);
});

async function handleFile(file) {
  statusEl.textContent = `Uploading ${file.name}…`;
  result.classList.add('hidden');

  const data = new FormData();
  data.append('upload', file);

  try {
    const res = await fetch('/clean', { method: 'POST', body: data });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (${res.status})`);
    }
    const json = await res.json();
    downloadLink.href = json.download;
    downloadLink.setAttribute('download', json.suggested_filename || 'clean_file');
    result.classList.remove('hidden');
    statusEl.textContent = '';
  } catch (err) {
    statusEl.textContent = `❌ ${err.message}`;
  }
}
