package tui

import (
	"fmt"
	"os/exec"
	"strings"
	"time"

	"github.com/aarontmaher/lauburu-opencode/internal/biometrics"
	"github.com/aarontmaher/lauburu-opencode/internal/bluetooth"
	"github.com/aarontmaher/lauburu-opencode/internal/config"
	"github.com/aarontmaher/lauburu-opencode/internal/mesh"
	"github.com/aarontmaher/lauburu-opencode/internal/router"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// --- STYLES ---
var (
	colorPrimary   = lipgloss.Color("62")
	colorSecondary = lipgloss.Color("205")
	colorText      = lipgloss.Color("252")
	colorMuted     = lipgloss.Color("240")
	colorSuccess   = lipgloss.Color("42")
	colorWarning   = lipgloss.Color("214")
	colorError     = lipgloss.Color("196")
	colorCmd       = lipgloss.Color("226")

	headerStyle = lipgloss.NewStyle().Foreground(colorText).Background(lipgloss.Color("236")).Padding(0, 1).Bold(true)
	footerStyle = lipgloss.NewStyle().Foreground(colorMuted).Background(lipgloss.Color("235")).Padding(0, 1)
	cmdStyle    = lipgloss.NewStyle().Foreground(colorCmd).Background(lipgloss.Color("235")).Padding(0, 1).Bold(true)

	tabActiveStyle   = lipgloss.NewStyle().Foreground(colorSecondary).Border(lipgloss.NormalBorder(), false, false, true, false).BorderForeground(colorSecondary).Padding(0, 2)
	tabInactiveStyle = lipgloss.NewStyle().Foreground(colorMuted).Border(lipgloss.NormalBorder(), false, false, true, false).BorderForeground(colorMuted).Padding(0, 2)

	paneStyle  = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).BorderForeground(colorPrimary).Padding(0, 1)
	modalStyle = lipgloss.NewStyle().Border(lipgloss.ThickBorder()).BorderForeground(colorError).Padding(2, 4).Align(lipgloss.Center)
)

// --- ASYNC ROUTING ---
type routingFinishedMsg struct{ response string }
type logUpdateMsg []string

func routeQueryCmd(r *router.MoERouter, query string) tea.Cmd {
	return func() tea.Msg {
		dest := r.DetermineRoute(query)
		var result string
		if dest == router.DestMedicalSwarm {
			result, _ = r.ExecuteMedicalSwarm(query, "{\"hr\": 65}")
		} else if dest == router.DestCloudAPI {
			result, _ = r.ExecuteCloudEscalation(query)
		} else {
			result, _ = r.QueryModel(fmt.Sprintf("http://127.0.0.1:%s/v1/chat/completions", r.Config.PortMasterOrchestrator), "qwen_38_max", "You are Qwen Master Orchestrator.", query)
		}
		return routingFinishedMsg{response: result}
	}
}

func fetchLogsCmd() tea.Cmd {
	return func() tea.Msg {
		out, err := exec.Command("tail", "-n", "10", "/tmp/lauburu_cli.log").Output()
		if err != nil {
			return logUpdateMsg{}
		}
		lines := strings.Split(strings.TrimSpace(string(out)), "\n")
		return logUpdateMsg(lines)
	}
}

// --- MAIN MODEL ---
type DashboardModel struct {
	Role      mesh.NodeRole
	BioBuffer *biometrics.TelemetryBuffer
	Router    *router.MoERouter
	BTerminal *bluetooth.BluetoothTerminal

	width     int
	height    int
	activeTab int
	isDev     bool

	// Chat State
	InputText  string
	Response   string
	isRouting  bool
	spinnerIdx int

	// Bluetooth Terminal State
	BTInputText string

	// Logs
	logLines []string

	// Vim Command Mode
	commandMode  bool
	commandInput string

	// Modal State
	showModal   bool
	modalText   string
	modalAction func()
}

