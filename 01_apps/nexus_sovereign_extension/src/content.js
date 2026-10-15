// Nexus Sovereign content script
// Injects a floating badge on pages when selection is made
let badge = null;

document.addEventListener('mouseup', (e) => {
  const selected = window.getSelection().toString().trim();
  if (selected.length > 10) {
    showBadge(e.pageX, e.pageY, selected);
  } else {
    hideBadge();
  }
});

function showBadge(x, y, text) {
  hideBadge();
  badge = document.createElement('div');
  badge.innerHTML = '⚡ Sovereign';
  badge.style.cssText = `
    position:absolute; left:${x}px; top:${y-28}px; z-index:999999;
    background:#4040cc; color:#fff; border-radius:4px; padding:3px 8px;
    font-size:11px; font-family:monospace; cursor:pointer;
    box-shadow:0 2px 8px rgba(0,0,0,0.5); user-select:none;
  `;
  badge.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'INVOKE_SOVEREIGN', text });
    hideBadge();
  });
  document.body.appendChild(badge);
}

function hideBadge() {
  if (badge) { badge.remove(); badge = null; }
}
