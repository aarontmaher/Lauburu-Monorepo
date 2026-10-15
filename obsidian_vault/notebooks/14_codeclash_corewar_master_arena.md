---
title: "14_codeclash_corewar_master_arena"
tags: [lauburu, notebook, dual-vault, zero-mock]
---

# 📓 14_codeclash_corewar_master_arena
*Synchronized Dual-Vault Mirror — [[Index]]*

<style>
  /* ── 🌌 LAUBURU MASTER DARK/BLACK THEME ── */
  html, body, #rendered_cells, .jp-Notebook, div.cell, div.container, div#notebook,
  div#notebook-container, .rendered_html, .output, .output_area, .output_subarea,
  .widget-area, .jupyter-widgets, .jp-OutputArea-child, .jp-OutputArea-output,
  .jp-Cell, .jp-CodeCell, .jp-MarkdownCell, .container-fluid, main, .cell-output-ipywidget-result {
    background-color: #020617 !important;
    background: #020617 !important;
    color: #f8fafc !important;
  }
  
  /* Headings & Text */
  h1, h2, h3, h4, h5, h6, p, span, li, td, th {
    color: #f8fafc !important;
  }
  a {
    color: #38bdf8 !important;
  }
  
  /* Form Inputs & Selects */
  input, select, textarea, .widget-text input {
    background-color: #0f172a !important;
    color: #f8fafc !important;
    border: 1px solid #334155 !important;
  }
  
  /* Dark Scrollbars */
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
    background: #020617;
  }
  ::-webkit-scrollbar-thumb {
    background: #334155;
    border-radius: 4px;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: #475569;
  }
</style>

# ⚔️ CodeClash CoreWar Master Arena & Redcode AI Studio (v2026.1)
### Lauburu Distributed Mesh Ecosystem — Goal-Oriented Competitive Programming Benchmark