func InitialModel(role mesh.NodeRole, bio *biometrics.TelemetryBuffer, bt *bluetooth.BluetoothTerminal, isDev bool) DashboardModel {
	cfg, _ := config.LoadConfig()
	r := router.NewRouter(cfg)
	if bt == nil {
		bt = bluetooth.NewBluetoothTerminal(r)
	}
	return DashboardModel{
		Role:        role,
		BioBuffer:   bio,
		Router:      r,
		BTerminal:   bt,
		activeTab:   0,
		isDev:       isDev,
		InputText:   "",
		BTInputText: "",
		Response:    "Lauburu Mesh Ecosystem Initialized.\nActive Engine: Genetic MoE (23B Parameters)\nSpeculative Decoding: Ready (Screen Lens VLA)",
		isRouting:   false,
	}
}

// SetActiveTab allows external CLI flags to select the active tab on startup
func (m *DashboardModel) SetActiveTab(tab int) {
	if tab >= 0 && tab < 5 {
		m.activeTab = tab
	}
}

type tickMsg time.Time

func tickCmd() tea.Cmd {
	return tea.Tick(time.Second/30, func(t time.Time) tea.Msg { return tickMsg(t) })
}

func (m DashboardModel) Init() tea.Cmd {
	return tea.Batch(tickCmd(), fetchLogsCmd())
}

func (m DashboardModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width, m.height = msg.Width, msg.Height
		return m, nil

	case tickMsg:
		if m.isRouting {
			m.spinnerIdx = (m.spinnerIdx + 1) % 4
		}
		if time.Now().UnixMilli()%1000 < 33 {
			cmds = append(cmds, fetchLogsCmd())
		}
		cmds = append(cmds, tickCmd())
		return m, tea.Batch(cmds...)

	case logUpdateMsg:
		m.logLines = msg
		return m, nil

	case routingFinishedMsg:
		m.isRouting = false
		m.Response = msg.response
		return m, nil

	case tea.MouseMsg:
		if msg.Type == tea.MouseLeft && !m.showModal {
			if msg.Y == 1 || msg.Y == 2 {
				if msg.X >= 0 && msg.X < 20 {
					m.activeTab = 0
				} else if msg.X >= 20 && msg.X < 36 {
					m.activeTab = 1
				} else if msg.X >= 36 && msg.X < 50 {
					m.activeTab = 2
				} else if msg.X >= 50 && msg.X < 65 {
					m.activeTab = 3
				} else if msg.X >= 65 {
					m.activeTab = 4
				}
			}
		}
		return m, nil

	case tea.KeyMsg:
		// 1. MODAL INTERCEPT
		if m.showModal {
			switch msg.String() {
			case "y", "Y", "enter":
				if m.modalAction != nil {
					m.modalAction()
				}
				m.showModal = false
			case "n", "N", "esc":
				m.showModal = false
			}
			return m, nil
		}

		// 2. VIM COMMAND MODE INTERCEPT
		if m.commandMode {
			switch msg.String() {
			case "esc":
				m.commandMode = false
				m.commandInput = ""
			case "enter":
				cmdStr := strings.TrimSpace(m.commandInput)
				m.commandMode = false
				m.commandInput = ""
				return m.executePowerCommand(cmdStr)
			case "backspace":
				if len(m.commandInput) > 0 {
					m.commandInput = m.commandInput[:len(m.commandInput)-1]
				} else {
					m.commandMode = false
				}
			default:
				if len(msg.String()) == 1 {
					m.commandInput += msg.String()
				}
			}
			return m, nil
		}

		// 3. STANDARD NAVIGATION & INPUT
		switch msg.String() {
		case "ctrl+c":
			return m, tea.Quit
		case "esc":
			if m.activeTab == 0 && len(m.InputText) > 0 {
				m.InputText = ""
			} else if m.activeTab == 4 && len(m.BTInputText) > 0 {
				m.BTInputText = ""
			}
			return m, nil
		case "ctrl+1":
			m.activeTab = 0
			return m, nil
		case "ctrl+2":
			m.activeTab = 1
			return m, nil
		case "ctrl+3":
			m.activeTab = 2
			return m, nil
		case "ctrl+4":
			m.activeTab = 3
			return m, nil
		case "ctrl+5":
			m.activeTab = 4
			return m, nil

		case "tab", "right":
			m.activeTab = (m.activeTab + 1) % 5
			return m, nil
		case "shift+tab", "left":
			if (m.activeTab == 0 && len(m.InputText) == 0) || (m.activeTab == 4 && len(m.BTInputText) == 0) || (m.activeTab != 0 && m.activeTab != 4) {
				m.activeTab = (m.activeTab - 1 + 5) % 5
				return m, nil
			}

		case ":":
			if (m.activeTab != 0 && m.activeTab != 4) || (m.activeTab == 0 && len(m.InputText) == 0) || (m.activeTab == 4 && len(m.BTInputText) == 0) {
				m.commandMode = true
				return m, nil
			}
			if m.activeTab == 0 {
				m.InputText += ":"
			} else if m.activeTab == 4 {
				m.BTInputText += ":"
			}
			return m, nil

		case "r":
			if m.activeTab == 3 {
				m.showModal = true
				m.modalText = "Are you sure you want to hard-reset the BLE Scanner?"
				m.modalAction = func() { biometrics.ResetScanner(m.BioBuffer) }
				return m, nil
			}
			if m.activeTab == 0 {
				m.InputText += "r"
			} else if m.activeTab == 4 {
				m.BTInputText += "r"
			}
			return m, nil

		case "enter":
			if m.activeTab == 0 && !m.isRouting {
				query := strings.TrimSpace(m.InputText)
				if query == "" {
					return m, nil
				}
				m.isRouting = true
				m.InputText = ""
				return m, routeQueryCmd(m.Router, query)
			}
			if m.activeTab == 4 {
				cmd := strings.TrimSpace(m.BTInputText)
				if cmd != "" && m.BTerminal != nil {
					m.BTerminal.WriteCommand(cmd)
					m.BTInputText = ""
				}
				return m, nil
			}

		case "backspace":
			if m.activeTab == 0 && len(m.InputText) > 0 {
				m.InputText = m.InputText[:len(m.InputText)-1]
			} else if m.activeTab == 4 && len(m.BTInputText) > 0 {
				m.BTInputText = m.BTInputText[:len(m.BTInputText)-1]
			}

		default:
			if m.activeTab == 0 && len(msg.String()) == 1 {
				m.InputText += msg.String()
			} else if m.activeTab == 4 {
				macros := map[string]string{
					"0": "scan", "1": "status", "2": "telemetry", "3": "ram", "4": "bicep",
					"5": "reconnect", "6": "clear", "7": "voice", "8": "help", "9": "mtu",
				}
				if m.BTInputText == "" {
					if macroCmd, ok := macros[msg.String()]; ok {
						if m.BTerminal != nil {
							m.BTerminal.WriteCommand(macroCmd)
						}
						return m, nil
					}
				}
				if len(msg.String()) == 1 {
					m.BTInputText += msg.String()
				}
			}
		}
	}

	return m, nil
}

