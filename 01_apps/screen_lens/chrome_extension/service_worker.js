/**
 * Lauburu Screen Lens Sovereign — Chrome MV3 Background Service Worker
 * Connects Google Chrome, Content Scripts, and Chrome DevTools to:
 * - Port 9224 Chrome DevTools Sentinel Bridge
 * - Port 8087 EmbeddingGemma 2 (768/512/256/128D MRL)
 * - Port 8089 / 8090 Local AI Chat
 * - Port 8096 Podman Local AI Trainer
 */

const BRIDGE_ENDPOINTS = [
  "http://127.0.0.1:9224",
  "http://100.121.202.34:9224",
  "http://100.121.247.8:9224"
];

async function callBridge(path, method = "GET", body = null) {
  let lastErr = null;
  for (const base of BRIDGE_ENDPOINTS) {
    try {
      const opts = {
        method,
        headers: { "Content-Type": "application/json" }
      };
      if (body && method !== "GET") {
        opts.body = JSON.stringify(body);
      }
      const resp = await fetch(`${base}${path}`, opts);
      if (resp.ok) {
        return await resp.json();
      }
    } catch (err) {
      lastErr = err;
    }
  }
  return { status: "error", error: String(lastErr || "Bridge unreachable") };
}

chrome.runtime.onInstalled.addListener(() => {
  console.log("[Lauburu Screen Lens Sovereign] Local AI & EmbeddingGemma 2 MV3 Extension Installed.");
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    if (message.type === "LENS_STATUS") {
      const res = await callBridge("/api/devtools/status", "GET");
      sendResponse(res);
    } else if (message.type === "LENS_AI_CHAT") {
      const res = await callBridge("/api/devtools/ai_chat", "POST", message.payload);
      sendResponse(res);
    } else if (message.type === "LENS_EMBED_PAGE") {
      const res = await callBridge("/api/devtools/embed_page", "POST", message.payload);
      sendResponse(res);
    } else if (message.type === "LENS_SEARCH_MRL") {
      const res = await callBridge("/api/devtools/search_mrl", "POST", message.payload);
      sendResponse(res);
    } else if (message.type === "LENS_WEBVLA_DISTILL") {
      const res = await callBridge("/api/devtools/webvla_distill", "POST", message.payload);
      sendResponse(res);
    } else if (message.type === "LENS_PODMAN_TRAIN") {
      const res = await callBridge("/api/devtools/trigger_podman_train", "POST", message.payload || { batch_size: 16 });
      sendResponse(res);
    } else if (message.type === "LENS_PAGE_ASSIST_STATUS") {
      const res = await callBridge("/api/devtools/page_assist", "GET");
      sendResponse(res);
    } else if (message.type === "LENS_AUTOMATION_TRAIN_247") {
      const res = await callBridge("/api/devtools/automation_protocol", "POST", message.payload || { trigger_mlx: false });
      sendResponse(res);
    } else if (message.type === "LENS_CHROMIUM_SPECIALIST_STATUS") {
      const res = await callBridge("/api/devtools/specialists", "GET");
      sendResponse({
        ...res,
        extension_specialist_stack: [
          "polyglot-typescript-web-specialist",
          "polyglot-rust-wgpu-specialist",
          "polyglot-go-bubbletea-specialist",
          "polyglot-python-specialist",
          "screen-lens-sovereign",
          "continus-lens-practice-automation"
        ]
      });
    } else {
      sendResponse({ status: "unknown_message", type: message.type });
    }
  })();
  return true; // keep async message channel open
});

