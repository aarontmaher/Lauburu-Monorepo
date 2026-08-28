## 2026-08-26T11:54:11Z
You are Explorer 2 focusing on Rule #0 Zero-Mock AST Linter & Discrimination Rubric.

Your working directory is: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_figma_2
Target report: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_figma_2/report.md
Handoff report: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_figma_2/handoff.md

Mandatory Input Files to read:
1. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md
2. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_spec_miner_survey_2/spec_report.md
3. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/orchestrator_figma_1/SCOPE.md
4. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/scripts/ai_claim_verifier.py
5. /Users/aaron/.gemini/config/skills/swarm/SKILL.md

Tasks:
1. Analyze the exact boundary between Permissible Structural Layout (HTML/JSX DOM hierarchy, CSS Flexbox/Grid, design tokens, dynamic state bindings {val ?? '--'}) and Forbidden Mock Data (hardcoded data literals like <span>142 bpm</span>, mock arrays const users = [...], synthetic setTimeout timers, fake API fixtures).
2. Formulate AST and regex parsing algorithms for TSX/JSX, Vue, HTML, and Python/Dart UI representations.
3. Design the pre-merge blocking mechanism (CLI tool that exits with code 1 upon detecting mock data and exit code 0 when clean).
4. Provide a detailed design for 06_scripts_and_tooling/scripts/figma_zero_mock_linter.py and 06_scripts_and_tooling/docs/FIGMA_ZERO_MOCK_SOP.md.

Hard Constraints:
- Read-only analysis. Do NOT modify source files directly.
- Write your complete findings to report.md and handoff.md in your working directory.
- Update progress.md as you work.
- Use send_message to report back when finished.