func (m DashboardModel) executePowerCommand(cmdStr string) (tea.Model, tea.Cmd) {
	switch cmdStr {
	case "q", "quit":
		return m, tea.Quit
	case "reset":
		biometrics.ResetScanner(m.BioBuffer)
		m.activeTab = 0
		m.Response = "Power Command Executed: BLE Scanner Reset."
	case "mesh":
		m.activeTab = 2
	case "bt", "terminal", "rfconnect":
		m.activeTab = 4
	case "reconnect":
		if m.BTerminal != nil {
			m.BTerminal.WriteCommand("reconnect")
		}
		m.activeTab = 4
	default:
		m.activeTab = 0
		m.Response = fmt.Sprintf("Unknown command: :%s", cmdStr)
	}
	return m, nil
}

// --- RENDERING ---
func (m DashboardModel) View() string {
	if m.width == 0 {
		return "Initializing Lauburu Terminal Environment..."
	}

	devBadge := ""
	if m.isDev {
		devBadge = " [DEV MODE ACTIVE] "
	}
	headerStr := fmt.Sprintf(" ⚛ LAUBURU MESH IDE | Role: %s | Node: Local Host%s ", m.Role, devBadge)
	header := headerStyle.Width(m.width).Render(headerStr)

	tabs := []string{"1: Chat & Context", "2: Telemetry", "3: Mesh Map", "4: Settings", "5: BT RFConnect"}
	var renderedTabs []string
	for i, t := range tabs {
		if i == m.activeTab {
			renderedTabs = append(renderedTabs, tabActiveStyle.Render(t))
		} else {
			renderedTabs = append(renderedTabs, tabInactiveStyle.Render(t))
		}
	}
	tabBar := lipgloss.JoinHorizontal(lipgloss.Bottom, renderedTabs...)

	viewportHeight := m.height - lipgloss.Height(header) - lipgloss.Height(tabBar) - 2
	if viewportHeight < 5 {
		viewportHeight = 5
	}

	var viewport string
	if m.showModal {
		modalBox := modalStyle.Width(m.width / 2).Render(fmt.Sprintf("⚠️ WARNING\n\n%s\n\n[Y]es   /   [N]o", m.modalText))
		viewport = lipgloss.Place(m.width, viewportHeight, lipgloss.Center, lipgloss.Center, modalBox)
	} else {
		switch m.activeTab {
		case 0:
			viewport = m.renderChatTab(m.width, viewportHeight)
		case 1:
			viewport = m.renderTelemetryTab(m.width, viewportHeight)
		case 2:
			viewport = m.renderMeshTab(m.width, viewportHeight)
		case 3:
			viewport = m.renderSettingsTab(m.width, viewportHeight)
		case 4:
			viewport = m.renderBluetoothTerminalTab(m.width, viewportHeight)
		}
	}

	var footer string
	if m.commandMode {
		footer = cmdStyle.Width(m.width).Render(fmt.Sprintf(":%s_", m.commandInput))
	} else {
		footerStr := " [Ctrl+1..5] Switch Tabs | [:] Power Command | [Esc] Quit "
		if m.activeTab == 0 {
			footerStr += "| [Enter] Submit "
		} else if m.activeTab == 3 {
			footerStr += "| [r] Reset Biometrics "
		} else if m.activeTab == 4 {
			footerStr += "| [0..9] Macros | [Enter] Send UART "
		}
		footer = footerStyle.Width(m.width).Render(footerStr)
	}

	return lipgloss.JoinVertical(lipgloss.Left, header, tabBar, viewport, footer)
}