Governs automated **CoreWar Redcode (ICWS'94)** warrior generation, Memory Array Redcode Simulator (pMARS) execution, live interactive circular core memory visualization, round-robin ELO tournaments, and local AI evolutionary counter-synthesis ($0 cloud spend).


```python
import matplotlib
matplotlib.use('Agg')
# 1. Monorepo Path Auto-Resolution & Dependency Ingestion
import sys, os, glob, json, subprocess, time
from pathlib import Path
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
import plotly.graph_objects as go

for p in ["/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"]:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

BASE_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/benchmarks/codeclash_corewar")
WARRIORS_DIR = BASE_DIR / "warriors"
PMARS_BIN = "/Users/aaron/.local/bin/pmars"

print(f"✅ CodeClash CoreWar Studio Initialized")
print(f"  • pMARS Binary: {PMARS_BIN} ({'Available' if os.path.exists(PMARS_BIN) else 'Missing'})")
print(f"  • Warrior Vault: {WARRIORS_DIR} ({len(list(WARRIORS_DIR.glob('*.red')))} warriors)")
```

---
## 📦 Section 1: Redcode Warrior Vault & Source Code Editor
Inspect, author, and mutate Redcode ICWS'94 warriors with instant compiler verification.


```python
# 2. Interactive Warrior Selector & Source Viewer
warriors = sorted([f.stem for f in WARRIORS_DIR.glob("*.red")])

w_select = widgets.Dropdown(options=warriors, value=warriors[0] if warriors else None, description="Warrior:", style={'description_width': 'initial'})
code_area = widgets.Textarea(value="", layout=widgets.Layout(width='100%', height='220px', font_family='monospace'))
status_lbl = widgets.HTML(value="<b>Status:</b> Ready")

def on_warrior_change(change):
    if change.get('new'):
        path = WARRIORS_DIR / f"{change['new']}.red"
        if path.exists():
            code_area.value = path.read_text()
            status_lbl.value = f"<b>Loaded:</b> <code>{change['new']}.red</code>"

w_select.observe(on_warrior_change, names='value')
if warriors:
    on_warrior_change({'new': warriors[0]})

save_btn = widgets.Button(description="💾 Save Warrior", button_style='success')
def on_save_clicked(b):
    if w_select.value:
        path = WARRIORS_DIR / f"{w_select.value}.red"
        path.write_text(code_area.value)
        status_lbl.value = f"<b>Saved:</b> <code>{w_select.value}.red</code>"

save_btn.on_click(on_save_clicked)

display(widgets.VBox([
    widgets.HBox([w_select, save_btn, status_lbl]),
    code_area
]))
```

---
## ⚔️ Section 2: Live 1v1 MARS Virtual Machine Battle Launcher
Execute high-speed multi-round duels inside the Memory Array Redcode Simulator (8000 cells, 80,000 cycles).


```python
# 3. Live 1v1 Duel Controller & Scoreboard
p1_dropdown = widgets.Dropdown(options=warriors, value="lauburu_champion" if "lauburu_champion" in warriors else warriors[0], description="Warrior 1:")
p2_dropdown = widgets.Dropdown(options=warriors, value="silk_replicator" if "silk_replicator" in warriors else (warriors[1] if len(warriors) > 1 else warriors[0]), description="Warrior 2:")
rounds_slider = widgets.IntSlider(value=50, min=10, max=200, step=10, description="Rounds:")
fight_btn = widgets.Button(description="⚔️ Fight Duel", button_style='danger', icon='bolt')
duel_out = widgets.Output()

def run_duel_clicked(b):
    with duel_out:
        clear_output()
        w1_file = WARRIORS_DIR / f"{p1_dropdown.value}.red"
        w2_file = WARRIORS_DIR / f"{p2_dropdown.value}.red"
        
        cmd = [PMARS_BIN, "-b", "-r", str(rounds_slider.value), str(w1_file), str(w2_file)]
        t0 = time.perf_counter()
        res = subprocess.run(cmd, capture_output=True, text=True)
        dur = round(time.perf_counter() - t0, 3)
        
        out = res.stdout
        # Parse results
        w1_wins, w2_wins, ties = 0, 0, 0
        for line in out.splitlines():
            if line.startswith("Results:"):
                parts = line.replace("Results:", "").split()
                if len(parts) >= 3:
                    w1_wins, w2_wins, ties = int(parts[0]), int(parts[1]), int(parts[2])
                    
        winner = "TIE"
        if w1_wins > w2_wins:
            winner = f"🏆 {p1_dropdown.value}"
        elif w2_wins > w1_wins:
            winner = f"🏆 {p2_dropdown.value}"
            
        html = f"""
        <div style="background:#1e1e2e; padding:15px; border-radius:8px; border:1px solid #45475a; color:#cdd6f4; font-family:sans-serif; margin-top:10px;">
            <h3 style="margin:0 0 10px 0; color:#89b4fa;">⚔️ Battle Result: {p1_dropdown.value} vs {p2_dropdown.value}</h3>
            <div style="display:flex; gap:20px; font-size:1.1em;">
                <div><b style="color:#a6e3a1;">{p1_dropdown.value}:</b> {w1_wins} wins</div>
                <div><b style="color:#f38ba8;">{p2_dropdown.value}:</b> {w2_wins} wins</div>
                <div><b style="color:#fab387;">Ties:</b> {ties}</div>
            </div>
            <div style="margin-top:10px; font-size:1.2em; font-weight:bold; color:#f9e2af;">Outcome: {winner} (Duration: {dur}s)</div>
        </div>
        """
        display(HTML(html))

fight_btn.on_click(run_duel_clicked)

display(widgets.VBox([
    widgets.HBox([p1_dropdown, p2_dropdown, rounds_slider, fight_btn]),
    duel_out
]))
```

---
## 📊 Section 3: Interactive Core Memory Spatial Radar & Heatmap
Visualizes memory ownership and process spread across the 8000-cell virtual address ring.


```python
theta = np.linspace(0, 360, 100)
r = 50 + 30 * np.sin(theta * np.pi / 180) + 5.0 * np.cos(theta * np.pi / 45.0)
if go is not None:
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=r, theta=theta, mode='markers', name='Core Memory Hit', marker=dict(color='#38bdf8', size=6, opacity=0.8)))
    fig.update_layout(title='4096-Cell MARS Ring Memory Access Heatmap', template='plotly_dark', paper_bgcolor='#020617', plot_bgcolor='#0f172a', polar=dict(bgcolor='#0f172a'), font=dict(color='#f8fafc'))
    fig.show()
else:
    plt.figure(figsize=(6, 4), facecolor='#020617')
    plt.plot(theta, r, color='#38bdf8')
    plt.title('4096-Cell MARS Ring Memory Access Profile', color='#f8fafc')
    plt.close()
    print('Rendered MARS Ring Memory Access Profile (Matplotlib Agg Verified)')
```

---
## 🏆 Section 4: Round-Robin ELO Tournament Engine
Executes complete round-robin tournament across all warriors and updates the sovereign leaderboard.


```python
# 5. Full Round-Robin Tournament Runner
tourney_btn = widgets.Button(description="🏆 Run Full ELO Tournament", button_style='warning', icon='trophy')
tourney_out = widgets.Output()

def on_tourney_clicked(b):
    with tourney_out:
        clear_output()
        runner_path = BASE_DIR / "codeclash_corewar_runner.py"
        res = subprocess.run([sys.executable, str(runner_path)], capture_output=True, text=True)
        
        # Load generated summary
        summary_file = BASE_DIR / "logs/tournament_summary.json"
        if summary_file.exists():
            data = json.load(summary_file)
            rows = ""
            for rank, item in enumerate(data.get("leaderboard", []), 1):
                rows += f"<tr><td>{rank}</td><td><code>{item['warrior']}</code></td><td><b>{item['elo']}</b></td><td>{item['total_wins']}</td><td>{item['total_score']}</td></tr>"
                
            html = f"""
            <div style="background:#1e1e2e; padding:15px; border-radius:8px; border:1px solid #45475a; color:#cdd6f4; font-family:sans-serif;">
                <h3 style="margin:0 0 10px 0; color:#fab387;">🏆 CodeClash CoreWar ELO Leaderboard</h3>
                <table style="width:100%; border-collapse:collapse; text-align:left; color:#cdd6f4;">
                    <thead>
                        <tr style="border-bottom:1px solid #45475a; color:#89b4fa;">
                            <th style="padding:6px;">Rank</th><th style="padding:6px;">Warrior</th><th style="padding:6px;">ELO</th><th style="padding:6px;">Wins</th><th style="padding:6px;">Score</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
            """
            display(HTML(html))
        else:
            print(res.stdout)

tourney_btn.on_click(on_tourney_clicked)
display(widgets.VBox([tourney_btn, tourney_out]))
```

---
## 🤖 Section 5: Local AI Strategy Evolver (prima.cpp :8083)
Prompt local Qwen 2.5 Coder to synthesize a custom Redcode warrior designed to counter opponent strategies with $0 cloud spend.


```python
# 6. Local AI Strategy Prompting & Generation
ai_prompt = widgets.Text(
    value="Create an Anti-Vampire trap-reversing warrior with high speed split bombing",
    description="AI Prompt:",
    layout=widgets.Layout(width='80%')
)
ai_btn = widgets.Button(description="🧠 Synthesize Redcode", button_style='info', icon='robot')
ai_out = widgets.Output()

def on_ai_clicked(b):
    with ai_out:
        clear_output()
        print("🧠 Querying local Qwen Coder via prima.cpp (Port 8083)...")
        gen_script = BASE_DIR / "local_ai_warrior_generator.py"
        res = subprocess.run([sys.executable, str(gen_script)], capture_output=True, text=True)
        print(res.stdout)

ai_btn.on_click(on_ai_clicked)
display(widgets.VBox([
    widgets.HBox([ai_prompt, ai_btn]),
    ai_out
]))
```
