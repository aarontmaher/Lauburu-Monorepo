"""
Hermes 3 Tool Routing Engine for the Lauburu IDE Intelligence Architecture.

Operates on Port 8083 (Sovereign Master Local Orchestrator: Qwen 3.8 Max 27B Abliterated).
Handles:
- Tool discovery from monorepo skills and built-in IDE actions
- XML <tools> schema formatting and <tool_call> response parsing
- Skill routing and dynamic dispatch
- /loop continuous distillation and optimization trigger detection
- Decoupled routing decision between Hermes Tool Router and Qwen 2.5 Coder
"""

from dataclasses import dataclass, field
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
import urllib.error
import urllib.request

logger = logging.getLogger("hermes_router")

# Default Ports and Endpoints per PROJECT.md and Canonical Hardware Matrix
PORT_HERMES_MASTER = 8083
PORT_QWEN_CODER = 8081

DEFAULT_HERMES_URL = f"http://127.0.0.1:{PORT_HERMES_MASTER}/v1/chat/completions"
DEFAULT_CODER_URL = f"http://127.0.0.1:{PORT_QWEN_CODER}/v1/chat/completions"

MODEL_HERMES_MASTER = "qwen_38_max_abliterated"
MODEL_QWEN_CODER = "qwen2.5-coder-7b-instruct"


@dataclass
class ToolDefinition:
    """Definition of an executable tool or skill."""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable[..., Any]] = None


@dataclass
class RoutingDecision:
    """Interface Contract per PROJECT.md §4.2."""
    engine: str                       # "HERMES_TOOL_ROUTER" or "QWEN_CODE_GENERATOR"
    target_endpoint: str              # Port 8083 or Port 8081
    model_id: str                     # "qwen_38_max_abliterated" or "qwen2.5-coder-7b-instruct"
    tools_to_invoke: List[Dict[str, Any]] = field(default_factory=list)
    vector_pages_paged: int = 0
    loop_triggered: bool = False
    reasoning: str = ""


