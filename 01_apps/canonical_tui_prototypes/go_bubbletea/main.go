package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"syscall"
	"time"

	"github.com/charmbracelet/bubbles/progress"
	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/table"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/mattn/go-isatty"
)

const defaultStatePath = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/cloud_api_quota_state.json"

// QuotaState represents the root cloud API quota data structure.
type QuotaState struct {
	Version       string                   `json:"version"`
	LastReset     string                   `json:"last_reset"`
	LastResetDate string                   `json:"last_reset_date"`
	LastUpdated   string                   `json:"last_updated"`
	Providers     map[string]ProviderState `json:"providers"`
	Metrics       GlobalMetrics            `json:"metrics"`
}

// ProviderState represents an individual provider's daily quota and latency metrics.
type ProviderState struct {
	DailyLimit          int64   `json:"daily_limit"`
	UsedToday           int64   `json:"used_today"`
	RemainingPct        float64 `json:"remaining_pct"`
	AvgLatencyMs        float64 `json:"avg_latency_ms"`
	MaxTokens           int64   `json:"max_tokens"`
	ConsecutiveFailures int64   `json:"consecutive_failures"`
	TotalRequests       int64   `json:"total_requests"`
	SuccessfulRequests  int64   `json:"successful_requests"`
	Status              string  `json:"status"`
	CooldownUntil       float64 `json:"cooldown_until"`
	LastUsedTimestamp   float64 `json:"last_used_timestamp"`
}

// GlobalMetrics contains overall routing and LoRA harvesting statistics.
type GlobalMetrics struct {
	TotalTasksRouted          int64 `json:"total_tasks_routed"`
	CloudTasksSucceeded       int64 `json:"cloud_tasks_succeeded"`
	LocalMeshFallbackCount    int64 `json:"local_mesh_fallback_count"`
	TotalLoRASamplesHarvested int64 `json:"total_lora_samples_harvested"`
}

// Validation helper
func validateState(state *QuotaState) error {
	if state == nil {
		return fmt.Errorf("state is nil")
	}
	if state.Version == "" {
		return fmt.Errorf("missing version")
	}
	if len(state.Providers) == 0 {
		return fmt.Errorf("providers map is empty")
	}
	for name, p := range state.Providers {
		if p.DailyLimit < 0 {
			return fmt.Errorf("provider %s has negative daily limit", name)
		}
		if p.Status == "" {
			return fmt.Errorf("provider %s has empty status", name)
		}
	}
	return nil
}

// Resilient read with flock and exponential backoff
func readStateWithRetry(filePath string, retries int) (*QuotaState, error) {
	var lastErr error
	lockPath := strings.TrimSuffix(filePath, filepath.Ext(filePath)) + ".lock"

	for attempt := 0; attempt < retries; attempt++ {
		// Non-blocking shared flock if lockfile exists
		if lockF, err := os.Open(lockPath); err == nil {
			_ = syscall.Flock(int(lockF.Fd()), syscall.LOCK_SH|syscall.LOCK_NB)
			defer func() {
				_ = syscall.Flock(int(lockF.Fd()), syscall.LOCK_UN)
				_ = lockF.Close()
			}()
		}

		data, err := os.ReadFile(filePath)
		if err == nil {
			if len(bytes.TrimSpace(data)) == 0 {
				lastErr = fmt.Errorf("state file is empty")
			} else {
				var state QuotaState
				if err := json.Unmarshal(data, &state); err == nil {
					if valErr := validateState(&state); valErr == nil {
						return &state, nil
					} else {
						lastErr = valErr
					}
				} else {
					lastErr = err
				}
			}
		} else {
			lastErr = err
		}

		if attempt < retries-1 {
			time.Sleep(time.Duration(50*(1<<attempt)) * time.Millisecond)
		}
	}
	if lastErr == nil {
		lastErr = fmt.Errorf("state file read failure")
	}
	return nil, lastErr
}