func (m DashboardModel) renderBluetoothTerminalTab(w, h int) string {
	if m.BTerminal == nil {
		return paneStyle.Width(w - 2).Height(h).Render(
			lipgloss.NewStyle().Foreground(colorMuted).Render("-- Bluetooth Terminal Inactive --"),
		)
	}

	stats := m.BTerminal.GetStats()
	lines := m.BTerminal.GetLines()

	statusStyle := lipgloss.NewStyle().Foreground(colorSuccess).Bold(true)
	statusText := "ONLINE"
	if !stats.IsOnline {
		statusStyle = lipgloss.NewStyle().Foreground(colorWarning)
		statusText = "STANDBY"
	}

	topInfo := fmt.Sprintf(
		"📡 Transport: %s | Device: %s | Status: %s\n"+
			"📊 Throughput: Tx: %d B (%d pkts) | Rx: %d B (%d pkts) | Baud: 115200 8N1\n",
		stats.ActiveTransport, stats.ConnectedDevice, statusStyle.Render(statusText),
		stats.BytesSent, stats.PacketsSent, stats.BytesReceived, stats.PacketsReceived,
	)

	macrosBar := lipgloss.NewStyle().Foreground(colorSecondary).Bold(true).Render(
		"[0:scan] [1:status] [2:telemetry] [3:ram] [4:bicep] [5:reconnect] [6:clear] [7:voice] [8:help] [9:mtu]",
	) + "\n\n"

	logHeight := h - 7
	if logHeight < 3 {
		logHeight = 3
	}

	var sb strings.Builder
	start := 0
	if len(lines) > logHeight {
		start = len(lines) - logHeight
	}
	for i := start; i < len(lines); i++ {
		l := lines[i]
		raw := l.Raw
		if len(raw) > w-6 {
			raw = raw[:w-6] + "..."
		}
		sb.WriteString(raw + "\n")
	}

	inputPrompt := fmt.Sprintf("\n> %s_", m.BTInputText)
	inputRendered := lipgloss.NewStyle().Foreground(colorCmd).Render(inputPrompt)

	content := topInfo + macrosBar + sb.String() + inputRendered
	return paneStyle.Width(w - 2).Height(h).Render(content)
}

