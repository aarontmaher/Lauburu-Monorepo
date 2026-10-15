const ENDPOINTS = {
  l1: 'http://127.0.0.1:8082/health',
  da: 'http://127.0.0.1:8083/health',
  l3: 'http://192.168.8.225:8082/health',
  l3vlm: 'http://192.168.8.225:8080/health',
  l3sw: 'http://192.168.8.225:8086/health',
};

async function checkHealth(url) {
  try {
    const r = await fetch(url, { signal: AbortSignal.timeout(2000) });
    return r.ok ? '✅ ONLINE' : `⚠️ HTTP ${r.status}`;
  } catch { return '❌ OFFLINE'; }
}

async function refreshStatus() {
  const checks = await Promise.all([
    checkHealth(ENDPOINTS.l1),
    checkHealth(ENDPOINTS.da),
    checkHealth(ENDPOINTS.l3),
    checkHealth(ENDPOINTS.l3vlm),
    checkHealth(ENDPOINTS.l3sw),
  ]);
  document.getElementById('l1-status').textContent = checks[0];
  document.getElementById('da-status').textContent = checks[1];
  document.getElementById('l3-status').textContent = checks[2];
  document.getElementById('l3vlm-status').textContent = checks[3];
  document.getElementById('l3sw-status').textContent = checks[4];
  document.getElementById('conn-dot').style.background = checks[0].includes('ONLINE') ? '#00ff88' : '#ff4444';
}

function setStatus(el, text, cls) {
  el.textContent = text;
  el.className = cls || '';
}

async function invokeAI(model) {
  const text = document.getElementById('query-input').value.trim();
  if (!text) return;
  const box = document.getElementById('response-box');
  const meta = document.getElementById('meta-line');
  box.style.display = 'block';
  box.textContent = '⏳ Invoking ' + model + '…';
  
  try {
    const start = Date.now();
    const resp = await chrome.runtime.sendMessage({ type: 'INVOKE_SOVEREIGN', text, model });
    const elapsed = ((Date.now() - start) / 1000).toFixed(1);
    box.textContent = resp.content;
    meta.textContent = `Model: ${resp.model} | Tokens: ${resp.tokens} | ${elapsed}s | Cost: $0.00 (local)`;
  } catch (e) {
    box.textContent = '❌ Error: ' + e.message;
  }
}

function invokeMain() { invokeAI('qwen_38_max'); }
function invokeDA() { invokeAI('qwen_38_max_27b_abliterated'); }
function openMeshGUI() { chrome.tabs.create({ url: 'http://192.168.8.1/mesh_gui.html' }); }
function openLuCI() { chrome.tabs.create({ url: 'http://192.168.8.1/cgi-bin/luci' }); }

// Init
document.addEventListener('DOMContentLoaded', () => {
  refreshStatus();
  // Load last response if any
  chrome.storage.session.get(['lastSovereignResponse', 'lastQuery'], (data) => {
    if (data.lastSovereignResponse && data.lastQuery) {
      document.getElementById('query-input').value = data.lastQuery;
      const box = document.getElementById('response-box');
      box.style.display = 'block';
      box.textContent = data.lastSovereignResponse.content || '';
    }
  });
  setInterval(refreshStatus, 30000);
});
