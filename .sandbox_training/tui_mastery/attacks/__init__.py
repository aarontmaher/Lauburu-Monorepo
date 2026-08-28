"""Red Team 5-Tier Attack Engine Package.

Provides adversarial stressors and fuzzing modules:
- SigwinchStressor (SIGWINCH resize storms)
- EventFloodStressor (1,000 keys/sec flood & telemetry torrents)
- MemoryStressor (RSS pressure and buffer exhaustion detector)
- SchemaFuzzer (15 mutation payload classes)
- LockContentionStressor (POSIX flock hijacking and atomic rename races)
"""

from .event_flood import EventFloodResult, EventFloodStressor
from .lock_contention import LockContentionResult, LockContentionStressor
from .memory_stressor import MemoryStressResult, MemoryStressor
from .schema_fuzzer import FuzzExecutionResult, FuzzSuiteResult, FuzzTestCase, SchemaFuzzer, get_fuzz_corpus
from .sigwinch_storm import SigwinchAttackResult, SigwinchStressor

__all__ = [
    "SigwinchStressor",
    "SigwinchAttackResult",
    "EventFloodStressor",
    "EventFloodResult",
    "MemoryStressor",
    "MemoryStressResult",
    "SchemaFuzzer",
    "FuzzSuiteResult",
    "FuzzExecutionResult",
    "FuzzTestCase",
    "get_fuzz_corpus",
    "LockContentionStressor",
    "LockContentionResult",
]