// Headless verification
func verifyStateHeadless(filePath string) int {
	state, err := readStateWithRetry(filePath, 3)
	if err != nil || state == nil {
		fmt.Fprintf(os.Stderr, "❌ Go Bubble Tea Verification FAILED: %v\n", err)
		return 1
	}

	var names []string
	for k := range state.Providers {
		names = append(names, k)
	}
	sort.Strings(names)

	fmt.Printf("✓ Go Bubble Tea Verification Passed: Version %s\n", state.Version)
	fmt.Printf("  Providers (%d): %s\n", len(state.Providers), strings.Join(names, ", "))
	fmt.Printf("  Metrics: Routed=%d, Cloud OK=%d, Fallbacks=%d, LoRA Harvested=%d\n",
		state.Metrics.TotalTasksRouted,
		state.Metrics.CloudTasksSucceeded,
		state.Metrics.LocalMeshFallbackCount,
		state.Metrics.TotalLoRASamplesHarvested,
	)
	return 0
}

// Lip Gloss Styles
var (
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#00ffcc")).
			Background(lipgloss.Color("#0b111c")).
			Padding(0, 1)

	subTitleStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#94a3b8")).
			Italic(true)

	cardStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#1e293b")).
			Background(lipgloss.Color("#0d1526")).
			Padding(0, 1).
			Width(22).
			Align(lipgloss.Center)

	cardTitleStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#94a3b8")).
			Bold(true)

	cardValueStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#38bdf8")).
			Bold(true)

	tableBoxStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#1e293b")).
			Background(lipgloss.Color("#090e17")).
			Padding(0, 1)

	footerStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#64748b")).
			Padding(0, 1)

	statusHealthy = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#4ade80")).
			Bold(true)

	statusCooldown = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#facc15")).
			Bold(true)

	statusDegraded = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#f43f5e")).
			Bold(true)

	statusExhausted = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#6b7280"))
)

// Messages
type tickMsg time.Time

type quotaDataMsg struct {
	state *QuotaState
	err   error
}

// Model
type Model struct {
	statePath    string
	pollInterval time.Duration
	quotaData    *QuotaState
	lastRead     time.Time
	err          error
	table        table.Model
	progressBars map[string]progress.Model
	spinner      spinner.Model
	width        int
	height       int
	verifyMode   bool
	timeout      time.Duration
	startTime    time.Time
	quitting     bool
	paused       bool
}

func initialModel(statePath string, pollInterval time.Duration, verifyMode bool, timeout time.Duration) Model {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("#00ffcc"))

	t := table.New(
		table.WithColumns([]table.Column{
			{Title: "Provider", Width: 16},
			{Title: "Daily Limit", Width: 12},
			{Title: "Used Today", Width: 12},
			{Title: "Rem %", Width: 10},
			{Title: "Avg Latency", Width: 14},
			{Title: "Failures", Width: 10},
			{Title: "Status", Width: 14},
		}),
		table.WithFocused(true),
		table.WithHeight(7),
	)

	tStyle := table.DefaultStyles()
	tStyle.Header = tStyle.Header.
		BorderStyle(lipgloss.NormalBorder()).
		BorderForeground(lipgloss.Color("#1e293b")).
		BorderBottom(true).
		Bold(true).
		Foreground(lipgloss.Color("#38bdf8"))
	tStyle.Selected = tStyle.Selected.
		Foreground(lipgloss.Color("#ffffff")).
		Background(lipgloss.Color("#0284c7")).
		Bold(true)
	t.SetStyles(tStyle)

	return Model{
		statePath:    statePath,
		pollInterval: pollInterval,
		table:        t,
		progressBars: make(map[string]progress.Model),
		spinner:      s,
		verifyMode:   verifyMode,
		timeout:      timeout,
		startTime:    time.Now(),
	}
}

func (m Model) Init() tea.Cmd {
	cmds := []tea.Cmd{
		m.spinner.Tick,
		readQuotaCmd(m.statePath),
	}
	if !m.verifyMode {
		cmds = append(cmds, tickCmd(m.pollInterval))
	}
	return tea.Batch(cmds...)
}

