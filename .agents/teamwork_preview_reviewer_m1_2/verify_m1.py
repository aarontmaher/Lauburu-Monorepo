import os, sys, json, yaml

print("=== 1. VERIFY DIRECTORY STRUCTURE ===")
base = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.sandbox_training/tui_mastery"
required_dirs = [
    "config",
    "config/specialists",
    "defenses",
    "defenses/python_textual",
    "defenses/go_bubbletea",
    "defenses/rust_ratatui",
    "attacks",
    "referee",
    "logs",
    "benchmarks"
]
for d in required_dirs:
    p = os.path.join(base, d)
    assert os.path.isdir(p), f"Directory missing: {p}"
    print(f"  [OK] Directory exists: {d}")

print("\n=== 2. VERIFY SKILL.MD FILES & YAML FRONTMATTER ===")
skills = [
    ("polyglot-python-textual-specialist", "/Users/aaron/.gemini/config/skills/polyglot-python-textual-specialist/SKILL.md", ["TCSS", "asyncio", "Zero-Mock", "Rule #0", "SIGWINCH"]),
    ("polyglot-go-bubbletea-specialist", "/Users/aaron/.gemini/config/skills/polyglot-go-bubbletea-specialist/SKILL.md", ["Elm", "Lipgloss", "Zero-Mock", "Rule #0", "WindowSizeMsg"]),
    ("polyglot-rust-ratatui-specialist", "/Users/aaron/.gemini/config/skills/polyglot-rust-ratatui-specialist/SKILL.md", ["Immediate-Mode", "Tokio", "Zero-Mock", "Rule #0", "panic"]),
]

for skill_name, skill_path, keywords in skills:
    assert os.path.isfile(skill_path), f"File missing: {skill_path}"
    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()
    parts = content.split("---")
    assert len(parts) >= 3, f"Invalid YAML frontmatter in {skill_path}"
    fm = yaml.safe_load(parts[1])
    assert fm.get("name") == skill_name, f"Expected name {skill_name}, got {fm.get('name')}"
    assert "description" in fm and len(fm["description"]) > 10, f"Missing description in {skill_path}"
    body = "---".join(parts[2:])
    for kw in keywords:
        assert kw in body, f"Keyword {kw} missing in {skill_path}"
    print(f"  [OK] Skill verified: {skill_name} ({len(content)} bytes)")

print("\n=== 3. VERIFY SPECIALIST JSON PROFILES ===")
expected_keys = {"name", "archetype", "framework", "language", "system_prompt", "core_competencies", "defensive_patterns", "zero_mock_enforcement"}
profiles = [
    ("python_textual.json", "polyglot-python-textual-specialist", "textual", "python"),
    ("go_bubbletea.json", "polyglot-go-bubbletea-specialist", "bubbletea", "go"),
    ("rust_ratatui.json", "polyglot-rust-ratatui-specialist", "ratatui", "rust")
]

for fn, name, fw, lang in profiles:
    p = os.path.join(base, "config/specialists", fn)
    assert os.path.isfile(p), f"Profile missing: {p}"
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert set(data.keys()) == expected_keys, f"Keys mismatch in {fn}: {set(data.keys()) ^ expected_keys}"
    assert data["name"] == name, f"Name mismatch in {fn}: {data['name']}"
    assert data["framework"] == fw, f"Framework mismatch in {fn}: {data['framework']}"
    assert data["language"] == lang, f"Language mismatch in {fn}: {data['language']}"
    assert data["zero_mock_enforcement"] is True, f"zero_mock_enforcement must be True in {fn}"
    assert len(data["core_competencies"]) >= 3, f"Too few competencies in {fn}"
    assert len(data["defensive_patterns"]) >= 3, f"Too few defensive patterns in {fn}"
    assert len(data["system_prompt"]) > 50, f"System prompt too short in {fn}"
    print(f"  [OK] Profile verified: {fn} -> {name}")

print("\n=== 4. VERIFY TOURNAMENT CONFIG & README ===")
cfg_path = os.path.join(base, "config/tournament_config.json")
assert os.path.isfile(cfg_path)
with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)
assert cfg["tournament_id"] == "tui_mastery_red_vs_blue_v1"
assert cfg["integrity_mode"] == "benchmark"
assert len(cfg["frameworks"]) == 3
assert len(cfg["attack_suite"]["scenarios"]) == 10
print(f"  [OK] Tournament config verified: {cfg['tournament_id']}")

readme_path = os.path.join(base, "README.md")
assert os.path.isfile(readme_path)
with open(readme_path, "r", encoding="utf-8") as f:
    readme_content = f.read()
assert len(readme_content) > 2000
assert "S_composite" in readme_content
assert "SIGWINCH_STORM" in readme_content
print(f"  [OK] README.md verified ({len(readme_content)} bytes)")

print("\n>>> ALL PROGRAMMATIC CHECKS PASSED SUCCESSFULLY! <<<")
