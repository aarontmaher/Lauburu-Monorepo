package process

import (
	"fmt"
	"os/exec"
	"strings"
	"time"
)

func pingTailscale(ip string) bool {
	cmd := exec.Command("ping", "-c", "1", "-W", "1", ip)
	err := cmd.Run()
	return err == nil
}

func StartPrimaOrchestrator() {
	mbpIP := "100.103.212.21"
	mbaIP := "100.121.202.34"

	var rpcArgs []string
	if pingTailscale(mbpIP) {
		rpcArgs = append(rpcArgs, mbpIP+":50053")
	}
	if pingTailscale(mbaIP) {
		rpcArgs = append(rpcArgs, mbaIP+":50053")
	}

	args := []string{
		"-m", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen_38_max.gguf",
		"--port", "8085",
		"--host", "0.0.0.0",
		"-c", "32768",
		"-ngl", "20",
	}

	if len(rpcArgs) > 0 {
		args = append(args, "--rpc", strings.Join(rpcArgs, ","))
	}

	// For safety, kill any existing llama-server 8085
	exec.Command("pkill", "-f", "llama-server.*8085").Run()

	cmd := exec.Command("/Users/aaron/.local/bin/llama-server", args...)
	// In a real scenario, we'd capture stdout/stderr to a channel for the UI
	err := cmd.Start()
	if err != nil {
		fmt.Println("Failed to start Prima Orchestrator:", err)
		return
	}
	
	// Keep alive
	for {
		time.Sleep(10 * time.Second)
	}
}