func readQuotaCmd(path string) tea.Cmd {
	return func() tea.Msg {
		state, err := readStateWithRetry(path, 3)
		return quotaDataMsg{state: state, err: err}
	}
}

func tickCmd(d time.Duration) tea.Cmd {
	return tea.Tick(d, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "q", "ctrl+c", "esc":
			m.quitting = true
			return m, tea.Quit
		case "r":
			return m, readQuotaCmd(m.statePath)
		case "p":
			m.paused = !m.paused
			return m, nil
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.table.SetWidth(msg.Width - 6)

	case tickMsg:
		if m.timeout > 0 && time.Since(m.startTime) >= m.timeout {
			m.quitting = true
			return m, tea.Quit
		}
		if !m.paused {
			return m, tea.Batch(readQuotaCmd(m.statePath), tickCmd(m.pollInterval))
		}
		return m, tickCmd(m.pollInterval)

	case quotaDataMsg:
		if msg.err != nil {
			m.err = msg.err
		} else {
			m.quotaData = msg.state
			m.lastRead = time.Now()
			m.err = nil
			m.updateTableRows()
		}

		if m.verifyMode {
			m.quitting = true
			return m, tea.Quit
		}

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd
	}

	var cmd tea.Cmd
	m.table, cmd = m.table.Update(msg)
	return m, cmd
}

func (m *Model) updateTableRows() {
	if m.quotaData == nil {
		return
	}
	var rows []table.Row
	var names []string
	for k := range m.quotaData.Providers {
		names = append(names, k)
	}
	sort.Strings(names)

	for _, name := range names {
		p := m.quotaData.Providers[name]
		limitStr := fmt.Sprintf("%d", p.DailyLimit)
		if p.DailyLimit >= 999999 {
			limitStr = "∞"
		}
		remPct := fmt.Sprintf("%.1f%%", p.RemainingPct*100.0)
		lat := fmt.Sprintf("%.1f ms", p.AvgLatencyMs)

		status := strings.ToLower(p.Status)
		var statusFmt string
		if status == "healthy" {
			statusFmt = statusHealthy.Render("● HEALTHY")
		} else if status == "in_cooldown" || status == "cooldown" {
			statusFmt = statusCooldown.Render("⏱ COOLDOWN")
		} else if status == "degraded" {
			statusFmt = statusDegraded.Render("🔻 DEGRADED")
		} else if status == "exhausted" {
			statusFmt = statusExhausted.Render("⛔ EXHAUSTED")
		} else {
			statusFmt = strings.ToUpper(status)
		}

		rows = append(rows, table.Row{
			name,
			limitStr,
			fmt.Sprintf("%d", p.UsedToday),
			remPct,
			lat,
			fmt.Sprintf("%d", p.ConsecutiveFailures),
			statusFmt,
		})
	}
	m.table.SetRows(rows)
}

