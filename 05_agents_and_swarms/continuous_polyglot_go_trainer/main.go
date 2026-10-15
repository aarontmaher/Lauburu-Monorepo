package main

import (
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

func main() {
	daemonMode := flag.Bool("daemon", false, "Run continuously in background daemon mode")
	tuiMode := flag.Bool("tui", false, "Run in interactive Bubble Tea TUI mode")
	evalOnce := flag.Bool("eval-once", false, "Execute a single verification cycle and exit")
	intervalSec := flag.Float64("interval", 30.0, "Interval between training cycles in seconds")
	flag.Parse()

	trainer := NewPolyglotTrainer(256)

	// Mode 1: Single Evaluation Pass
	if *evalOnce {
		fmt.Printf("🚀 [POLYGLOT-TRAINER] Executing single evaluation cycle (Rust/wgpu & Go)...\n")
		events := trainer.ExecuteCycle(1)
		for _, ev := range events {
			verStr := "PASSED"
			if !ev.CompilerVerified {
				verStr = fmt.Sprintf("FAILED(%d)", ev.CompilerExitCode)
			}
			fmt.Printf("  • [%s] %s (%s): Compiler %s in %.2fms | SHA: %s\n",
				ev.Language, ev.TaskID, ev.Domain, verStr, ev.CompilerLatencyMs, ev.Sha256Checksum[:12])
		}
		fmt.Printf("✅ [POLYGLOT-TRAINER] Evaluated %d curriculum items. Tri-Vault synchronized.\n", len(events))
		os.Exit(0)
	}

	// Mode 2: Interactive Bubble Tea TUI
	if *tuiMode {
		// Spawn continuous trainer in background goroutine
		go func() {
			cycle := int64(1)
			for {
				trainer.ExecuteCycle(cycle)
				cycle++
				time.Sleep(time.Duration(*intervalSec * float64(time.Second)))
			}
		}()

		p := tea.NewProgram(NewTUIModel(trainer), tea.WithAltScreen())
		if _, err := p.Run(); err != nil {
			fmt.Fprintf(os.Stderr, "Error running TUI: %v\n", err)
			os.Exit(1)
		}
		os.Exit(0)
	}

	// Mode 3: Continuous Daemon Mode (Default if --daemon or fallback)
	modeLabel := "Daemon"
	if !*daemonMode {
		modeLabel = "Foreground Continuous"
	}
	fmt.Printf("🚀 [POLYGLOT-TRAINER] Starting Continuous Polyglot Trainer %s (interval: %.1fs)...\n", modeLabel, *intervalSec)
	fmt.Printf("   • Target Domains: Rust/wgpu, Go Bubble Tea, Go Systems, Go-Rust FFI\n")
	fmt.Printf("   • Tri-Vault Lake: %s\n", DataLakeJsonlPath)
	fmt.Printf("   • LoRA Sink     : %s\n", LoraDatasetPath)
	fmt.Printf("   • Obsidian Vault: %s\n", ObsidianLedgerPath)

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	cycle := trainer.state.TotalCycles + 1
	ticker := time.NewTicker(time.Duration(*intervalSec * float64(time.Second)))
	defer ticker.Stop()

	// Initial cycle immediately
	fmt.Printf("\n[Cycle %d] Executing verification & Tri-Vault sync...\n", cycle)
	events := trainer.ExecuteCycle(cycle)
	for _, ev := range events {
		ver := "PASSED"
		if !ev.CompilerVerified {
			ver = "FAILED"
		}
		fmt.Printf("  [%s] %s (%s): %s in %.2fms\n", ev.Language, ev.TaskID, ev.Domain, ver, ev.CompilerLatencyMs)
	}
	cycle++

	for {
		select {
		case <-sigChan:
			fmt.Println("\n🛑 [POLYGLOT-TRAINER] Graceful shutdown signal received. Saving state...")
			trainer.saveState()
			trainer.syncObsidianVault()
			fmt.Println("👋 Polyglot trainer stopped cleanly.")
			return

		case <-ticker.C:
			fmt.Printf("\n[Cycle %d] Executing verification & Tri-Vault sync...\n", cycle)
			events := trainer.ExecuteCycle(cycle)
			for _, ev := range events {
				ver := "PASSED"
				if !ev.CompilerVerified {
					ver = "FAILED"
				}
				fmt.Printf("  [%s] %s (%s): %s in %.2fms\n", ev.Language, ev.TaskID, ev.Domain, ver, ev.CompilerLatencyMs)
			}
			cycle++
		}
	}
}
