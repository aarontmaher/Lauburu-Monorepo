package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/textinput"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type LogMsg struct {
	Source    string
	Content   string
	Timestamp time.Time
}

type SummaryMsg string

type model struct {
	logs        []LogMsg
	summary     string
	viewport    viewport.Model
	textInput   textinput.Model
	width       int
	height      int
	ready       bool
	logChan     chan tea.Msg
}

// Styling definitions
var (
	leftPaneStyle = lipgloss.NewStyle().
			BorderStyle(lipgloss.NormalBorder()).
			BorderForeground(lipgloss.Color("240"))

	topRightPaneStyle = lipgloss.NewStyle().
				BorderStyle(lipgloss.NormalBorder()).
				BorderForeground(lipgloss.Color("207")) // Magenta

	bottomRightPaneStyle = lipgloss.NewStyle().
				BorderStyle(lipgloss.NormalBorder()).
				BorderForeground(lipgloss.Color("226")) // Yellow

	agentNameStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("51")) // Cyan
	timestampStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("240")) // Gray
	dividerStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("236"))
)

func initialModel() model {
	ti := textinput.New()
	ti.Placeholder = "Dispatch answer..."
	ti.Focus()
	ti.CharLimit = 256
	ti.Width = 30

	logChan := make(chan tea.Msg, 256)

	return model{
		logs:      []LogMsg{},
		summary:   "Awaiting AI Synthesis from Port 8082...",
		textInput: ti,
		logChan:   logChan,
	}
}


type TickMsg time.Time

func tickCmd() tea.Cmd {
	return tea.Tick(time.Second*2, func(t time.Time) tea.Msg {
		return TickMsg(t)
	})
}

func (m model) Init() tea.Cmd {
	return tea.Batch(
		textinput.Blink,
		m.waitForLog(),
		startTailing(m.logChan),
		tickCmd(),
	)
}

func (m model) waitForLog() tea.Cmd {
	return func() tea.Msg {
		return <-m.logChan
	}
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var (
		cmd  tea.Cmd
		cmds []tea.Cmd
	)

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height

		leftWidth := (m.width * 6) / 10
		rightWidth := m.width - leftWidth

		if !m.ready {
			m.viewport = viewport.New(leftWidth-2, m.height-2)
			m.ready = true
		} else {
			m.viewport.Width = leftWidth - 2
			m.viewport.Height = m.height - 2
		}

		leftPaneStyle = leftPaneStyle.Width(leftWidth - 2).Height(m.height - 2)

		rightHeight := (m.height - 2) / 2
		topRightPaneStyle = topRightPaneStyle.Width(rightWidth - 2).Height(rightHeight - 1)
		bottomRightPaneStyle = bottomRightPaneStyle.Width(rightWidth - 2).Height(m.height - rightHeight - 3)
		m.textInput.Width = rightWidth - 4

		m.viewport.SetContent(m.formatLogs())

	case LogMsg:
		m.logs = append(m.logs, msg)
		if len(m.logs) > 100 {
			m.logs = m.logs[1:]
		}
		m.viewport.SetContent(m.formatLogs())
		m.viewport.GotoBottom()
		return m, m.waitForLog()

	
	case TickMsg:
		data, err := os.ReadFile("/tmp/swarm_speculative_summary.txt")
		if err == nil {
			m.summary = string(data)
		}
		return m, tickCmd()

	case SummaryMsg:
		m.summary = string(msg)
		return m, m.waitForLog()

	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyCtrlC, tea.KeyEsc:
			return m, tea.Quit
		case tea.KeyEnter:
			input := m.textInput.Value()
			if input != "" {
				// Handle user dispatch
				select {
				case m.logChan <- LogMsg{
					Source:    "Human Operator",
					Content:   input,
					Timestamp: time.Now(),
				}:
				default:
				}
				m.textInput.SetValue("")
			}
		}
	}

	m.textInput, cmd = m.textInput.Update(msg)
	cmds = append(cmds, cmd)

	m.viewport, cmd = m.viewport.Update(msg)
	cmds = append(cmds, cmd)

	return m, tea.Batch(cmds...)
}

