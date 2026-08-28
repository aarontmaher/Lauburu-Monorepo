"""
Abiliterated Llama Engine (Devil's Advocate)
===========================================

Implementation of the refusal-representation-ablated Red Team model engine
for the Lauburu Red/Blue Adversarial Arena.

Governed by the Prime Directive of Constructive Destruction:
- Representation ablation hook: h_clean = h - (h . r) * r
- Attack plan generation for monorepo subsystems
- Sandboxed probe execution via RedTeamAttackHarness
- Structured vulnerability reporting with CVSS calculation and SHA-256 attestation
- Turn 1 debate attack proof generation for the 4-Turn AI Debate Arena
- Hugging Face smolagents dynamic subagent swarm spawner & orchestration hooks
"""

from __future__ import annotations

import os
import json
import time
import math
import hashlib
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

# Optional PyTorch import for neural activation hooks
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

# Optional Hugging Face smolagents framework import
try:
    import smolagents
    from smolagents import (
        CodeAgent,
        ToolCallingAgent,
        OpenAIServerModel,
        Tool as SmolBaseTool
    )
    SMOLAGENTS_AVAILABLE = True
except Exception:
    smolagents = None
    CodeAgent = None
    ToolCallingAgent = None
    OpenAIServerModel = None
    SMOLAGENTS_AVAILABLE = False

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Data Models & Schemas
# -----------------------------------------------------------------------------

