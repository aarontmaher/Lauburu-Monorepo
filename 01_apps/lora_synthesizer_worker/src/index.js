export default {
  async scheduled(event, env, ctx) {
    const prompts = [
      "Screen Lens detected Port 18805 Real-Time Command Console rendering at 45 FPS instead of 120 FPS. React useEffect hook was triggering double re-renders.",
      "A new subagent 'DeepCoder' was spawned but hung because 'skill_search' tool was missing from the registry.",
      "The host Mac Mini VRAM usage spiked to 92%, violating the 9.6GB Sanctuary Headroom rule.",
      "A local GGUF model failed to load over the 10Gbps Thunderbolt bridge due to TCP handshake timeout.",
      "Movesense ECG 512Hz stream had missing R-peaks due to Bluetooth Low Energy interference."
    ];
    
    const rawTelemetry = prompts[Math.floor(Math.random() * prompts.length)];

    const systemPrompt = "You are an expert Synthetic Data Architect for the Lauburu AI Mesh. Your goal is to generate high-quality Direct Preference Optimization (DPO) pairs to train local models. Synthesize a JSON tuple containing: 'instruction' (what the user asked), 'input' (the context), and 'output' (the optimal zero-mock response enforcing Lauburu rules). Output ONLY valid JSON.";

    const messages = [
      { role: "system", content: systemPrompt },
      { role: "user", content: `Raw Data: ${rawTelemetry}` }
    ];

    try {
      const response = await env.AI.run("@cf/meta/llama-3.1-8b-instruct", { messages });
      
      let aiOutput = response.response;
      if (aiOutput.includes('```json')) {
         aiOutput = aiOutput.split('```json')[1].split('```')[0].trim();
      } else if (aiOutput.includes('```')) {
         aiOutput = aiOutput.split('```')[1].split('```')[0].trim();
      }

      const parsed = JSON.parse(aiOutput);
      const loraPair = {
          timestamp: new Date().toISOString(),
          instruction: parsed.instruction,
          input: parsed.input,
          output: parsed.output,
          generator: "Cloudflare_Workers_AI_Llama3.1"
      };

      const key = `lora_pair_${Date.now()}`;
      await env.LORA_SYNTHESIS_QUEUE.put(key, JSON.stringify(loraPair));
      console.log(`Saved ${key}`);
    } catch (err) {
      console.error("Error generating or parsing", err);
    }
  }
};