func (m DashboardModel) renderChatTab(w, h int) string {
	chatWidth := (w * 65) / 100
	bioWidth := w - chatWidth - 2

	spinners := []string{"⠋", "⠙", "⠹", "⠸"}
	statusLine := ""
	if m.isRouting {
		statusLine = lipgloss.NewStyle().Foreground(colorWarning).Render(fmt.Sprintf("\n\n%s Genetic MoE is routing query...", spinners[m.spinnerIdx]))
	}

	chatContent := fmt.Sprintf("%s%s\n\n> %s_", m.Response, statusLine, m.InputText)
	chatPane := paneStyle.Width(chatWidth).Height(h).Render(chatContent)

	bpmStr := lipgloss.NewStyle().Foreground(colorMuted).Render("-- BPM")
	devName := lipgloss.NewStyle().Foreground(colorMuted).Render("Movesense 261030002013")
	statusBadge := lipgloss.NewStyle().Foreground(colorMuted).Render("○ STANDBY")
	batStr := ""

	if m.BioBuffer != nil {
		snap := m.BioBuffer.GetSnapshot()
		if snap.DeviceName != "" {
			if snap.Connected {
				devName = lipgloss.NewStyle().Foreground(colorSuccess).Bold(true).Render(snap.DeviceName)
				statusBadge = lipgloss.NewStyle().Foreground(colorSuccess).Bold(true).Render("● CONNECTED")
			} else {
				devName = lipgloss.NewStyle().Foreground(colorWarning).Render(snap.DeviceName)
				statusBadge = lipgloss.NewStyle().Foreground(colorMuted).Render("○ STANDBY")
			}
		}
		if snap.BatteryPct > 0 {
			batStr = fmt.Sprintf(" (%d%%)", snap.BatteryPct)
		}
		if snap.Connected && snap.LatestBPM > 0 {
			bpmStr = lipgloss.NewStyle().Foreground(colorSecondary).Bold(true).Render(fmt.Sprintf("❤ %d BPM", snap.LatestBPM))
		}
	}

	bioContent := fmt.Sprintf("%s\n\nSensor: %s\nStatus: %s%s\nRate:   %s\n\n%s\n",
		lipgloss.NewStyle().Foreground(colorPrimary).Bold(true).Render("LIVE CONTEXT"),
		devName, statusBadge, batStr, bpmStr,
		lipgloss.NewStyle().Foreground(colorPrimary).Bold(true).Render("RECENT SYSTEM EVENTS:"))

	logLimit := h - 10
	start := 0
	if len(m.logLines) > logLimit {
		start = len(m.logLines) - logLimit
	}
	for i := start; i < len(m.logLines); i++ {
		line := m.logLines[i]
		if len(line) > bioWidth-4 {
			line = line[:bioWidth-4] + "..."
		}
		bioContent += lipgloss.NewStyle().Foreground(colorMuted).Render(line) + "\n"
	}

	bioPane := paneStyle.Width(bioWidth).Height(h).Render(bioContent)
	return lipgloss.JoinHorizontal(lipgloss.Top, chatPane, bioPane)
}

