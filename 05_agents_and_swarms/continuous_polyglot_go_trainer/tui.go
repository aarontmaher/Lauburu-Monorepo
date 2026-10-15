package main

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

var (
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#FAFAFA")).
			Background(lipgloss.Color("#7D56F4")).
			Padding(0, 1)

	headerStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#04B575")).
			Bold(true)

	statusStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#EE6FF8"))

	boxStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#5A56E0")).
			Padding(1, 2)

	logStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#A0A0A0"))
)

// TUIModel represents the Bubble Tea interactive model.
type TUIModel struct {
	trainer   *PolyglotTrainer
	spinner   spinner.Model
	events    []TrainingEvent
	cycle     int64
	width     int
	height    int
	quitting  bool
}

// TickMsg triggers regular TUI refreshes.
type TickMsg time.Time

func tickCmd() tea.Cmd {
	return tea.Tick(500*time.Millisecond, func(t time.Time) tea.Msg {
		return TickMsg(t)
	})
}

// NewTUIModel initializes the Bubble Tea interactive model.
func NewTUIModel(trainer *PolyglotTrainer) TUIModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("#04B575"))

	return TUIModel{
		trainer: trainer,
		spinner: s,
		events:  make([]TrainingEvent, 0, 20),
	}
}

func (m TUIModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, tickCmd())
}

func (m TUIModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.String() == "q" || msg.String() == "ctrl+c" {
			m.quitting = true
			return m, tea.Quit
		}
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		return m, nil
	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd
	case TickMsg:
		// Drain new events from trainer event channel
		for {
			select {
			case ev := <-m.trainer.eventChannel:
				m.events = append(m.events, ev)
				if len(m.events) > 12 {
					m.events = m.events[1:]
				}
				m.cycle = ev.CycleNumber
			default:
				return m, tickCmd()
			}
		}
	}
	return m, nil
}

func (m TUIModel) View() string {
	if m.quitting {
		return "\n  👋 Exiting Lauburu Polyglot Continuous Trainer.\n\n"
	}

	m.trainer.mu.RLock()
	st := m.trainer.state
	m.trainer.mu.RUnlock()

	header := titleStyle.Render("🌐 LAUBURU CONTINUOUS POLYGLOT TRAINER (TUI, CLI & POLYGLOT)")
	meta := fmt.Sprintf("\n%s Cycle: %d | Samples: %d | TUI: %d | CLI: %d | Polyglot: %d\n",
		m.spinner.View(), st.TotalCycles, st.TotalSamplesLogged, st.TuiPassCount, st.CliPassCount, st.PolyglotPassCount)

	eloStr := fmt.Sprintf("%s Qwen 3.8 Max: %d | Abliterated: %d | Qwen 2.5 Coder: %d\n",
		headerStyle.Render("ELO Ratings:"),
		st.EloScores["qwen_38_max"],
		st.EloScores["qwen_38_max_abliterated"],
		st.EloScores["qwen_25_coder"],
	)

	tableHeader := fmt.Sprintf("\n%-18s %-20s %-8s %-12s %-10s\n",
		"TASK ID", "DOMAIN", "LANG", "COMPILER", "LATENCY")
	divider := strings.Repeat("─", 74) + "\n"

	var eventRows strings.Builder
	for i := len(m.events) - 1; i >= 0; i-- {
		ev := m.events[i]
		verStr := "PASSED"
		if !ev.CompilerVerified {
			verStr = fmt.Sprintf("FAIL(%d)", ev.CompilerExitCode)
		}
		eventRows.WriteString(fmt.Sprintf("%-18s %-20s %-8s %-12s %8.2fms\n",
			ev.TaskID, ev.Domain, ev.Language, verStr, ev.CompilerLatencyMs))
	}

	footer := logStyle.Render("\nPress 'q' or Ctrl+C to exit. Continuous training active across Tri-Vault storage.")
	body := header + meta + eloStr + headerStyle.Render(tableHeader) + divider + eventRows.String() + footer

	return boxStyle.Render(body)
}
