// Nexus Sovereign — Background Service Worker
// Routes browser AI requests through prima.cpp mesh orchestrator

const SOVEREIGN_CONFIG = {
  primaryEndpoint: 'http://127.0.0.1:8082/v1/chat/completions',
  adversarialEndpoint: 'http://127.0.0.1:8083/v1/chat/completions',
  screenLensEndpoint: 'http://127.0.0.1:3035/api/latest',
  l3SwarmEndpoint: 'http://192.168.8.225:8086/v1/chat/completions',
  meshTelemetryEndpoint: 'http://192.168.8.1/mesh_telemetry_full.json',
  defaultModel: 'qwen_38_max',
  adversarialModel: 'qwen_38_max_27b_abliterated',
};

// Context menu: "Send to Sovereign AI"
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'send-to-sovereign',
    title: '🏛️ Send to Sovereign AI (prima.cpp)',
    contexts: ['selection']
  });
  chrome.contextMenus.create({
    id: 'open-mesh-panel',
    title: '📡 Open Mesh Control Panel',
    contexts: ['all']
  });
  chrome.contextMenus.create({
    id: 'challenge-with-da',
    title: '🔴 Devil\'s Advocate Challenge',
    contexts: ['selection']
  });
  console.log('[Nexus Sovereign] Extension activated. prima.cpp endpoint:', SOVEREIGN_CONFIG.primaryEndpoint);
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const selectedText = info.selectionText || '';
  
  if (info.menuItemId === 'send-to-sovereign') {
    const result = await invokeSovereign(selectedText, SOVEREIGN_CONFIG.defaultModel);
    await chrome.storage.session.set({ lastSovereignResponse: result, lastQuery: selectedText });
    chrome.sidePanel.open({ tabId: tab.id });
  } else if (info.menuItemId === 'challenge-with-da') {
    const result = await invokeSovereign(selectedText, SOVEREIGN_CONFIG.adversarialModel);
    await chrome.storage.session.set({ lastSovereignResponse: result, lastQuery: selectedText, isAdversarial: true });
    chrome.sidePanel.open({ tabId: tab.id });
  } else if (info.menuItemId === 'open-mesh-panel') {
    chrome.sidePanel.open({ tabId: tab.id });
  }
});

// Keyboard shortcut handler
chrome.commands.onCommand.addListener(async (command) => {
  if (command === 'invoke-sovereign') {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.getSelection().toString()
    });
    const selectedText = result.result;
    if (selectedText) {
      const response = await invokeSovereign(selectedText, SOVEREIGN_CONFIG.defaultModel);
      await chrome.storage.session.set({ lastSovereignResponse: response, lastQuery: selectedText });
    }
    chrome.sidePanel.open({ tabId: tab.id });
  } else if (command === 'open-mesh-panel') {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    chrome.sidePanel.open({ tabId: tab.id });
  }
});

// Core sovereign inference call
async function invokeSovereign(text, model) {
  try {
    const endpoint = model.includes('abliterated') 
      ? SOVEREIGN_CONFIG.adversarialEndpoint 
      : SOVEREIGN_CONFIG.primaryEndpoint;
    
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: model,
        messages: [
          { role: 'system', content: 'You are the Lauburu Sovereign AI (Qwen 3.8 Max via prima.cpp). Analyze the provided text concisely and provide actionable insights.' },
          { role: 'user', content: text }
        ],
        max_tokens: 500,
        temperature: 0.3,
        stream: false
      })
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    return { 
      content: data.choices[0].message.content, 
      model: model,
      tokens: data.usage?.total_tokens || 0,
      endpoint: endpoint,
      timestamp: Date.now()
    };
  } catch (err) {
    // Fallback to L3 swarm worker
    try {
      const fallback = await fetch(SOVEREIGN_CONFIG.l3SwarmEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'qwen2.5-coder-1.5b-instruct-q4_k_m',
          messages: [{ role: 'user', content: text }],
          max_tokens: 300
        })
      });
      const data = await fallback.json();
      return { content: data.choices[0].message.content, model: 'L3-fallback', error: err.message };
    } catch (e) {
      return { content: `Error: ${err.message}`, model: 'error', error: e.message };
    }
  }
}

// Periodic mesh telemetry fetch (every 30s)
async function fetchMeshTelemetry() {
  try {
    const r = await fetch(SOVEREIGN_CONFIG.meshTelemetryEndpoint);
    const data = await r.json();
    await chrome.storage.session.set({ meshTelemetry: data, meshLastFetch: Date.now() });
  } catch (e) {
    // Silent fail — router may be inaccessible from browser context
  }
}

// Message handler from popup/sidepanel
chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  if (msg.type === 'INVOKE_SOVEREIGN') {
    invokeSovereign(msg.text, msg.model || SOVEREIGN_CONFIG.defaultModel).then(reply);
    return true; // async reply
  }
  if (msg.type === 'GET_CONFIG') {
    reply(SOVEREIGN_CONFIG);
    return true;
  }
  if (msg.type === 'FETCH_TELEMETRY') {
    fetchMeshTelemetry().then(() => {
      chrome.storage.session.get(['meshTelemetry'], (r) => reply(r.meshTelemetry));
    });
    return true;
  }
});