class HermesRouter:
    """
    Hermes 3 Tool Routing Engine.
    Discovers tools, formats Hermes 3 XML schema prompts, parses model tool-calls,
    routes skills, and manages /loop continuous learning triggers.
    """

    def __init__(
        self,
        hermes_url: str = DEFAULT_HERMES_URL,
        coder_url: str = DEFAULT_CODER_URL,
        master_model_id: str = MODEL_HERMES_MASTER,
        coder_model_id: str = MODEL_QWEN_CODER,
        skills_dir: Optional[str] = None,
    ):
        self.hermes_url = hermes_url
        self.coder_url = coder_url
        self.master_model_id = master_model_id
        self.coder_model_id = coder_model_id

        # Monorepo skills path
        self.skills_dir = Path(
            skills_dir
            or os.path.expanduser("~/DFS_UNIFIED/Lauburu-Monorepo/.agents/skills")
        )

        self._tools: Dict[str, ToolDefinition] = {}
        self._skills_cache: Dict[str, Dict[str, str]] = {}
        self._register_builtin_tools()
        self.discover_skills()

    def _register_builtin_tools(self) -> None:
        """Register built-in IDE and mesh tools."""
        self.register_tool(
            ToolDefinition(
                name="vector_search",
                description="Search Vector DB / KV-cache for relevant code context, function definitions, and architecture docs.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query to retrieve context for."},
                        "top_k": {"type": "integer", "description": "Number of pages to retrieve (default 3)."}
                    },
                    "required": ["query"]
                }
            )
        )

        self.register_tool(
            ToolDefinition(
                name="read_source_file",
                description="Read contents of a file from the workspace filesystem.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Absolute or relative path to the file."}
                    },
                    "required": ["file_path"]
                }
            )
        )

        self.register_tool(
            ToolDefinition(
                name="write_source_file",
                description="Write modified or generated code content to a file in the workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Absolute or relative path to the file."},
                        "content": {"type": "string", "description": "File contents to write."}
                    },
                    "required": ["file_path", "content"]
                }
            )
        )

        self.register_tool(
            ToolDefinition(
                name="run_linter",
                description="Execute static analysis and linting checks on workspace code.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file to lint."}
                    },
                    "required": ["file_path"]
                }
            )
        )

        self.register_tool(
            ToolDefinition(
                name="run_terminal_command",
                description="Execute a shell command in the local environment and return stdout, stderr, and exit code.",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The shell command to run."}
                    },
                    "required": ["command"]
                }
            )
        )

        self.register_tool(
            ToolDefinition(
                name="mesh_ping",
                description="Check physical reachability and latency of Lauburu mesh nodes (L1 through L7).",
                parameters={
                    "type": "object",
                    "properties": {
                        "node_name": {"type": "string", "description": "Name of node e.g. L3_Linux_Hub, L2_MacBook_Pro."}
                    },
                    "required": ["node_name"]
                }
            )
        )

        self.register_tool(
            ToolDefinition(
                name="loop_trigger",
                description="Trigger an autonomous /loop distillation or self-healing cycle on L3 Linux Hub.",
                parameters={
                    "type": "object",
                    "properties": {
                        "task_description": {"type": "string", "description": "Description of the task to optimize or fine-tune."},
                        "target_model": {"type": "string", "description": "Target model for distillation."}
                    },
                    "required": ["task_description"]
                }
            )
        )

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool in the router registry."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Retrieve a tool definition by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """List all currently registered tools."""
        return list(self._tools.values())

    def get_registered_tools(self) -> List[ToolDefinition]:
        """Alias for list_tools() to satisfy test suites."""
        return list(self._tools.values())

    def discover_skills(self) -> Dict[str, Dict[str, str]]:
        """Scan skills directories in monorepo and register them as callable tools."""
        candidate_paths = [
            self.skills_dir,
            Path(os.path.expanduser("~/.gemini/config/skills")),
            Path(os.path.expanduser("~/.gemini/antigravity/skills")),
        ]

        for base_path in candidate_paths:
            if not base_path.exists() or not base_path.is_dir():
                continue
            for skill_dir in base_path.iterdir():
                if not skill_dir.is_dir():
                    continue
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    skill_name = skill_dir.name
                    desc = self._extract_skill_description(skill_file)
                    self._skills_cache[skill_name] = {
                        "name": skill_name,
                        "path": str(skill_file),
                        "description": desc,
                    }
                    tool_name = f"skill_{skill_name.replace('-', '_')}"
                    if tool_name not in self._tools:
                        self.register_tool(
                            ToolDefinition(
                                name=tool_name,
                                description=f"Specialized Skill: {desc}",
                                parameters={
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "Action or question for this specialist."}
                                    },
                                    "required": ["query"]
                                }
                            )
                        )

        return self._skills_cache

    @staticmethod
    def _extract_skill_description(skill_file: Path) -> str:
        """Parse description from YAML frontmatter or first paragraph in SKILL.md."""
        try:
            content = skill_file.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if match:
                frontmatter = match.group(1)
                desc_match = re.search(r"description:\s*(.+)", frontmatter)
                if desc_match:
                    return desc_match.group(1).strip().strip('"').strip("'")
            lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
            if lines:
                return lines[0][:150]
        except Exception as e:
            logger.debug(f"Failed to read skill {skill_file}: {e}")
        return "Specialized domain skill."

    def format_hermes_tools_prompt(self, tools: Optional[List[ToolDefinition]] = None) -> str:
        """Format tools into standard Hermes 3 XML <tools> prompt schema."""
        selected_tools = tools if tools is not None else list(self._tools.values())
        tools_json_list = []
        for t in selected_tools:
            tools_json_list.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            })

        tools_str = json.dumps(tools_json_list, indent=2)
        hermes_prompt = (
            "<tools>\n"
            f"{tools_str}\n"
            "</tools>\n\n"
            "You have access to the above tools. To invoke a tool, you MUST use the following format:\n"
            "<tool_call>\n"
            '{"name": "tool_name", "arguments": {"arg_key": "arg_value"}}\n'
            "</tool_call>"
        )
        return hermes_prompt

    def parse_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Parse <tool_call>...</tool_call> tags from model output."""
        if not text:
            return []

        calls: List[Dict[str, Any]] = []
        xml_matches = re.findall(r"<tool_call>\s*(.*?)\s*</tool_call>", text, re.DOTALL)
        for match in xml_matches:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, dict) and "name" in parsed:
                    calls.append({
                        "name": str(parsed["name"]),
                        "arguments": parsed.get("arguments", {}),
                    })
            except Exception as e:
                logger.debug(f"Failed to parse tool call JSON: {match}. Error: {e}")

        if not calls:
            code_matches = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
            for match in code_matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, dict) and ("name" in parsed or "tool" in parsed):
                        name = parsed.get("name") or parsed.get("tool")
                        calls.append({
                            "name": str(name),
                            "arguments": parsed.get("arguments", parsed.get("parameters", {})),
                        })
                except Exception:
                    pass

        return calls

    def detect_loop_trigger(self, text: str) -> Tuple[bool, Optional[str]]:
        """Detect if prompt contains a /loop trigger."""
        if not text:
            return False, None
        match = re.search(r"/loop(?::|\b)\s*(.*)", text, re.IGNORECASE)
        if match:
            trigger_arg = match.group(1).strip()
            return True, trigger_arg
        return False, None

    def classify_and_route(
        self,
        payload: Optional[Dict[str, Any]] = None,
        prompt: Optional[str] = None,
        vector_pages_count: int = 0
    ) -> RoutingDecision:
        """
        Analyze incoming request and decide whether to route to:
        - HERMES_TOOL_ROUTER (Port 8083)
        - QWEN_CODE_GENERATOR (Port 8081)
        """
        req_payload = payload or {}
        user_text = prompt or ""

        if not user_text:
            if "prompt" in req_payload:
                user_text = str(req_payload["prompt"])
            elif "messages" in req_payload:
                for msg in reversed(req_payload.get("messages", [])):
                    if msg.get("role") == "user":
                        user_text = msg.get("content", "")
                        break

        # Check for /loop trigger
        has_loop, loop_arg = self.detect_loop_trigger(user_text)
        if has_loop:
            tools_to_invoke = [{
                "name": "loop_trigger",
                "arguments": {"task_description": loop_arg or "continuous self-optimization"}
            }]
            return RoutingDecision(
                engine="HERMES_TOOL_ROUTER",
                target_endpoint=self.hermes_url,
                model_id=self.master_model_id,
                tools_to_invoke=tools_to_invoke,
                vector_pages_paged=vector_pages_count,
                loop_triggered=True,
                reasoning="Active /loop command detected. Routing to Hermes 3 Tool Router on Port 8083.",
            )

        # If payload explicitly defines tools, dispatch to Hermes Tool Router
        if req_payload.get("tools") or req_payload.get("functions"):
            return RoutingDecision(
                engine="HERMES_TOOL_ROUTER",
                target_endpoint=self.hermes_url,
                model_id=self.master_model_id,
                tools_to_invoke=[],
                vector_pages_paged=vector_pages_count,
                loop_triggered=False,
                reasoning="Payload specifies tool schemas. Routing to Hermes 3 Tool Router on Port 8083.",
            )

        # Pure code completion patterns
        is_autocomplete = ("prompt" in req_payload and not req_payload.get("messages") and not req_payload.get("tools"))
        pure_code_patterns = [
            r"^\s*def\s+\w+\(",
            r"^\s*class\s+\w+",
            r"^\s*import\s+\w+",
            r"<\|fim_prefix\|>",
            r"<\|fim_suffix\|>",
        ]

        is_pure_code = is_autocomplete
        if not is_pure_code:
            for pat in pure_code_patterns:
                if re.search(pat, user_text, re.IGNORECASE):
                    is_pure_code = True
                    break

        if is_pure_code:
            return RoutingDecision(
                engine="QWEN_CODE_GENERATOR",
                target_endpoint=self.coder_url,
                model_id=self.coder_model_id,
                tools_to_invoke=[],
                vector_pages_paged=vector_pages_count,
                loop_triggered=False,
                reasoning="Syntax generation / code completion detected. Routing to Qwen 2.5 Coder on Port 8081.",
            )

        # Default to Hermes Tool Router for reasoning, tool dispatch, or questions
        return RoutingDecision(
            engine="HERMES_TOOL_ROUTER",
            target_endpoint=self.hermes_url,
            model_id=self.master_model_id,
            tools_to_invoke=[],
            vector_pages_paged=vector_pages_count,
            loop_triggered=False,
            reasoning="Task requires reasoning, tool discovery, or general assistance. Routing to Port 8083.",
        )

    def prepare_hermes_payload(
        self,
        payload: Dict[str, Any],
        tools: Optional[List[ToolDefinition]] = None
    ) -> Dict[str, Any]:
        """Inject Hermes 3 <tools> XML schema into the system message of the payload."""
        hermes_tools_str = self.format_hermes_tools_prompt(tools)
        modified_payload = dict(payload)
        messages = list(modified_payload.get("messages", []))

        if messages and messages[0].get("role") == "system":
            system_msg = dict(messages[0])
            system_msg["content"] = f"{system_msg.get('content', '')}\n\n{hermes_tools_str}"
            messages[0] = system_msg
        else:
            messages.insert(0, {
                "role": "system",
                "content": f"You are an autonomous Hermes 3 Tool Routing agent.\n\n{hermes_tools_str}"
            })

        modified_payload["messages"] = messages
        modified_payload["model"] = self.master_model_id
        return modified_payload

    def execute_routing_sync(
        self,
        payload: Dict[str, Any],
        timeout: float = 3.0
    ) -> Tuple[RoutingDecision, Optional[Dict[str, Any]]]:
        """Classify, prepare payload, and attempt execution against Hermes endpoint."""
        decision = self.classify_and_route(payload)
        if decision.engine != "HERMES_TOOL_ROUTER":
            return decision, None

        hermes_payload = self.prepare_hermes_payload(payload)
        req_data = json.dumps(hermes_payload).encode("utf-8")
        req = urllib.request.Request(
            self.hermes_url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    choices = resp_data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        decision.tools_to_invoke = self.parse_tool_calls(content)
                    return decision, resp_data
        except Exception as e:
            logger.debug(f"Hermes endpoint {self.hermes_url} call failed: {e}")

        return decision, None