func cleanContent(s string) string {
	var b strings.Builder
	inTag := false
	for _, r := range s {
		if r == '<' {
			inTag = true
			continue
		}
		if r == '>' && inTag {
			inTag = false
			continue
		}
		if !inTag {
			b.WriteRune(r)
		}
	}

	s = b.String()
	s = strings.Join(strings.Fields(s), " ")
	
	// Limit length for digestability, preventing raw JSON dumps from overflowing
	if len(s) > 150 {
		s = s[:147] + "..."
	}
	
	if s == "" {
		s = "[Complex Payload Omitted]"
	}
	
	return s
}

func (m model) formatLogs() string {
	var b strings.Builder
	for _, l := range m.logs {
		ts := timestampStyle.Render(l.Timestamp.Format("15:04:05"))
		agent := agentNameStyle.Render(l.Source)
		content := cleanContent(l.Content)
		
		// Use Lipgloss for proper wrapping
		lineStyle := lipgloss.NewStyle().Width(m.viewport.Width)
		line := lineStyle.Render(fmt.Sprintf("%s [%s] -> %s", ts, agent, content))
		divider := dividerStyle.Render(strings.Repeat("-", m.viewport.Width/2))
		
		b.WriteString(line + "\n" + divider + "\n")
	}
	return b.String()
}

func (m model) View() string {
	if !m.ready {
		return "\n  Initializing Sovereign Swarm Control Terminal..."
	}

	left := leftPaneStyle.Render(m.viewport.View())
	
	topRightContent := lipgloss.NewStyle().Padding(0, 1).Render("Speculative AI Synthesis\n\n" + m.summary)
	topRight := topRightPaneStyle.Render(topRightContent)
	
	backlogView := "Blocked Agents Waiting for Input:\n- None currently blocked\n\n"
	inputView := m.textInput.View()
	bottomRightContent := lipgloss.NewStyle().Padding(0, 1).Render(backlogView + inputView)
	bottomRight := bottomRightPaneStyle.Render(bottomRightContent)

	right := lipgloss.JoinVertical(lipgloss.Left, topRight, bottomRight)
	return lipgloss.JoinHorizontal(lipgloss.Top, left, right)
}

// Background worker tailing the newest JSONL transcript
func startTailing(out chan<- tea.Msg) tea.Cmd {
	return func() tea.Msg {
		go func() {
			pattern := "/Users/aaron/.gemini/antigravity/brain/*/.system_generated/logs/transcript.jsonl"
			files, err := filepath.Glob(pattern)
			if err != nil || len(files) == 0 {
				// No files found yet, retry loop in a real app, here we just return
				// For the sake of standard operation, let's inject a dummy log
				time.Sleep(1 * time.Second)
				out <- LogMsg{
					Source:    "System",
					Content:   "Waiting for swarm transcripts to appear...",
					Timestamp: time.Now(),
				}
			}

			var latestFile string
			var latestMod time.Time
			for _, f := range files {
				info, err := os.Stat(f)
				if err == nil && info.ModTime().After(latestMod) {
					latestMod = info.ModTime()
					latestFile = f
				}
			}

			if latestFile == "" {
				return
			}

			file, err := os.Open(latestFile)
			if err != nil {
				return
			}
			defer file.Close()

			// In a real application, you might tail the file continuously.
			// Here we read it all, then poll for new lines.
			scanner := bufio.NewScanner(file)
			// Increase buffer capacity for large JSON lines
			buf := make([]byte, 1024*1024)
			scanner.Buffer(buf, 10*1024*1024)

			for {
				for scanner.Scan() {
					line := scanner.Text()
					
					var entry struct {
						Source  string `json:"source"`
						Content string `json:"content"`
						Type    string `json:"type"`
					}
					
					if err := json.Unmarshal([]byte(line), &entry); err == nil {
						if entry.Source != "" {
							select {
							case out <- LogMsg{
								Source:    entry.Source,
								Content:   entry.Content,
								Timestamp: time.Now(),
							}:
							default:
							}
						}
					}
				}
				time.Sleep(500 * time.Millisecond)
			}
		}()
		return nil
	}
}

func main() {
	p := tea.NewProgram(initialModel(), tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		log.Fatal(err)
	}
}
