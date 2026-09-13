package main

import (
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/aarontmaher/lauburu-opencode/internal/api"
	"github.com/aarontmaher/lauburu-opencode/internal/biometrics"
	"github.com/aarontmaher/lauburu-opencode/internal/bluetooth"
	"github.com/aarontmaher/lauburu-opencode/internal/config"
	"github.com/aarontmaher/lauburu-opencode/internal/mesh"
	"github.com/aarontmaher/lauburu-opencode/internal/router"
	"github.com/aarontmaher/lauburu-opencode/internal/tui"
)

func main() {
	logPath := "/tmp/lauburu_cli.log"
	if termuxPrefix := os.Getenv("PREFIX"); termuxPrefix != "" {
		logPath = termuxPrefix + "/tmp/lauburu_cli.log"
	}
	f, _ := os.OpenFile(logPath, os.O_RDWR|os.O_CREATE|os.O_APPEND, 0666)
	if f != nil {
		log.SetOutput(f)
		defer f.Close()
	}

	// Bypass Cobra completely to avoid Android/Termux linker arg shifting bugs
	args := strings.Join(os.Args, " ")

	if strings.Contains(args, "--help") || strings.Contains(args, "-h") {
		fmt.Print("Lauburu OpenCode Go Sovereign Mesh CLI & Bluetooth RFConnect Terminal\n\n" +
			"Usage:\n" +
			"  lauburu [command] [flags]\n\n" +
			"Commands:\n" +
			"  worker                    Run autonomous headless background mesh worker (Movesense BLE + IP-less BT + TCP :4050)\n" +
			"  rfconnect                 Launch TUI directly in BT RFConnect Terminal\n" +
			"  rfconnect --scan          Perform standalone BLE RFConnect discovery scan\n" +
			"  rfconnect --connect=<id>  Connect directly to target BLE NUS peripheral\n" +
			"  bt-daemon                 Run headless background Bluetooth Terminal Daemon\n" +
			"  serve                     Start OpenAI-compatible REST server (:8080)\n\n" +
			"Flags:\n" +
			"  --dev                     Enable development mode\n" +
			"  --help                    Show this help message\n")
		return
	}
	
	cfg, _ := config.LoadConfig()
	r := router.NewRouter(cfg)

	if strings.Contains(args, "serve") {
		srv := api.NewServer(r)
		log.Fatal(srv.Start(":8080"))
		return
	}

	bioBuffer := biometrics.NewTelemetryBuffer()
	go func() {
		_ = biometrics.StartScanner(bioBuffer)
	}()

	btTerminal := bluetooth.NewBluetoothTerminal(r)
	btTerminal.SetTelemetryBuffer(bioBuffer)
	_ = btTerminal.Start()
	defer btTerminal.Stop()

	// Standalone headless Autonomous Mesh Worker & Bluetooth Terminal Daemon mode
	if strings.Contains(args, "worker") || strings.Contains(args, "bt-daemon") || strings.Contains(args, "terminal-daemon") {
		tcpBridge := bluetooth.NewTCPBridge(btTerminal, bioBuffer)
		_ = tcpBridge.Start(4050)
		defer tcpBridge.Stop()
		log.Printf("[HEADLESS-WORKER] OpenCode Go Autonomous Mesh Worker Running on %s (TCP :4050 / :4051)...", bluetooth.ResolveStreamPipePath())
		select {}
	}

	// Standalone CLI Scan mode
	if strings.Contains(args, "--scan") {
		fmt.Println("\033[1;36m[RFCONNECT]\033[0m Scanning for BLE NUS & Movesense peripherals (3s)...")
		_, _ = btTerminal.ScanDevices(3 * time.Second)
		if rf := btTerminal.GetRFConnect(); rf != nil {
			fmt.Println(rf.FormatDiscoveredDevices())
		}
		return
	}

	// Standalone CLI Connect mode
	for _, arg := range os.Args {
		if strings.HasPrefix(arg, "--connect=") {
			target := strings.TrimPrefix(arg, "--connect=")
			fmt.Println(fmt.Sprintf("\033[1;36m[RFCONNECT]\033[0m Connecting to %s...", target))
			if err := btTerminal.ConnectDevice(target); err != nil {
				fmt.Println(fmt.Sprintf("\033[31m[RFCONNECT ERROR]\033[0m %v", err))
				return
			}
			fmt.Println("\033[1;32m[RFCONNECT CONNECTED]\033[0m Session established. Streaming to pipe...")
			select {}
		}
	}

	// Default to Chat & Bluetooth TUI
	if cfg.AuthKey != "" {
		m, err := mesh.StartMesh(cfg)
		if err != nil {
			log.Printf("Mesh error: %v", err)
		} else {
			defer m.Close()
		}
	}

	role := mesh.ProfileHardware()
	isDev := strings.Contains(args, "--dev")
	initialModel := tui.InitialModel(role, bioBuffer, btTerminal, isDev)

	// If invoked with 'rfconnect' or 'bt' or 'terminal', jump directly to Tab 5 (BT RFConnect)
	if strings.Contains(args, "rfconnect") || strings.Contains(args, "bt") || strings.Contains(args, "terminal") {
		initialModel.SetActiveTab(4)
	}

	p := tea.NewProgram(initialModel, tea.WithAltScreen(), tea.WithMouseCellMotion())
	if _, err := p.Run(); err != nil {
		log.Fatal(err)
	}
}
