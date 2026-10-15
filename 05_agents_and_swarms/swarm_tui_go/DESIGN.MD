---
version: "Stitch 2.0 TUI Protocol"
target: "Go Bubble Tea & Lipgloss"
app_name: "Sovereign Swarm Control Terminal"
---

# 1. Architecture Overview
This is a Go-based TUI using `charmbracelet/bubbletea` and `charmbracelet/lipgloss`.
The application must present a highly digestible, structured dashboard that multiplexes autonomous AI agent logs, displays a speculative summary, and allows direct user input.

# 2. Visual Layout (Lipgloss)
The layout is a 3-pane split:
1. **Left Pane (60% width): Unified Swarm Stream.**
   - Must use a scrolling `viewport` or `table`.
   - Data must be highly digested: Do not dump raw JSON. Format as `[Agent Name] -> [Action/Summary]`.
   - Use soft, readable colors (e.g., Lipgloss Cyan for agent names, Gray for timestamps).
2. **Top Right Pane (40% width): Speculative AI Synthesis.**
   - Boxed in Magenta.
   - Displays the high-level summary from Port 8082 of what the swarm is doing.
3. **Bottom Right Pane (40% width): Interaction Backlog & Input.**
   - Boxed in Yellow.
   - Displays a list of blocked agents waiting for input.
   - Must include a `charmbracelet/bubbles/textinput` component actively listening for user typing to dispatch answers.

# 3. Data Ingestion Logic
- Use standard Go `os.Open` and `bufio.Scanner` to tail `/Users/aaron/.gemini/antigravity/brain/*/.system_generated/logs/transcript.jsonl`.
- Parse the JSON strictly. Extract `source` and `content`.
- Pipe updates into the Bubble Tea `Update()` loop via `tea.Cmd` message passing (Msg types: `LogMsg`, `SummaryMsg`).

# 4. UX/UI Digestibility Rules
- No text wrapping that breaks words arbitrarily; use proper Lipgloss word-wrap.
- Use visual dividers between different agents' messages.
- Hide all raw system prompts or internal HTML; only show human-readable intents.