func (m DashboardModel) renderTelemetryTab(w, h int) string {
	content := lipgloss.NewStyle().Foreground(colorPrimary).Bold(true).Render("▶ LIVE SPARKLINE TELEMETRY (MOVESENSE 512Hz ECG / HR)\n\n")

	sparklineHeight := h / 3
	logHeight := h - sparklineHeight - 5

	if m.BioBuffer != nil {
		snap := m.BioBuffer.GetSnapshot()
		pts := m.BioBuffer.GetLatest()

		if snap.Connected && len(pts) > 0 {
			var data []int
			for _, p := range pts {
				data = append(data, p.BPM)
			}
			sparkline := renderSparkline(data, w-4)
			content += lipgloss.NewStyle().Foreground(colorSuccess).Render(sparkline)
			batStr := ""
			if snap.BatteryPct > 0 {
				batStr = fmt.Sprintf(" | Battery: %d%%", snap.BatteryPct)
			}
			hrvStr := ""
			if snap.RMSSD > 0 {
				hrvStr = fmt.Sprintf(" | RMSSD: %.1fms | DFA-α1: %.2f", snap.RMSSD, snap.DFAAlpha1)
			}
			content += fmt.Sprintf("\nSensor: %s (%s)%s\nLatest: ❤ %d BPM | Packets: %d%s\nDSP Filter: Kamath 20%% Clinical Filter Active\n\n",
				snap.DeviceName, snap.DeviceAddress, batStr, snap.LatestBPM, len(pts), hrvStr)
		} else {
			content += lipgloss.NewStyle().Foreground(colorWarning).Render(
				fmt.Sprintf("Movesense Medical / HR+ (%s): STANDBY\nRate: -- BPM | Placement: %s\nStatus: Awaiting physical sensor BLE contact\nTip: Bridge rear contacts or fasten strap to wake.\n\n",
					snap.DeviceAddress, snap.Placement))
		}
	}

	content += lipgloss.NewStyle().Foreground(colorPrimary).Bold(true).Render(fmt.Sprintf("▶ LAUBURU KERNEL LOGS (Last %d events)\n\n", logHeight))

	start := 0
	if len(m.logLines) > logHeight {
		start = len(m.logLines) - logHeight
	}
	for i := start; i < len(m.logLines); i++ {
		line := m.logLines[i]
		if strings.Contains(line, "Error") || strings.Contains(line, "failed") {
			line = lipgloss.NewStyle().Foreground(colorError).Render(line)
		} else if strings.Contains(line, "Connected") || strings.Contains(line, "Found HR") {
			line = lipgloss.NewStyle().Foreground(colorSuccess).Render(line)
		} else {
			line = lipgloss.NewStyle().Foreground(colorText).Render(line)
		}
		if len(line) > w-4 {
			line = line[:w-4] + "..."
		}
		content += line + "\n"
	}

	return paneStyle.Width(w - 2).Height(h).Render(content)
}

func renderSparkline(data []int, width int) string {
	if len(data) == 0 {
		return ""
	}
	bars := []rune{' ', '▂', '▃', '▄', '▅', '▆', '▇', '█'}
	min, max := data[0], data[0]
	for _, v := range data {
		if v < min {
			min = v
		}
		if v > max {
			max = v
		}
	}
	if max == min {
		max = min + 1
	}
	start := 0
	if len(data) > width {
		start = len(data) - width
	}
	var sb strings.Builder
	for i := start; i < len(data); i++ {
		val := data[i]
		idx := ((val - min) * (len(bars) - 1)) / (max - min)
		sb.WriteRune(bars[idx])
	}
	return sb.String()
}

func (m DashboardModel) renderMeshTab(w, h int) string {
	title := lipgloss.NewStyle().Foreground(colorPrimary).Bold(true).Render("▶ HARDWARE MATRIX & MESH SUMMARY\n\n")
	box := lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).BorderForeground(colorSecondary).Padding(1, 2)
	summary := "📡 LAYER 0: BLE GATT (0x180D) -> Zero-IP Sensor Ingestion\n"
	summary += "🌐 LAYER 3/4: Kernel-mode Tailscale Overlay (10Gbps TB4)\n"
	summary += "🧠 INFERENCE: Prima.cpp Pipelined-Ring Parallelism (PRP)\n\n"
	summary += lipgloss.NewStyle().Foreground(colorSuccess).Bold(true).Render("🔥 POOLED AI VRAM CAPABILITY: 82.8 GB\n")
	summary += "(7-Layer Mesh Topology securely routing via Tailscale/WireGuard)\n\n"
	summary += "Target: Customer Data Pooling & Sub-Millisecond Llama-3/Qwen Sync"
	return paneStyle.Width(w - 2).Height(h).Render(title + box.Render(summary))
}

func (m DashboardModel) renderSettingsTab(w, h int) string {
	content := lipgloss.NewStyle().Foreground(colorPrimary).Bold(true).Render("⚙ SYSTEM CONFIGURATION & ROUTING\n\n")
	content += lipgloss.NewStyle().Foreground(colorWarning).Render("[LOCKED] Master Local Orchestrator Endpoint\n")
	content += "         (Requires Host Admin Privileges to re-route Port 8080)\n\n"
	content += lipgloss.NewStyle().Foreground(colorSuccess).Render("[r] Reset BLE Biometrics Scanner\n")
	content += lipgloss.NewStyle().Foreground(colorMuted).Render("    (Force-restart the 0x180D discovery routine)\n\n")
	return paneStyle.Width(w - 2).Height(h).Render(content)
}
