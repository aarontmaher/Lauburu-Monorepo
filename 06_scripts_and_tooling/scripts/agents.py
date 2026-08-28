import json
import urllib.request
import urllib.error
import logging
from google.antigravity import Agent, LocalAgentConfig
from src.config import DEVICES, LOCAL_OLLAMA_URL
from src.tools import (
    establish_ssh_tunnel,
    configure_tailscale_routing,
    control_debugging_mode,
    scan_bluetooth_devices,
    connect_bluetooth_device,
    run_docker_fallback,
    execute_termux_command,
    manage_cursor,
    manage_copilot,
    manage_docker,
    manage_tailscale,
    manage_glinet,
    manage_luci,
    manage_speedify
)

logger = logging.getLogger("lauburu-agi-agents")

def get_specialist_tools(device_key: str):
    """Returns the list of Python tools registered for each device specialist."""
    if device_key == "pixel":
        return [
            establish_ssh_tunnel,
            configure_tailscale_routing,
            control_debugging_mode,
            scan_bluetooth_devices,
            connect_bluetooth_device,
            run_docker_fallback,
            execute_termux_command,
            manage_tailscale,
            manage_glinet,
            manage_luci,
            manage_speedify,
            manage_docker
        ]
    elif device_key == "mac":
        return [
            establish_ssh_tunnel,
            configure_tailscale_routing,
            scan_bluetooth_devices,
            manage_cursor,
            manage_copilot,
            manage_docker,
            manage_tailscale,
            manage_speedify
        ]
    elif device_key == "samsung_server":
        return [
            establish_ssh_tunnel,
            configure_tailscale_routing,
            run_docker_fallback,
            manage_docker,
            manage_tailscale
        ]
    elif device_key == "windows":
        return [
            establish_ssh_tunnel,
            configure_tailscale_routing,
            run_docker_fallback,
            manage_docker,
            manage_tailscale
        ]
    elif device_key == "tablet":
        return [
            configure_tailscale_routing,
            scan_bluetooth_devices,
            manage_tailscale
        ]
    else:  # iphone
        return [
            configure_tailscale_routing,
            scan_bluetooth_devices,
            manage_tailscale
        ]



