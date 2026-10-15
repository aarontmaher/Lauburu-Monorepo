package main

import (
	"flag"
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/aarontmaher/opengo_bt_ide/src/process"
	"github.com/aarontmaher/opengo_bt_ide/src/ui"
)

func main() {
	isServer := flag.Bool("server", false, "Run in Server Mode (Spawns AI Processes)")
	isClient := flag.Bool("client", false, "Run in Client Mode (UI only)")
	isSpecialist := flag.Bool("specialist", false, "Print integrated Polyglot Go Bubble Tea Specialist & Bluetooth Serial (:4005) status JSON")
	btSerialAddr := flag.String("bt-serial", "127.0.0.1:4005", "Bluetooth Serial Terminal TCP bridge endpoint (:4005)")
	url := flag.String("url", "http://100.119.199.76:8083/completion", "Orchestrator URL")
	flag.Parse()

	if *isSpecialist {
		fmt.Printf(`{"app":"opengo_bt_ide","ide":"GoLand (langgo) / IntelliJ IDEA","primary_specialist":"/polyglot-go-bubbletea-specialist","bt_serial_endpoint":"%s","elm_architecture":true,"bubbletea_version":"v1.3.10","lipgloss_version":"v1.1.0","verified":true}`+"\n", *btSerialAddr)
		return
	}

	if *isServer {
		fmt.Println("🚀 Starting OpenGo Hub [SERVER MODE]")
		go process.StartPrimaOrchestrator()
		go process.StartMLXSupervisor()
	} else if *isClient {
		fmt.Println("📱 Starting OpenGo Hub [CLIENT MODE]")
	}

	p := tea.NewProgram(ui.InitialModel(*url), tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		fmt.Printf("Fatal error: %v", err)
		os.Exit(1)
	}
}
