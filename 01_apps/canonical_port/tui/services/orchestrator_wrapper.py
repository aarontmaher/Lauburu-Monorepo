import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any

class HeadlessOrchestratorWrapper:
    """
    Manages a background headless `agy` (Gemini Ultra/Flash) process.
    Acts as the Cloud Handoff Engine for complex tool execution.
    """
    def __init__(self, model: str = "gemini-ultra", headless_flag: str = "--headless"):
        self.model = model
        self.headless_flag = headless_flag
        self.process: Optional[asyncio.subprocess.Process] = None
        self.on_message_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_tool_call_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._running = False
        
    async def start(self):
        """Spawns the headless agy process."""
        if self._running:
            return
            
        logging.info(f"Starting Headless Agy Orchestrator (Model: {self.model})")
        # In a real environment, we'd spawn the actual agy CLI.
        # This wrapper expects agy to communicate via JSON Lines over stdout.
        try:
            self.process = await asyncio.create_subprocess_exec(
                "agy", self.headless_flag, "--model", self.model, "--json-ipc",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self._running = True
            asyncio.create_task(self._read_stdout())
            asyncio.create_task(self._read_stderr())
        except FileNotFoundError:
            logging.error("agy CLI not found in path. Cannot start headless orchestrator. (Zero-Mock Enforced)")
            self._running = False
            if self.on_message_callback:
                self.on_message_callback({"type": "ERROR", "content": "-- (Agy process not found, zero-mock enforced)"})
            
    async def stop(self):
        """Terminates the headless process."""
        self._running = False
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except ProcessLookupError:
                pass
            self.process = None

    def set_callbacks(self, on_message: Callable, on_tool_call: Callable):
        self.on_message_callback = on_message
        self.on_tool_call_callback = on_tool_call

    async def send_prompt(self, prompt: str, context: Optional[str] = None):
        """Delegates a complex prompt to the cloud orchestrator."""
        if not self._running:
            await self.start()
            
        payload = {
            "type": "USER_PROMPT",
            "content": prompt,
            "context": context
        }
        
        if self.process and self.process.stdin:
            self.process.stdin.write((json.dumps(payload) + "\n").encode('utf-8'))
            await self.process.stdin.drain()
        else:
            if self.on_message_callback:
                self.on_message_callback({"type": "ERROR", "content": "-- (Agy process not running)"})

    async def _read_stdout(self):
        if not self.process or not self.process.stdout:
            return
            
        while self._running:
            try:
                line = await self.process.stdout.readline()
                if not line:
                    break
                
                try:
                    data = json.loads(line.decode('utf-8').strip())
                    msg_type = data.get("type", "TEXT")
                    
                    if msg_type == "TOOL_CALL" and self.on_tool_call_callback:
                        self.on_tool_call_callback(data)
                    elif self.on_message_callback:
                        self.on_message_callback(data)
                        
                except json.JSONDecodeError:
                    if self.on_message_callback:
                        self.on_message_callback({"type": "TEXT", "content": line.decode('utf-8').strip()})
                        
            except Exception as e:
                logging.error(f"Error reading agy stdout: {e}")
                break

    async def _read_stderr(self):
        if not self.process or not self.process.stderr:
            return
            
        while self._running:
            line = await self.process.stderr.readline()
            if not line:
                break
            logging.debug(f"[AGY STDERR] {line.decode('utf-8').strip()}")