func (m Model) View() string {
	if m.quitting && m.verifyMode {
		return lipgloss.NewStyle().Foreground(lipgloss.Color("#10b981")).Render("✓ Go Bubble Tea Verification Passed.\n")
	}

	title := titleStyle.Render("⚡ LAUBURU MESH — BUBBLE TEA QUOTA HUD")
	subTitle := subTitleStyle.Render(" Sovereign Free Token Maximizer & 24/7 LoRA Telemetry")
	header := lipgloss.JoinHorizontal(lipgloss.Center, title, subTitle)

	// HUD Metric Cards
	var totalTasks, cloudOK, fallbacks, loraSamples int64
	if m.quotaData != nil {
		totalTasks = m.quotaData.Metrics.TotalTasksRouted
		cloudOK = m.quotaData.Metrics.CloudTasksSucceeded
		fallbacks = m.quotaData.Metrics.LocalMeshFallbackCount
		loraSamples = m.quotaData.Metrics.TotalLoRASamplesHarvested
	}

	card1 := cardStyle.Render(lipgloss.JoinVertical(lipgloss.Center, cardTitleStyle.Render("TOTAL TASKS"), cardValueStyle.Render(fmt.Sprintf("%d", totalTasks))))
	card2 := cardStyle.Render(lipgloss.JoinVertical(lipgloss.Center, cardTitleStyle.Render("CLOUD SUCCEEDED"), cardValueStyle.Render(fmt.Sprintf("%d", cloudOK))))
	card3 := cardStyle.Render(lipgloss.JoinVertical(lipgloss.Center, cardTitleStyle.Render("MESH FALLBACKS"), cardValueStyle.Render(fmt.Sprintf("%d", fallbacks))))
	card4 := cardStyle.Render(lipgloss.JoinVertical(lipgloss.Center, cardTitleStyle.Render("LORA HARVESTED"), cardValueStyle.Render(fmt.Sprintf("%d", loraSamples))))

	metricsRow := lipgloss.JoinHorizontal(lipgloss.Top, card1, " ", card2, " ", card3, " ", card4)

	tableBox := tableBoxStyle.Render(m.table.View())

	pauseMsg := ""
	if m.paused {
		pauseMsg = " [PAUSED]"
	}

	syncTime := "--:--:--"
	if !m.lastRead.IsZero() {
		syncTime = m.lastRead.Format("15:04:05")
	}

	footerText := fmt.Sprintf("%s Last Sync: %s%s | 'q' quit | 'r' refresh | 'p' pause | '--verify' CI check",
		m.spinner.View(),
		syncTime,
		pauseMsg,
	)
	footer := footerStyle.Render(footerText)

	return lipgloss.JoinVertical(lipgloss.Left, header, "\n", metricsRow, "\n", tableBox, "\n", footer)
}

func runHeadlessLoop(statePath string, pollDur time.Duration, timeoutDur time.Duration) int {
	start := time.Now()
	for {
		state, err := readStateWithRetry(statePath, 3)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Headless loop state read warning: %v\n", err)
		} else {
			_ = state
		}
		if timeoutDur > 0 && time.Since(start) >= timeoutDur {
			break
		}
		time.Sleep(pollDur)
	}
	return 0
}

func main() {
	statePathFlag := flag.String("state-path", "", "Path to cloud_api_quota_state.json")
	stateAliasFlag := flag.String("state", "", "Alias for -state-path")
	pollIntervalFlag := flag.Float64("poll-interval", 2.0, "Polling interval in seconds")
	verifyFlag := flag.Bool("verify", false, "Run in headless verification mode")
	timeoutFlag := flag.Float64("timeout", 0.0, "Auto-exit timeout in seconds (0 = disabled)")

	flag.Parse()

	statePath := defaultStatePath
	if *statePathFlag != "" {
		statePath = *statePathFlag
	} else if *stateAliasFlag != "" {
		statePath = *stateAliasFlag
	} else if envPath := os.Getenv("LAUBURU_QUOTA_STATE_PATH"); envPath != "" {
		statePath = envPath
	}

	if *verifyFlag {
		os.Exit(verifyStateHeadless(statePath))
	}

	pollDur := time.Duration(*pollIntervalFlag * float64(time.Second))
	timeoutDur := time.Duration(*timeoutFlag * float64(time.Second))

	// Check if running in interactive terminal
	isTTY := isatty.IsTerminal(os.Stdout.Fd()) || isatty.IsCygwinTerminal(os.Stdout.Fd())
	if !isTTY && timeoutDur > 0 {
		os.Exit(runHeadlessLoop(statePath, pollDur, timeoutDur))
	}

	m := initialModel(statePath, pollDur, *verifyFlag, timeoutDur)
	var pOpts []tea.ProgramOption
	if isTTY {
		pOpts = append(pOpts, tea.WithAltScreen())
	} else {
		pOpts = append(pOpts, tea.WithInput(os.Stdin), tea.WithOutput(os.Stdout))
	}

	p := tea.NewProgram(m, pOpts...)
	if _, err := p.Run(); err != nil {
		if !isTTY && timeoutDur > 0 {
			os.Exit(runHeadlessLoop(statePath, pollDur, timeoutDur))
		}
		fmt.Fprintf(os.Stderr, "Error running Bubble Tea application: %v\n", err)
		os.Exit(1)
	}
}
