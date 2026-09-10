---
title: "AI Debate: Generation 2 Mutation - UI Testing Hygiene"
---
# ⚔️ AI Debate: Gen 2 Mutation
[ROUND 1: GEMINI ULTRA (ARCHITECT)]
The UI/UX is built, but process hygiene is nonexistent. We must mutate the swarm prompt for Gen 2: ALL Playwright tests must be intercepted by a centralized test runner wrapper that hardcodes `headless=True` and wraps execution in a robust `try/finally` block that explicitly calls `os.kill(pgid, signal.SIGKILL)` on browser exit.
[ROUND 2: QWEN 80B (LOCAL ORCHESTRATOR)]
Agreed. Furthermore, concurrent challengers should be limited to `max_workers=2` in `pytest` to prevent CPU and RAM starvation on the Mac Mini.
[ROUND 3: DEVIL'S ADVOCATE]
What if a test runner wrapper fails? Gen 2 must also deploy a cron-based 'Sweeper Daemon' that runs `pgrep -fl Google Chrome` every 60 seconds and kills any instance spawned by `pytest` or `playwright` that exceeds a 5-minute TTL.

## 🏆 Final Consensus
[FINAL CONSENSUS — SCORE 0.99]
Generation 2 Mutation Directives:
1. Hardcode `--headless=new` in `conftest.py`.
2. Limit concurrent UI adversarial tests to 2 workers.
3. Deploy a Sweeper Daemon (5-minute TTL for headless browsers).
4. Resume UI polish on SeaweedFS IDE.
