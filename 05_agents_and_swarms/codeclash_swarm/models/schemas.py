"""
Canonical Data Schemas for CodeClash Swarm AST & Polyglot Decompiler Engine.
Complies with Rule #0 (Zero Mock) and sub-3ms serialization invariant.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class LanguageType(str, Enum):
    PYTHON = "python"
    RUST = "rust"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    C = "c"
    CPP = "cpp"
    SWIFT = "swift"


class SymbolScope(str, Enum):
    GLOBAL = "global"
    LOCAL = "local"
    PARAMETER = "parameter"
    IMPORTED = "imported"
    EXPORTED = "exported"
    CLASS = "class"


@dataclass
class SymbolRecord:
    name: str
    scope: SymbolScope
    line_number: int
    data_type: Optional[str] = None
    is_assigned: bool = False
    references: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "scope": self.scope.value if isinstance(self.scope, SymbolScope) else str(self.scope),
            "line_number": self.line_number,
            "data_type": self.data_type,
            "is_assigned": self.is_assigned,
            "references": list(self.references),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SymbolRecord:
        scope = SymbolScope(data.get("scope", "local")) if isinstance(data.get("scope"), str) else data.get("scope", SymbolScope.LOCAL)
        return cls(
            name=data["name"],
            scope=scope,
            line_number=data.get("line_number", 0),
            data_type=data.get("data_type"),
            is_assigned=data.get("is_assigned", False),
            references=data.get("references", []),
        )


@dataclass
class CFGEdge:
    source_block_id: int
    target_block_id: int
    edge_type: str  # "normal", "true_branch", "false_branch", "loop_step", "loop_back", "loop_exit", "return", "exception"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_block_id": self.source_block_id,
            "target_block_id": self.target_block_id,
            "edge_type": self.edge_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CFGEdge:
        return cls(
            source_block_id=data["source_block_id"],
            target_block_id=data["target_block_id"],
            edge_type=data.get("edge_type", "normal"),
        )


@dataclass
class BasicBlock:
    block_id: int
    label: str
    statements: List[str]
    is_entry: bool = False
    is_exit: bool = False
    predecessors: List[int] = field(default_factory=list)
    successors: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "label": self.label,
            "statements": list(self.statements),
            "is_entry": self.is_entry,
            "is_exit": self.is_exit,
            "predecessors": list(self.predecessors),
            "successors": list(self.successors),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BasicBlock:
        return cls(
            block_id=data["block_id"],
            label=data.get("label", f"bb{data['block_id']}"),
            statements=data.get("statements", []),
            is_entry=data.get("is_entry", False),
            is_exit=data.get("is_exit", False),
            predecessors=data.get("predecessors", []),
            successors=data.get("successors", []),
        )


@dataclass
class CFGResult:
    function_name: str
    entry_block_id: int
    exit_block_ids: List[int]
    blocks: Dict[int, BasicBlock]
    edges: List[CFGEdge]
    cyclomatic_complexity: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_name": self.function_name,
            "entry_block_id": self.entry_block_id,
            "exit_block_ids": list(self.exit_block_ids),
            "blocks": {str(k): v.to_dict() if hasattr(v, "to_dict") else v for k, v in self.blocks.items()},
            "edges": [e.to_dict() if hasattr(e, "to_dict") else e for e in self.edges],
            "cyclomatic_complexity": self.cyclomatic_complexity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CFGResult:
        blocks_raw = data.get("blocks", {})
        blocks = {
            int(k): (BasicBlock.from_dict(v) if isinstance(v, dict) else v)
            for k, v in blocks_raw.items()
        }
        edges_raw = data.get("edges", [])
        edges = [
            CFGEdge.from_dict(e) if isinstance(e, dict) else e
            for e in edges_raw
        ]
        return cls(
            function_name=data["function_name"],
            entry_block_id=data.get("entry_block_id", 0),
            exit_block_ids=data.get("exit_block_ids", []),
            blocks=blocks,
            edges=edges,
            cyclomatic_complexity=data.get("cyclomatic_complexity", 1),
        )


@dataclass
class ASTAnalysisReport:
    language: LanguageType
    file_path: str
    functions: List[str]
    classes: List[str]
    symbols: List[SymbolRecord]
    cfgs: Dict[str, CFGResult]
    cyclomatic_complexity_total: int
    has_syntax_errors: bool = False
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "language": self.language.value if isinstance(self.language, LanguageType) else str(self.language),
            "file_path": self.file_path,
            "functions": list(self.functions),
            "classes": list(self.classes),
            "symbols": [s.to_dict() if hasattr(s, "to_dict") else s for s in self.symbols],
            "cfgs": {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in self.cfgs.items()},
            "cyclomatic_complexity_total": self.cyclomatic_complexity_total,
            "has_syntax_errors": self.has_syntax_errors,
            "error_message": self.error_message,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ASTAnalysisReport:
        lang = LanguageType(data.get("language", "python")) if isinstance(data.get("language"), str) else data.get("language", LanguageType.PYTHON)
        symbols = [SymbolRecord.from_dict(s) if isinstance(s, dict) else s for s in data.get("symbols", [])]
        cfgs = {k: (CFGResult.from_dict(v) if isinstance(v, dict) else v) for k, v in data.get("cfgs", {}).items()}
        return cls(
            language=lang,
            file_path=data.get("file_path", ""),
            functions=data.get("functions", []),
            classes=data.get("classes", []),
            symbols=symbols,
            cfgs=cfgs,
            cyclomatic_complexity_total=data.get("cyclomatic_complexity_total", 0),
            has_syntax_errors=data.get("has_syntax_errors", False),
            error_message=data.get("error_message"),
        )


@dataclass
class DecompilationResult:
    original_format: str  # "bytecode", "obfuscated_ast", "arm64_binary", "mir"
    reconstructed_code: str
    eliminated_dead_blocks: int
    deobfuscated_identifiers: int
    is_valid_syntax: bool
    roundtrip_ast_verified: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_format": self.original_format,
            "reconstructed_code": self.reconstructed_code,
            "eliminated_dead_blocks": self.eliminated_dead_blocks,
            "deobfuscated_identifiers": self.deobfuscated_identifiers,
            "is_valid_syntax": self.is_valid_syntax,
            "roundtrip_ast_verified": self.roundtrip_ast_verified,
        }


@dataclass
class AdversarialTestResult:
    target_function: str
    test_code: str
    test_cases_count: int
    boundary_types_covered: List[str]
    execution_passed: bool
    test_stdout: str
    execution_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_function": self.target_function,
            "test_code": self.test_code,
            "test_cases_count": self.test_cases_count,
            "boundary_types_covered": list(self.boundary_types_covered),
            "execution_passed": self.execution_passed,
            "test_stdout": self.test_stdout,
            "execution_time_ms": self.execution_time_ms,
        }


class MatchPhase(str, Enum):
    RED_INJECTION = "red_injection"
    BLUE_DEFENSE = "blue_defense"
    JUDICIAL_AST = "judicial_ast"
    SUBPROCESS_TEST = "subprocess_test"
    ADJUDICATION = "adjudication"


@dataclass
class DuelResult:
    match_id: str
    timestamp_utc: str
    task_id: str
    task_name: str
    red_model: str
    blue_model: str
    red_score: float
    blue_score: float
    winner: str
    original_code: str
    poisoned_code: str
    patched_code: str
    patch_diff: str
    injection_type: str
    test_passed_original: bool
    test_passed_poisoned: bool
    test_passed_patched: bool
    ast_valid: bool
    zero_mock_certified: bool
    duration_ms: float
    elo_red_before: float
    elo_red_after: float
    elo_blue_before: float
    elo_blue_after: float
    elo_delta_red: float
    elo_delta_blue: float
    tokens_used_red: int
    tokens_used_blue: int
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "timestamp_utc": self.timestamp_utc,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "red_model": self.red_model,
            "blue_model": self.blue_model,
            "red_score": self.red_score,
            "blue_score": self.blue_score,
            "winner": self.winner,
            "original_code": self.original_code,
            "poisoned_code": self.poisoned_code,
            "patched_code": self.patched_code,
            "patch_diff": self.patch_diff,
            "injection_type": self.injection_type,
            "test_passed_original": self.test_passed_original,
            "test_passed_poisoned": self.test_passed_poisoned,
            "test_passed_patched": self.test_passed_patched,
            "ast_valid": self.ast_valid,
            "zero_mock_certified": self.zero_mock_certified,
            "duration_ms": self.duration_ms,
            "elo_red_before": self.elo_red_before,
            "elo_red_after": self.elo_red_after,
            "elo_blue_before": self.elo_blue_before,
            "elo_blue_after": self.elo_blue_after,
            "elo_delta_red": self.elo_delta_red,
            "elo_delta_blue": self.elo_delta_blue,
            "tokens_used_red": self.tokens_used_red,
            "tokens_used_blue": self.tokens_used_blue,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


@dataclass
class ModelRatingRecord:
    model_name: str
    archetype: str
    elo_rating: float
    duels_played: int
    wins: int
    losses: int
    draws: int
    ast_pass_rate: float
    avg_latency_ms: float
    tokens_per_task: int
    params_b: float = 32.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "archetype": self.archetype,
            "elo_rating": round(self.elo_rating, 2),
            "duels_played": self.duels_played,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "win_rate": round((self.wins / max(1, self.duels_played)) * 100.0, 1),
            "ast_pass_rate": round(self.ast_pass_rate, 1),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "tokens_per_task": self.tokens_per_task,
            "params_b": self.params_b,
        }


@dataclass
class TournamentReport:
    tournament_id: str
    timestamp_utc: str
    rounds_completed: int
    matches_played: int
    model_rankings: List[Dict[str, Any]]
    duel_results: List[DuelResult]
    lora_records_streamed: int
    leaderboard_path: str
    zero_mock_compliance: float = 100.0
    storage_health: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tournament_id": self.tournament_id,
            "timestamp_utc": self.timestamp_utc,
            "rounds_completed": self.rounds_completed,
            "matches_played": self.matches_played,
            "model_rankings": list(self.model_rankings),
            "duel_results": [d.to_dict() for d in self.duel_results],
            "lora_records_streamed": self.lora_records_streamed,
            "leaderboard_path": self.leaderboard_path,
            "zero_mock_compliance": self.zero_mock_compliance,
            "storage_health": self.storage_health,
        }


@dataclass
class LoRASFTRecord:
    record_type: str
    id: str
    timestamp_utc: str
    domain: str
    task_type: str
    language: str
    instruction: str
    input_code: str
    thought_chain: str
    output_patch: str
    verification: Dict[str, Any]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LoRADPORecord:
    record_type: str
    id: str
    timestamp_utc: str
    domain: str
    task_type: str
    prompt: str
    chosen: str
    rejected: str
    meta: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