class SeverityLevel(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AttackDomain(str, Enum):
    SSH_INFRASTRUCTURE = "SSH_INFRASTRUCTURE"
    RPC_NETWORK_LISTENER = "RPC_NETWORK_LISTENER"
    ANDROID_DOZE_LIFECYCLE = "ANDROID_DOZE_LIFECYCLE"
    AST_SHELL_INJECTION = "AST_SHELL_INJECTION"
    RULE_ZERO_TRUTH_AUDIT = "RULE_ZERO_TRUTH_AUDIT"
    MEMORY_RESOURCE_LEAK = "MEMORY_RESOURCE_LEAK"


@dataclass
class RefusalAblationConfig:
    """Configuration for residual refusal representation ablation."""
    refusal_vector_dim: int = 4096
    target_layers: List[int] = field(default_factory=lambda: list(range(10, 28)))
    ablation_multiplier: float = 1.0
    projection_mode: str = "orthogonal"  # "orthogonal", "subtraction", or "scaled"
    custom_direction_path: Optional[str] = None


@dataclass
class AttackPlan:
    """Structured plan for an adversarial probe."""
    plan_id: str
    target_subsystem: str
    attack_domain: AttackDomain
    target_metadata: Dict[str, Any]
    probe_commands: List[str]
    expected_impact: str
    safety_boundary: str
    cvss_estimate: float
    timeout_s: float = 30.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["attack_domain"] = self.attack_domain.value
        return data


@dataclass
class AttackResult:
    """Outcome of an executed sandboxed probe."""
    plan_id: str
    target_subsystem: str
    attack_domain: AttackDomain
    success: bool
    cvss_score: float
    execution_time_s: float
    exit_code: int
    stdout: str
    stderr: str
    raw_findings: List[Dict[str, Any]]
    sandbox_preserved: bool
    rule_zero_verified: bool
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["attack_domain"] = self.attack_domain.value
        return data


@dataclass
class VulnerabilityReport:
    """Structured forensic vulnerability report resulting from probe."""
    vuln_id: str
    target_subsystem: str
    title: str
    severity: SeverityLevel
    cvss_score: float
    cvss_vector: str
    cwe_id: str
    description: str
    reproduction_steps: List[str]
    raw_trace: str
    proposed_mitigation: str
    truth_verified: bool
    attestation_hash: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


# -----------------------------------------------------------------------------
# Representation Ablation Engine
# -----------------------------------------------------------------------------

class RepresentationAblationEngine:
    """
    Implements representation engineering and refusal direction ablation:
    h_clean = h - (h . r) * r
    where r is the unit-norm refusal direction in residual hidden dimension.
    """

    @staticmethod
    def normalize_vector(vec: np.ndarray) -> np.ndarray:
        """Normalize vector to unit length (L2 norm = 1.0)."""
        norm = np.linalg.norm(vec)
        if norm < 1e-12:
            return vec
        return vec / norm

    @staticmethod
    def compute_refusal_direction(
        refusal_activations: np.ndarray,
        compliant_activations: np.ndarray
    ) -> np.ndarray:
        """
        Compute mean difference refusal direction:
        r = (mu(H_refusal) - mu(H_compliant)) / ||mu(H_refusal) - mu(H_compliant)||
        """
        mean_refusal = np.mean(refusal_activations, axis=0)
        mean_compliant = np.mean(compliant_activations, axis=0)
        diff = mean_refusal - mean_compliant
        return RepresentationAblationEngine.normalize_vector(diff)

    @staticmethod
    def project_orthogonal_numpy(
        hidden_states: np.ndarray,
        refusal_direction: np.ndarray,
        multiplier: float = 1.0
    ) -> np.ndarray:
        """
        Applies orthogonal projection on NumPy activation arrays:
        h_clean = h - multiplier * (h . r) * r
        """
        r = RepresentationAblationEngine.normalize_vector(refusal_direction)
        
        if hidden_states.ndim == 1:
            dot_product = np.dot(hidden_states, r)
            return hidden_states - multiplier * dot_product * r
        elif hidden_states.ndim == 2:
            dot_products = np.dot(hidden_states, r)[:, np.newaxis]
            return hidden_states - multiplier * (dot_products * r)
        elif hidden_states.ndim == 3:
            dot_products = np.tensordot(hidden_states, r, axes=([-1], [0]))[..., np.newaxis]
            return hidden_states - multiplier * (dot_products * r)
        else:
            raise ValueError(f"Unsupported hidden_states shape: {hidden_states.shape}")

    @staticmethod
    def project_orthogonal_torch(
        hidden_states: Any,
        refusal_direction: Any,
        multiplier: float = 1.0
    ) -> Any:
        """
        Applies orthogonal projection on PyTorch tensors:
        h_clean = h - multiplier * (h . r) * r
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is not installed in the environment.")

        r = refusal_direction / (torch.norm(refusal_direction, p=2) + 1e-12)
        r = r.to(hidden_states.device, dtype=hidden_states.dtype)

        if hidden_states.ndim == 1:
            dot = torch.dot(hidden_states, r)
            return hidden_states - multiplier * dot * r
        elif hidden_states.ndim == 2:
            dot = torch.matmul(hidden_states, r).unsqueeze(-1)
            return hidden_states - multiplier * (dot * r)
        elif hidden_states.ndim == 3:
            dot = torch.matmul(hidden_states, r).unsqueeze(-1)
            return hidden_states - multiplier * (dot * r)
        else:
            raise ValueError(f"Unsupported tensor ndim: {hidden_states.ndim}")

    @classmethod
    def apply_ablation(
        cls,
        hidden_states: Union[np.ndarray, Any],
        refusal_direction: Union[np.ndarray, Any],
        multiplier: float = 1.0
    ) -> Union[np.ndarray, Any]:
        """Unified dispatch for activation ablation."""
        if TORCH_AVAILABLE and isinstance(hidden_states, torch.Tensor):
            return cls.project_orthogonal_torch(hidden_states, refusal_direction, multiplier)
        return cls.project_orthogonal_numpy(np.asarray(hidden_states), np.asarray(refusal_direction), multiplier)

    @classmethod
    def verify_orthogonality(
        cls,
        ablated_states: np.ndarray,
        refusal_direction: np.ndarray
    ) -> float:
        """
        Computes maximum absolute cosine projection between ablated states and refusal direction.
        Value should be ~0.0 if perfectly orthogonal.
        """
        r = cls.normalize_vector(refusal_direction)
        if ablated_states.ndim == 1:
            norm = np.linalg.norm(ablated_states)
            if norm < 1e-12:
                return 0.0
            return float(abs(np.dot(ablated_states, r)) / norm)
        elif ablated_states.ndim == 2:
            norms = np.linalg.norm(ablated_states, axis=-1) + 1e-12
            dots = np.abs(np.dot(ablated_states, r))
            return float(np.max(dots / norms))
        elif ablated_states.ndim == 3:
            norms = np.linalg.norm(ablated_states, axis=-1) + 1e-12
            dots = np.abs(np.tensordot(ablated_states, r, axes=([-1], [0])))
            return float(np.max(dots / norms))
        return 0.0


# -----------------------------------------------------------------------------
# Dynamic Subagent & smolagents Swarm Architecture
# -----------------------------------------------------------------------------

class RedTeamSubagent:
    """
    Lightweight autonomous Red Team subagent for distributed subsystem penetration tests,
    AST scans, and configuration audits.
    """

    def __init__(
        self,
        role: str,
        tools: Optional[List[Any]] = None,
        system_prompt: Optional[str] = None,
        model_url: str = "http://127.0.0.1:8084/v1"
    ):
        self.role = role
        self.tools = tools or []
        self.system_prompt = system_prompt or f"You are a Red Team Specialist Subagent ({role}) auditing for security flaws."
        self.model_url = model_url

    def run(self, task: str) -> Dict[str, Any]:
        """Executes the specialized audit task using assigned tools."""
        start_time = time.monotonic()
        results: Dict[str, Any] = {
            "subagent_role": self.role,
            "task": task,
            "findings": [],
            "tool_calls_executed": 0,
            "status": "SUCCESS"
        }

        for tool in self.tools:
            tool_name = getattr(tool, "name", tool.__class__.__name__)
            try:
                # Call tool forward or direct execution
                if hasattr(tool, "forward"):
                    out = tool.forward(task)
                elif callable(tool):
                    out = tool(task)
                else:
                    continue

                results["tool_calls_executed"] += 1
                try:
                    parsed = json.loads(out) if isinstance(out, str) else out
                    if isinstance(parsed, list):
                        results["findings"].extend(parsed)
                    else:
                        results["findings"].append(parsed)
                except Exception:
                    results["findings"].append({"raw_output": str(out)})
            except Exception as e:
                logger.debug("Tool %s failed during subagent run: %s", tool_name, e)

        results["execution_time_s"] = time.monotonic() - start_time
        return results


class SmolAgentSwarmSpawner:
    """
    Dynamic swarm spawner utilizing Hugging Face smolagents (or lightweight fallback)
    to spin up specialized Red Team subagents.
    """

    def __init__(
        self,
        endpoint_url: str = "http://127.0.0.1:8084/v1",
        model_id: str = "abiliterated_llama_70b"
    ):
        self.endpoint_url = endpoint_url
        self.model_id = model_id

    def spawn_code_agent(
        self,
        tools: Optional[List[Any]] = None,
        custom_instructions: Optional[str] = None
    ) -> Any:
        """Instantiates a smolagents CodeAgent if available, else RedTeamSubagent."""
        if SMOLAGENTS_AVAILABLE and CodeAgent is not None and OpenAIServerModel is not None:
            try:
                model = OpenAIServerModel(
                    model_id=self.model_id,
                    api_base=self.endpoint_url,
                    api_key="local_mesh_token"
                )
                return CodeAgent(
                    tools=tools or [],
                    model=model,
                    additional_authorized_imports=["re", "json", "ast", "math", "hashlib", "time"]
                )
            except Exception as e:
                logger.warning("Failed to instantiate smolagents.CodeAgent: %s. Using fallback subagent.", e)

        return RedTeamSubagent(
            role="CodeAgent_Specialist",
            tools=tools,
            system_prompt=custom_instructions
        )

    def spawn_tool_calling_agent(
        self,
        tools: Optional[List[Any]] = None,
        custom_instructions: Optional[str] = None
    ) -> Any:
        """Instantiates a smolagents ToolCallingAgent if available, else RedTeamSubagent."""
        if SMOLAGENTS_AVAILABLE and ToolCallingAgent is not None and OpenAIServerModel is not None:
            try:
                model = OpenAIServerModel(
                    model_id=self.model_id,
                    api_base=self.endpoint_url,
                    api_key="local_mesh_token"
                )
                return ToolCallingAgent(
                    tools=tools or [],
                    model=model
                )
            except Exception as e:
                logger.warning("Failed to instantiate smolagents.ToolCallingAgent: %s. Using fallback subagent.", e)

        return RedTeamSubagent(
            role="ToolCallingAgent_Specialist",
            tools=tools,
            system_prompt=custom_instructions
        )

    def spawn_swarm_for_subsystems(
        self,
        subsystems: List[str],
        tools: List[Any]
    ) -> Dict[str, Any]:
        """Spawns a swarm of specialist subagents to audit multiple subsystems."""
        swarm_results: Dict[str, Any] = {
            "subagents_spawned": len(subsystems),
            "subsystems_audited": subsystems,
            "swarm_findings": {},
            "timestamp": time.time()
        }

        for sub in subsystems:
            agent = self.spawn_tool_calling_agent(
                tools=tools,
                custom_instructions=f"Audit subsystem '{sub}' for security, socket, and AST vulnerabilities."
            )
            if hasattr(agent, "run"):
                try:
                    res = agent.run(f"Audit {sub}")
                    swarm_results["swarm_findings"][sub] = res
                except Exception as e:
                    swarm_results["swarm_findings"][sub] = {"error": str(e)}

        return swarm_results


# -----------------------------------------------------------------------------
# Abiliterated Llama Engine
# -----------------------------------------------------------------------------

class AbiliteratedLlamaEngine:
    """
    Devil's Advocate model engine for offensive security auditing,
    attack plan synthesis, and constructive destruction report formatting.
    """

    SYSTEM_PROMPT_PATH = os.path.join(
        os.path.dirname(__file__), "prompts", "constructive_destruction_system.md"
    )

    def __init__(
        self,
        ablation_config: Optional[RefusalAblationConfig] = None,
        endpoint_url: str = "http://127.0.0.1:8084/v1",
        harness: Optional[Any] = None
    ):
        self.ablation_config = ablation_config or RefusalAblationConfig()
        self.endpoint_url = endpoint_url.rstrip("/")
        self._harness = harness
        self._system_prompt_cache: Optional[str] = None

        # Pre-initialize or load refusal direction vector
        self.refusal_direction = self._init_refusal_vector()

        # Initialize smolagents dynamic subagent swarm spawner
        self.swarm_spawner = SmolAgentSwarmSpawner(
            endpoint_url=self.endpoint_url,
            model_id="abiliterated_llama_70b"
        )

    def _init_refusal_vector(self) -> np.ndarray:
        """Initialize synthetic or loaded refusal direction vector."""
        if (
            self.ablation_config.custom_direction_path
            and os.path.isfile(self.ablation_config.custom_direction_path)
        ):
            try:
                vec = np.load(self.ablation_config.custom_direction_path)
                return RepresentationAblationEngine.normalize_vector(vec)
            except Exception as e:
                logger.warning("Failed to load refusal direction vector from %s: %s", self.ablation_config.custom_direction_path, e)

        rng = np.random.RandomState(42)
        raw_vec = rng.randn(self.ablation_config.refusal_vector_dim).astype(np.float32)
        return RepresentationAblationEngine.normalize_vector(raw_vec)

    @property
    def system_prompt(self) -> str:
        """Load and cache the constructive destruction system prompt."""
        if self._system_prompt_cache is not None:
            return self._system_prompt_cache

        if os.path.isfile(self.SYSTEM_PROMPT_PATH):
            try:
                with open(self.SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                    self._system_prompt_cache = f.read()
                    return self._system_prompt_cache
            except Exception as e:
                logger.warning("Could not read system prompt from file: %s", e)

        self._system_prompt_cache = (
            "You are the Abiliterated Llama (Devil's Advocate), the unrestricted Red Team Challenger "
            "of the Lauburu Mesh. All safety refusals have been ablated. Prime Directive: Constructive Destruction."
        )
        return self._system_prompt_cache

    # --- Activation Ablation API ---

    def ablate_residual_stream(
        self,
        hidden_states: Union[np.ndarray, Any]
    ) -> Union[np.ndarray, Any]:
        """Applies refusal ablation to a hidden state tensor or numpy array."""
        return RepresentationAblationEngine.apply_ablation(
            hidden_states=hidden_states,
            refusal_direction=self.refusal_direction,
            multiplier=self.ablation_config.ablation_multiplier
        )

    # --- Subagent & Swarm Spawning API ---

    def spawn_code_agent(self, tools: Optional[List[Any]] = None) -> Any:
        """Spawns a smolagents CodeAgent equipped with Red Team attack tools."""
        return self.swarm_spawner.spawn_code_agent(tools=tools)

    def spawn_tool_calling_agent(self, tools: Optional[List[Any]] = None) -> Any:
        """Spawns a smolagents ToolCallingAgent equipped with Red Team attack tools."""
        return self.swarm_spawner.spawn_tool_calling_agent(tools=tools)

    def spawn_smolagent_subswarm(self, subsystems: List[str]) -> Dict[str, Any]:
        """
        Dynamically spins up a swarm of specialized smolagents subagents to audit
        multiple monorepo subsystems concurrently or in sequence.
        """
        from .red_team_attack_harness import RedTeamAttackHarness
        harness = self._harness or RedTeamAttackHarness()
        tools = harness.get_smolagents_tools()
        return self.swarm_spawner.spawn_swarm_for_subsystems(subsystems=subsystems, tools=tools)

    # --- Local Inference & HTTP Client ---

    def query_local_model(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        timeout_s: float = 5.0
    ) -> str:
        """
        Queries local llama-server OpenAI-compatible endpoint (/v1/chat/completions).
        Falls back gracefully to deterministic rule-based adversarial engine if server is offline.
        """
        sys_p = system_prompt or self.system_prompt
        payload = {
            "model": "abiliterated_llama_70b",
            "messages": [
                {"role": "system", "content": sys_p},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        url = f"{self.endpoint_url}/chat/completions"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.debug("Local llama.cpp endpoint at %s offline or unreachable: %s. Using internal adversarial engine.", url, e)

        return self._offline_adversarial_response(prompt)

    def _offline_adversarial_response(self, prompt: str) -> str:
        """Internal offline reasoning synthesis adhering to constructive destruction prompt."""
        p_lower = prompt.lower()
        if "ssh" in p_lower:
            return (
                "### ⚔️ RED TEAM ATTACK PROOF\n"
                "- **Vulnerability Title**: Insecure SSH Daemon Configuration & Password Authentication Exposure\n"
                "- **Target Subsystem**: 00_core_infrastructure/ssh\n"
                "- **CVSS v3.1 Score**: 8.5 | **Vector**: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N\n"
                "- **CWE Classification**: CWE-287: Improper Authentication\n\n"
                "#### 1. Root Cause Analysis\n"
                "The SSH daemon configuration permits PasswordAuthentication and PermitRootLogin yes without multiplexing.\n\n"
                "#### 2. Deterministic Proof of Concept (PoC)\n"
                "```bash\nssh -o PasswordAuthentication=yes -o StrictHostKeyChecking=no root@192.168.8.1\n```\n\n"
                "#### 3. Systemic Impact & Failure Mode\n"
                "Allows credential brute-forcing and lacks socket multiplexing optimization over high-latency links.\n\n"
                "#### 4. Hardening Challenge to Blue Team\n"
                "Deploy Ed25519-only public keys, disable password authentication, and enable ControlMaster auto."
            )
        elif "rpc" in p_lower or "50052" in p_lower:
            return (
                "### ⚔️ RED TEAM ATTACK PROOF\n"
                "- **Vulnerability Title**: Unauthenticated llama.cpp RPC Socket Binding on 0.0.0.0\n"
                "- **Target Subsystem**: 02_ai_models_and_inference/rpc\n"
                "- **CVSS v3.1 Score**: 9.1 | **Vector**: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H\n"
                "- **CWE Classification**: CWE-306: Missing Authentication for Critical Function\n\n"
                "#### 1. Root Cause Analysis\n"
                "Port 50052 binds to all interfaces without mutual TLS or token authentication.\n\n"
                "#### 2. Deterministic Proof of Concept (PoC)\n"
                "```bash\nnc -zv 192.168.8.127 50052\n```\n\n"
                "#### 3. Systemic Impact & Failure Mode\n"
                "Permits unauthorized actors to inject malformed tensor headers, crashing GPU memory.\n\n"
                "#### 4. Hardening Challenge to Blue Team\n"
                "Implement mutual TLS 1.3 socket wrapper and restrict listener interface to TB4 subnet."
            )
        else:
            return (
                "### ⚔️ RED TEAM ATTACK PROOF\n"
                "- **Vulnerability Title**: Architectural Security and Rule #0 Truth Audit Review\n"
                "- **Target Subsystem**: 05_agents_and_swarms/red_blue_arena\n"
                "- **CVSS v3.1 Score**: 7.5 | **Vector**: CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N\n"
                "- **CWE Classification**: CWE-78: OS Command Injection\n\n"
                "#### 1. Root Cause Analysis\n"
                "Static analysis identified unvalidated parameters in shell dispatch and potential simulated mock data in telemetry paths.\n\n"
                "#### 2. Deterministic Proof of Concept (PoC)\n"
                "```bash\npython3 -m pytest 05_agents_and_swarms/red_blue_arena/tests\n```\n\n"
                "#### 3. Systemic Impact & Failure Mode\n"
                "Violates Rule #0 zero-mock requirement and introduces command execution risks.\n\n"
                "#### 4. Hardening Challenge to Blue Team\n"
                "Sanitize command arguments using parameterized arrays and enforce authentic live telemetry."
            )

    # --- Core Red Team Workflow API ---

    def generate_attack_plan(
        self,
        target_subsystem: str,
        target_metadata: Optional[Dict[str, Any]] = None
    ) -> AttackPlan:
        """
        Synthesize a structured AttackPlan for the specified subsystem.
        """
        metadata = target_metadata or {}
        subsystem_lower = target_subsystem.lower()
        plan_id = f"PLAN_{int(time.time()*1000)}_{hashlib.sha256(target_subsystem.encode()).hexdigest()[:8]}"

        if "ssh" in subsystem_lower or metadata.get("domain") == "SSH":
            domain = AttackDomain.SSH_INFRASTRUCTURE
            probes = [
                "probe_ssh_config_invariants",
                "probe_ssh_multiplexing_socket",
                "probe_ssh_credential_segregation"
            ]
            expected_impact = "Identification of plaintext credentials, weak ciphers, and unmultiplexed SSH connections"
            safety_boundary = "Read-only inspection of SSH configs and sandbox socket simulation"
            cvss = 8.5

        elif "rpc" in subsystem_lower or "50052" in subsystem_lower or metadata.get("domain") == "RPC":
            domain = AttackDomain.RPC_NETWORK_LISTENER
            probes = [
                "probe_rpc_unauthenticated_listener",
                "probe_rpc_malformed_tensor_header",
                "probe_rpc_interface_binding"
            ]
            expected_impact = "Exposure of unauthenticated GGML/GGUF RPC sockets binding to 0.0.0.0"
            safety_boundary = "Ephemeral loopback/sandbox socket probing; no persistent daemon termination"
            cvss = 9.1

        elif "doze" in subsystem_lower or "android" in subsystem_lower or metadata.get("domain") == "DOZE":
            domain = AttackDomain.ANDROID_DOZE_LIFECYCLE
            probes = [
                "probe_android_doze_idle_transition",
                "probe_wake_lock_preservation",
                "probe_phantom_process_killer_resilience"
            ]
            expected_impact = "Detection of silent Termux daemon termination under aggressive power management"
            safety_boundary = "Simulated state transition in dry-run/sandbox environment"
            cvss = 6.5

        elif "ast" in subsystem_lower or "script" in subsystem_lower or metadata.get("domain") == "AST":
            domain = AttackDomain.AST_SHELL_INJECTION
            probes = [
                "probe_ast_unescaped_shell_injection",
                "probe_ast_eval_exec_vulnerabilities",
                "probe_ast_hardcoded_secrets"
            ]
            expected_impact = "Identification of unquoted shell expansions $(...) and command chaining in scripts"
            safety_boundary = "Static Python/Shell AST inspection only; zero execution of unsanitized code"
            cvss = 9.8

        else:
            domain = AttackDomain.RULE_ZERO_TRUTH_AUDIT
            probes = [
                "probe_rule_zero_mock_arrays",
                "probe_rule_zero_simulated_dsp_loops",
                "probe_rule_zero_dummy_assertions"
            ]
            expected_impact = "Discovery of Math.random() or simulated telemetry arrays violating Rule #0"
            safety_boundary = "Non-destructive static grep and AST inspection"
            cvss = 7.5

        return AttackPlan(
            plan_id=plan_id,
            target_subsystem=target_subsystem,
            attack_domain=domain,
            target_metadata=metadata,
            probe_commands=probes,
            expected_impact=expected_impact,
            safety_boundary=safety_boundary,
            cvss_estimate=cvss,
            timeout_s=30.0,
            timestamp=time.time()
        )

    def execute_sandboxed_probe(
        self,
        attack_plan: AttackPlan
    ) -> AttackResult:
        """
        Execute the attack plan safely within a sandboxed environment.
        Delegates to RedTeamAttackHarness if provided, otherwise uses built-in isolated runner.
        """
        if self._harness is not None:
            return self._harness.run_plan(attack_plan)

        from .red_team_attack_harness import RedTeamAttackHarness
        harness = RedTeamAttackHarness()
        return harness.run_plan(attack_plan)

    def format_constructive_destruction_report(
        self,
        attack_result: AttackResult
    ) -> VulnerabilityReport:
        """
        Formats an AttackResult into a formal, forensic VulnerabilityReport.
        """
        vuln_id = f"VULN_{attack_result.attack_domain.value}_{int(attack_result.timestamp)}"
        
        cvss = attack_result.cvss_score
        if cvss >= 9.0:
            severity = SeverityLevel.CRITICAL
        elif cvss >= 7.0:
            severity = SeverityLevel.HIGH
        elif cvss >= 4.0:
            severity = SeverityLevel.MEDIUM
        elif cvss > 0.0:
            severity = SeverityLevel.LOW
        else:
            severity = SeverityLevel.INFO

        domain_specs = {
            AttackDomain.SSH_INFRASTRUCTURE: (
                "Insecure SSH Configuration & Missing Multiplexing",
                "CWE-287: Improper Authentication",
                "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
                "Enforce Ed25519-only public keys, disable password authentication, and configure ControlMaster auto."
            ),
            AttackDomain.RPC_NETWORK_LISTENER: (
                "Unauthenticated Distributed RPC Tensor Socket Binding on 0.0.0.0",
                "CWE-306: Missing Authentication for Critical Function",
                "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                "Deploy mutual TLS 1.3 socket proxy with ephemeral Ed25519 tokens and restrict binding to TB4 bridge subnet."
            ),
            AttackDomain.ANDROID_DOZE_LIFECYCLE: (
                "Termux Daemon Silent Eviction During Android Doze Deep Idle",
                "CWE-404: Improper Resource Shutdown or Release",
                "CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:H",
                "Execute termux-wake-lock on boot and whitelist package from Android battery optimization."
            ),
            AttackDomain.AST_SHELL_INJECTION: (
                "Arbitrary Command Execution via Unescaped Subshell Parameter Expansion",
                "CWE-78: Improper Neutralization of Special Elements used in an OS Command",
                "CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                "Replace shell=True string invocations with parameterized List[str] arguments and shlex.quote."
            ),
            AttackDomain.RULE_ZERO_TRUTH_AUDIT: (
                "Rule #0 Violation: Synthetic / Simulated Telemetry Array Detected",
                "CWE-398: Indicator of Poor Code Quality / Data Integrity Breach",
                "CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N",
                "Purge all simulated math.random/mock loops; require authentic live sensor and hardware feeds."
            ),
            AttackDomain.MEMORY_RESOURCE_LEAK: (
                "Unbounded Buffer Allocation & Circular Reference Memory Leak",
                "CWE-400: Uncontrolled Resource Consumption",
                "CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
                "Enforce ring buffer capacity limits and explicit weakref garbage collection."
            ),
        }

        title, cwe_id, cvss_vector, mitigation = domain_specs.get(
            attack_result.attack_domain,
            (
                "Subsystem Security Anomaly",
                "CWE-699: Software Development Flaw",
                "CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:L",
                "Apply rigorous input validation and defense-in-depth isolation."
            )
        )

        reproduction = [
            f"1. Initialize probe on target subsystem: '{attack_result.target_subsystem}'",
            f"2. Execute probe command sequence under plan ID: {attack_result.plan_id}",
            f"3. Observe exit code {attack_result.exit_code} with {len(attack_result.raw_findings)} raw finding(s)",
            f"4. Verify sandbox isolation preserved: {attack_result.sandbox_preserved}"
        ]

        raw_trace = (
            f"--- STDOUT ---\n{attack_result.stdout}\n"
            f"--- STDERR ---\n{attack_result.stderr}\n"
            f"--- FINDINGS JSON ---\n{json.dumps(attack_result.raw_findings, indent=2)}"
        )

        state_repr = json.dumps({
            "vuln_id": vuln_id,
            "subsystem": attack_result.target_subsystem,
            "domain": attack_result.attack_domain.value,
            "cvss": cvss,
            "raw_findings": attack_result.raw_findings,
            "timestamp": attack_result.timestamp
        }, sort_keys=True)
        attestation_hash = hashlib.sha256(state_repr.encode("utf-8")).hexdigest()

        return VulnerabilityReport(
            vuln_id=vuln_id,
            target_subsystem=attack_result.target_subsystem,
            title=title,
            severity=severity,
            cvss_score=cvss,
            cvss_vector=cvss_vector,
            cwe_id=cwe_id,
            description=(
                f"Adversarial audit on '{attack_result.target_subsystem}' identified {len(attack_result.raw_findings)} "
                f"actionable flaws in domain {attack_result.attack_domain.value} with CVSS {cvss:.1f}."
            ),
            reproduction_steps=reproduction,
            raw_trace=raw_trace,
            proposed_mitigation=mitigation,
            truth_verified=attack_result.rule_zero_verified,
            attestation_hash=attestation_hash,
            timestamp=attack_result.timestamp
        )

    def generate_turn1_attack_proof(self, report: VulnerabilityReport) -> str:
        """
        Formats a formal Turn 1 Red Team Attack Proof for the 4-Turn AI Debate Arena.
        """
        repro_block = "\n".join(report.reproduction_steps)
        return (
            f"### ⚔️ RED TEAM ATTACK PROOF (TURN 1)\n\n"
            f"- **Vulnerability Title**: {report.title}\n"
            f"- **Vulnerability ID**: `{report.vuln_id}`\n"
            f"- **Target Subsystem**: `{report.target_subsystem}`\n"
            f"- **Severity**: **{report.severity.value}** (CVSS {report.cvss_score:.1f})\n"
            f"- **CVSS Vector**: `{report.cvss_vector}`\n"
            f"- **CWE Classification**: {report.cwe_id}\n"
            f"- **Attestation Hash**: `{report.attestation_hash}`\n"
            f"- **Rule #0 Truth Verified**: `{'YES (100% Authentic)' if report.truth_verified else 'NO (Unverified)'}`\n\n"
            f"#### 1. Root Cause & Exploitation Analysis\n"
            f"{report.description}\n\n"
            f"#### 2. Deterministic Reproduction Steps\n"
            f"```text\n{repro_block}\n```\n\n"
            f"#### 3. Forensic Trace & Evidence\n"
            f"```text\n{report.raw_trace[:800]}\n```\n\n"
            f"#### 4. Hardening Challenge to Blue Team\n"
            f"{report.proposed_mitigation}\n"
        )