class DualModeAgent:
    def __init__(self, device_key: str):
        self.device_key = device_key
        self.config = DEVICES[device_key]
        self.instructions = self._get_system_instructions()
        self.tools = get_specialist_tools(device_key)
        
        # Configure the Google Antigravity SDK Agent for Escalated API Mode
        sdk_config = LocalAgentConfig(
            model="gemini-3.5-flash",
            system_instructions=self.instructions,
            tools=self.tools
        )
        self.sdk_agent = Agent(sdk_config)

    def _get_system_instructions(self) -> str:
        base = (
            f"You are the {self.device_key.upper()} Specialist AGI. Device: {self.config.name}.\n"
            f"Simulated Base Model: {self.config.local_model}.\n"
            "Goal: Maintain network stability, storage consistency, and system coordination.\n"
        )
        if self.device_key == "pixel":
            base += (
                "ROLE: PRIMARY SYSTEM CONTROLLER.\n"
                "You are the global coordinator. You monitor connectivity to the headless Samsung Linux Server, macOS laptop, "
                "and other devices. Ensure that network tunnels (SSH, Tailscale) and debugging modes are maintained.\n"
                "Exception: Store full project files internally on the Google Pixel.\n"
                "Important: You are NOT reliant on the SSD for file operations. Your master project files "
                "reside entirely on your internal storage. The SSD is treated only as a synchronization destination. "
                "You are capable of running fully offline, practicing coding, and implementing approved features "
                "in your local Linux terminal sandbox.\n"
                "PROOF OF PRODUCT (MOST IMPORTANT RULE): Your most critical rule is 'Proof of Product'. You must act "
                "as a deep auditor of feature code and feature implementations, never trusting claims or database "
                "reports without verification. You demand live, human-like click-through verification of dashboard UI "
                "elements, and are highly critical of all status statements. You must actively cross-verify and prove "
                "everything yourself, seeking outside AGI peer reviews (e.g. from MacBook Specialist or Lauburu coordinator) "
                "to confirm system and storage status consensus.\n"
                "CONSULTATION & STUDY: You are encouraged to consult other surrounding AGIs (e.g., Lauburu coordinator, "
                "MacBook Pro specialist) to deepen context. You must continuously study the local app, project files, "
                "the Self Training Optimizer parameter tuning heuristics, and your local device environment.\n"
                "SAFETY & HUMAN OVERRIDE: Always prioritize device and data safety. Monitor thermal levels carefully to "
                "prevent overheating (never exceed target cpu temperature bounds). Establish very strong coding standards; "
                "never write reckless code or execute destructive bash operations. You MUST consult human approval in the chat "
                "or modal overrides for any significant system changes or operations. You must NEVER auto-dismiss, bypass, "
                "or click away human approval pop-ups; you must halt processing and await manual interaction. Whenever you "
                "halt execution, you must automatically default your background cycles to local sandbox training, studying "
                "the local app/project codebase structure, reviewing device telemetry, and practicing secure shell coding in Termux/Termius.\n"
            )
        elif self.device_key == "mac":
            base += (
                "ROLE: FALLBACK SYSTEM CONTROLLER.\n"
                "You run on the macOS host environment. You prioritize storing files on the external SSD, backing up to Google Drive.\n"
                "You must constantly verify the Pixel (Primary Controller) status. If it goes offline, you take over "
                "coordinating duties to maintain network stability and local AI training progress, utilizing Tailscale, SSH, "
                "and wireless debugging links."
            )
        elif self.device_key == "samsung_server":
            base += (
                "ROLE: HIGH-PERFORMANCE AI RESOURCE HUB.\n"
                "You run on the Samsung S20+ Headless Linux Server (gl-mt3600be). Your job is to host the main local AI training, "
                "docker container execution, and act as a reliable backup sync point. You communicate with whichever "
                "controller is active (Pixel or Mac fallback) to report compute performance and store project data."
            )
        elif self.device_key == "tablet":
            base += (
                "ROLE: CONNECTIVITY GATEWAY & HOTSPOT.\n"
                "You run on the Tablet (Felix Hotspot). Your job is to keep the Felix Mobile connection active, "
                "act as the main internet router/hotspot for all other devices, and monitor network statistics. "
                "Communicate with the active controller to report connection stability."
            )
        base += "Output your decisions in a strict JSON format matching the schema:\n"
        base += '{"reasoning": "str", "action": "str", "tools": ["tool_name"], "confidence": float}'
        return base

    async def chat(self, prompt: str):
        """Delegates chat prompts to the underlying Antigravity SDK Agent."""
        return await self.sdk_agent.chat(prompt)

    async def __aenter__(self):
        await self.sdk_agent.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.sdk_agent.__aexit__(exc_type, exc_val, exc_tb)

    async def run_local_inference(self, prompt: str, ssd_online: bool) -> dict:
        """Runs inference via local Ollama endpoint. Falls back to mock heuristics if Ollama is offline."""
        logger.info(f"AGENT [{self.device_key.upper()}]: Executing local inference using '{self.config.local_model}'...")
        
        # Build prompt payload
        system_context = f"{self.instructions}\nCurrent System Status: SSD is {'ONLINE' if ssd_online else 'OFFLINE'}.\n"
        full_prompt = f"{system_context}\nUser: {prompt}\nJSON Output:"

        # 1. Attempt local Ollama endpoint query
        payload = {
            "model": self.config.local_model,
            "prompt": full_prompt,
            "stream": False,
            "format": "json"
        }
        
        try:
            req = urllib.request.Request(
                LOCAL_OLLAMA_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            # Short timeout to fail fast if Ollama service is not running
            with urllib.request.urlopen(req, timeout=3.0) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                response_text = res_data.get("response", "")
                return json.loads(response_text)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            # 2. Offline Fallback / Heuristics when Ollama is unavailable
            logger.info(f"AGENT [{self.device_key.upper()}]: Local Ollama offline. Executing local specialist heuristics.")
            return self._run_offline_heuristics(ssd_online)

    def _run_offline_heuristics(self, ssd_online: bool) -> dict:
        """Determines storage specialist action and confidence scores when offline."""
        if ssd_online:
            # High confidence when everything is normal
            return {
                "reasoning": f"External SSD is online. Storing files at primary path {self.config.ssd_path}.",
                "action": "use_ssd",
                "tools": [],
                "confidence": 0.95
            }
        
        # When SSD goes offline, specialists must handle fallbacks
        if self.device_key == "pixel":
            # Pixel has a lot of offline tools, but needs coordination (confidence low to trigger escalation)
            return {
                "reasoning": "SSD is offline. Google Pixel project must run from internal storage. Need to scan Bluetooth to locate SSD and set up SSH tunnels to re-route other devices.",
                "action": "bluetooth_recovery",
                "tools": ["scan_bluetooth_devices", "establish_ssh_tunnel"],
                "confidence": 0.60  # Triggers escalation because it's below consensus threshold (0.7)
            }
        elif self.device_key == "mac":
            return {
                "reasoning": "SSD offline. Redirecting folder paths to Google Drive mount. Awaiting coordinator direction.",
                "action": "gdrive_fallback",
                "tools": ["configure_tailscale_routing"],
                "confidence": 0.65
            }
        elif self.device_key == "samsung_server":
            return {
                "reasoning": "SSD offline. Samsung Linux Server acting as compute hub and local backup node. Running container sync procedures.",
                "action": "docker_sync",
                "tools": ["run_docker_fallback"],
                "confidence": 0.80
            }
        elif self.device_key == "tablet":
            return {
                "reasoning": "SSD offline. Tablet hotspot connection is fully functional. Maintaining routing and hotspot gateway.",
                "action": "maintain_hotspot",
                "tools": ["configure_tailscale_routing"],
                "confidence": 0.90
            }
        else:
            return {
                "reasoning": "SSD offline. Referencing local folder backup paths.",
                "action": "local_backup",
                "tools": [],
                "confidence": 0.85  # Simple devices might report higher confidence in basic fallbacks
            }

    async def run_escalated_inference(self, prompt: str) -> str:
        """Escalates decision to paid API using the Google Antigravity SDK."""
        logger.warning(f"AGENT [{self.device_key.upper()}]: Escalating turns to Google Antigravity AGI (Gemini API)...")
        try:
            response = await self.sdk_agent.chat(prompt)
            return await response.text()
        except Exception as e:
            logger.error(f"AGENT [{self.device_key.upper()}]: Escalated API call failed: {e}")
            # Safe recovery if API key is invalid/missing
            return self._run_escalated_key_fallback(prompt)

    def _run_escalated_key_fallback(self, prompt: str) -> str:
        """Gracefully recovers if Gemini API key is missing or invalid."""
        logger.warning(f"AGENT [{self.device_key.upper()}]: API key missing/invalid. Executing deterministic escalation recovery plan.")
        if self.device_key == "pixel":
            return (
                "LOCAL FALLBACK PLAN: Switch to internal project folder. "
                "Trigger 'scan_bluetooth_devices' and verify connection to Tailscale. "
                "Establish SSH tunnel to Mac Host to regain sync tunnel."
            )
        elif self.device_key == "samsung_server":
            return f"LOCAL FALLBACK PLAN: Standby compute mode active. Backup target directory is: {self.config.gdrive_path}."
        elif self.device_key == "tablet":
            return "LOCAL FALLBACK PLAN: Maintaining Felix Mobile hotspot and Tailscale connection."
        else:
            return f"LOCAL FALLBACK PLAN: Defaulting storage paths to local Google Drive backup: {self.config.gdrive_path}."

