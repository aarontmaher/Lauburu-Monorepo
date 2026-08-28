/**
 * Lauburu AI Gateway Router Worker
 * ==================================
 * Routes AI API calls through the Cloudflare AI Gateway for observability,
 * caching, rate limiting, and free-tier zero-cost orchestration.
 * Deployed at the edge — all external AI calls are proxied through here for
 * unified logging and zero-cost optimization.
 *
 * Routes:
 *   /v1/anthropic/*      → Anthropic Claude API (Paid Fallback)
 *   /v1/openai/*         → OpenAI API (Paid Fallback)
 *   /v1/google/*         → Google Generative Language API (Gemini Free Tier)
 *   /v1/gemini/*         → Google Gemini API Alias
 *   /v1/cloudflare/*     → Cloudflare Workers AI (Free Tier 10k Neurons/day)
 *   /v1/workers-ai/*     → Direct Cloudflare Workers AI runner
 *   /v1/huggingface/*    → Hugging Face Serverless Inference API (Free Open Models)
 *   /v1/julien/*         → Julien / HuggingFace Serverless Inference Alias
 */

const ACCOUNT_ID   = "16282271f1eccb56f0b96afed09d21ff";
const GATEWAY_SLUG = "lauburu-ai-gateway";
const GW_BASE      = `https://gateway.ai.cloudflare.com/v1/${ACCOUNT_ID}/${GATEWAY_SLUG}`;

const PROVIDER_MAP = {
  anthropic:   "https://api.anthropic.com",
  openai:      "https://api.openai.com",
  google:      "https://generativelanguage.googleapis.com",
  gemini:      "https://generativelanguage.googleapis.com",
  cloudflare:  `https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/ai`,
  "workers-ai": `https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/ai`,
  huggingface: "https://router.huggingface.co/hf-inference",
  julien:      "https://router.huggingface.co/hf-inference",
};

const FREE_TIER_PROVIDERS = new Set(["google", "gemini", "cloudflare", "workers-ai", "huggingface", "julien"]);

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "*",
          "Access-Control-Max-Age": "86400",
        },
      });
    }

    const parts = url.pathname.split("/").filter(Boolean); // ["v1","gemini","v1beta","models"]

    // Health check endpoint
    if (parts.length === 1 && parts[0] === "health") {
      return new Response(JSON.stringify({
        status: "ok",
        service: "lauburu-ai-gateway-router",
        free_tier_providers: Array.from(FREE_TIER_PROVIDERS),
        all_providers: Object.keys(PROVIDER_MAP),
        gateway_base: GW_BASE,
      }), { status: 200, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } });
    }

    // Expect /v1/{provider}/...
    if (parts.length < 2 || parts[0] !== "v1") {
      return new Response(JSON.stringify({
        error: "Invalid route. Use /v1/{provider}/{path}",
        providers: Object.keys(PROVIDER_MAP),
        free_tiers: Array.from(FREE_TIER_PROVIDERS),
      }), { status: 400, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } });
    }

    const provider  = parts[1].toLowerCase();
    const remaining = "/" + parts.slice(2).join("/");

    if (!PROVIDER_MAP[provider]) {
      return new Response(JSON.stringify({
        error: `Unknown provider: ${provider}`,
        valid_providers: Object.keys(PROVIDER_MAP),
      }), { status: 400, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } });
    }

    // Canonicalize provider name for Gateway vs Direct
    const gatewayProvider = (provider === "gemini" ? "google" :
                            (provider === "julien" ? "huggingface" :
                            (provider === "workers-ai" ? "cloudflare" : provider)));

    // Direct Cloudflare Workers AI binding acceleration (if bound and targeted)
    if (env.AI && (provider === "cloudflare" || provider === "workers-ai") && parts[2] === "run") {
      try {
        const modelName = parts.slice(3).join("/");
        const body = await request.json();
        const startTime = Date.now();
        const aiResponse = await env.AI.run(modelName, body);
        const latencyMs = Date.now() - startTime;

        return new Response(JSON.stringify(aiResponse), {
          status: 200,
          headers: {
            "Content-Type": "application/json",
            "X-Lauburu-Provider": "cloudflare-workers-ai-direct",
            "X-Lauburu-Tier": "free-10k-neurons",
            "X-Lauburu-Latency-Ms": String(latencyMs),
            "Access-Control-Allow-Origin": "*",
          },
        });
      } catch (err) {
        // Fallback to Gateway proxy on direct binding failure
        console.warn("Direct Workers AI binding fallback to Gateway:", err);
      }
    }

    // Build Cloudflare AI Gateway target URL
    const targetUrl = `${GW_BASE}/${gatewayProvider}${remaining}${url.search}`;

    // Clone and forward request headers
    const forwardHeaders = new Headers(request.headers);
    forwardHeaders.delete("host");

    const startTime = Date.now();
    let upstreamResp;
    try {
      upstreamResp = await fetch(targetUrl, {
        method:  request.method,
        headers: forwardHeaders,
        body:    request.method !== "GET" && request.method !== "HEAD"
                   ? request.body : undefined,
      });
    } catch (err) {
      return new Response(JSON.stringify({
        error: "Gateway fetch failed",
        provider: gatewayProvider,
        detail: String(err),
        fallback_suggestion: "Check local mesh status on port 8081/8083 or switch provider"
      }), { status: 502, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } });
    }

    const latencyMs = Date.now() - startTime;

    // Log to Analytics Engine (non-blocking)
    if (env.COST_LOGGER) {
      ctx.waitUntil(env.COST_LOGGER.writeDataPoint({
        indexes:  [gatewayProvider, url.hostname],
        doubles:  [latencyMs],
        blobs:    [request.method, remaining, String(upstreamResp.status)],
      }));
    }

    // Forward response with telemetry and tier annotations
    const respHeaders = new Headers(upstreamResp.headers);
    respHeaders.set("X-Lauburu-Provider",    gatewayProvider);
    respHeaders.set("X-Lauburu-Latency-Ms",  String(latencyMs));
    respHeaders.set("X-Lauburu-Tier",        FREE_TIER_PROVIDERS.has(provider) ? "free-tier" : "paid-gateway");
    respHeaders.set("X-Lauburu-Gateway",     "cloudflare");
    respHeaders.set("Access-Control-Allow-Origin", "*");

    return new Response(upstreamResp.body, {
      status:  upstreamResp.status,
      headers: respHeaders,
    });
  },
};
