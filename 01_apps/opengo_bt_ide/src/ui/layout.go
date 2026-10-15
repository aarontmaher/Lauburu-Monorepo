package ui

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/textarea"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/aarontmaher/opengo_bt_ide/src/mesh"
)

var (
	activeTabStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#00FF00")).Padding(0, 1)
	inactiveTabStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#666666")).Padding(0, 1)
	borderStyle = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(1)
	agentStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#7D56F4"))
)

type tickMsg time.Time

type model struct {
	activeTab int
	url       string
	
	// Chat pane
	textarea textarea.Model
	viewport viewport.Model
	messages []string
	
	// Mesh pane
	nodes []mesh.Node
}

func InitialModel(targetURL string) model {
	ta := textarea.New()
	ta.Placeholder = "Command the Orchestrator..."
	ta.Focus()
	ta.Prompt = "❯ "
	ta.SetHeight(3)
	ta.SetWidth(80)

	vp := viewport.New(80, 15)
	vp.SetContent("OpenGo Mesh Hub.\nConnected to: " + targetURL)

	return model{
		activeTab: 0,
		url:       targetURL,
		textarea:  ta,
		viewport:  vp,
		messages:  []string{},
		nodes:     mesh.GetNodes(),
	}
}

func (m model) Init() tea.Cmd {
	return tea.Batch(textarea.Blink, tickCmd())
}

func tickCmd() tea.Cmd {
	return tea.Tick(10*time.Second, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

type aiResponseMsg struct {
	Text string
}

func queryLLM(url, prompt string) string {
	payload := map[string]interface{}{
		"prompt": prompt,
		"n_predict": 128,
	}
	jsonPayload, _ := json.Marshal(payload)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonPayload))
	if err != nil {
		return "Error: " + err.Error()
	}
	defer resp.Body.Close()
	body, _ := ioutil.ReadAll(resp.Body)
	var result map[string]interface{}
	json.Unmarshal(body, &result)
	if val, ok := result["content"]; ok {
		return val.(string)
	}
	return "No content"
}

func askLLM(url, prompt string) tea.Cmd {
	return func() tea.Msg {
		return aiResponseMsg{Text: queryLLM(url, prompt)}
	}
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var tiCmd, vpCmd tea.Cmd

	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "esc":
			return m, tea.Quit
		case "tab":
			m.activeTab = (m.activeTab + 1) % 3
			return m, nil
		case "enter":
			if m.activeTab == 0 && m.textarea.Value() != "" {
				v := m.textarea.Value()
				m.messages = append(m.messages, "You: "+v)
				m.viewport.SetContent(strings.Join(m.messages, "\n\n"))
				m.viewport.GotoBottom()
				m.textarea.Reset()
				return m, askLLM(m.url, v)
			}
		}
	case aiResponseMsg:
		m.messages = append(m.messages, agentStyle.Render("Qwen: "+msg.Text))
		m.viewport.SetContent(strings.Join(m.messages, "\n\n"))
		m.viewport.GotoBottom()
	case tickMsg:
		if m.activeTab == 1 {
			m.nodes = mesh.GetNodes()
		}
		return m, tickCmd()
	}

	m.textarea, tiCmd = m.textarea.Update(msg)
	m.viewport, vpCmd = m.viewport.Update(msg)
	return m, tea.Batch(tiCmd, vpCmd)
}

func (m model) View() string {
	tabs := []string{"[0] Chat", "[1] Mesh", "[2] Training"}
	var renderedTabs []string
	for i, t := range tabs {
		if i == m.activeTab {
			renderedTabs = append(renderedTabs, activeTabStyle.Render(t))
		} else {
			renderedTabs = append(renderedTabs, inactiveTabStyle.Render(t))
		}
	}
	tabRow := lipgloss.JoinHorizontal(lipgloss.Top, renderedTabs...)

	var content string
	if m.activeTab == 0 {
		content = borderStyle.Render(m.viewport.View()) + "\n" + m.textarea.View()
	} else if m.activeTab == 1 {
		sb := strings.Builder{}
		sb.WriteString("=== MESH TELEMETRY ===\n\n")
		sb.WriteString(mesh.GetHostRAM() + "\n\n")
		for _, n := range m.nodes {
			sb.WriteString(fmt.Sprintf("%-15s | %-15s | %s\n", n.Name, n.IP, n.Status))
		}
		content = borderStyle.Render(sb.String())
	} else {
		content = borderStyle.Render("=== MLX TRAINING SUPERVISOR ===\n\nStatus: Gathering clean loss metrics...\n(Metrics parsing via os/exec pipeline active)")
	}

	return fmt.Sprintf("%s\n\n%s", tabRow, content)
}
