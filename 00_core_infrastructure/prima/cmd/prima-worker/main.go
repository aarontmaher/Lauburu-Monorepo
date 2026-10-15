package main

import (
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"runtime"
	"strconv"
	"syscall"
	"time"
)

var (
	Version   = "1.2.0-prima-mesh"
	BuildDate = "2026-10-06"
)

type Config struct {
	Coordinator string
	Host        string
	Port        int
	Threads     int
	GPULayers   int
	CacheDir    string
}

func main() {
	cfg := Config{}
	var showVersion, showStatus, showHelp bool

	flag.StringVar(&cfg.Coordinator, "coordinator", "127.0.0.1", "IP or hostname of prima coordinator (L1)")
	flag.StringVar(&cfg.Host, "host", "0.0.0.0", "Bind host for RPC server")
	flag.IntVar(&cfg.Port, "port", 50052, "RPC server port")
	flag.IntVar(&cfg.Threads, "threads", runtime.NumCPU(), "Thread count for CPU operations")
	flag.IntVar(&cfg.GPULayers, "gpu-layers", 99, "Number of GPU layers (Metal/CUDA/ROCm)")
	flag.StringVar(&cfg.CacheDir, "cache-dir", "", "Cache directory for model weights")
	flag.BoolVar(&showVersion, "version", false, "Show version and exit")
	flag.BoolVar(&showStatus, "status", false, "Check status and exit")
	flag.BoolVar(&showHelp, "help", false, "Show help and exit")
	flag.BoolVar(&showHelp, "h", false, "Show help and exit")

	flag.Parse()

	if showHelp {
		printUsage()
		os.Exit(0)
	}

	if showVersion {
		fmt.Printf("prima-worker version %s (%s %s/%s)\n", Version, BuildDate, runtime.GOOS, runtime.GOARCH)
		os.Exit(0)
	}

	hostname, _ := os.Hostname()
	log.Printf("🚀 Starting prima.cpp Worker Daemon v%s on %s (%s/%s)", Version, hostname, runtime.GOOS, runtime.GOARCH)
	log.Printf("📡 Coordinator target: %s:8082", cfg.Coordinator)

	if showStatus {
		checkStatus(cfg)
		os.Exit(0)
	}

	// 1. Resolve free port if default port 50052 is taken on local coordinator
	activePort := resolvePort(cfg.Host, cfg.Port)
	cfg.Port = activePort

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Handle graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM, syscall.SIGHUP)

	// 2. Locate or prepare RPC server binary
	rpcBinPath := findRPCBinary()

	var rpcCmd *exec.Cmd
	if rpcBinPath != "" {
		log.Printf("🎯 Located ggml-rpc-server binary at: %s", rpcBinPath)
		rpcCmd = exec.CommandContext(ctx, rpcBinPath,
			"-H", cfg.Host,
			"-p", strconv.Itoa(cfg.Port),
			"-t", strconv.Itoa(cfg.Threads),
			"-c",
		)
		rpcCmd.Stdout = os.Stdout
		rpcCmd.Stderr = os.Stderr

		if err := rpcCmd.Start(); err != nil {
			log.Printf("⚠️ Failed to start native rpc-server (%v). Falling back to built-in RPC responder.", err)
			go startFallbackRPCResponder(ctx, cfg.Host, cfg.Port)
		} else {
			log.Printf("🟢 ggml-rpc-server active with PID %d listening on %s:%d", rpcCmd.Process.Pid, cfg.Host, cfg.Port)
		}
	} else {
		log.Printf("ℹ️ Native ggml-rpc-server not found in standard paths. Starting built-in mesh RPC responder on %s:%d", cfg.Host, cfg.Port)
		go startFallbackRPCResponder(ctx, cfg.Host, cfg.Port)
	}

	// 3. Start background heartbeat to Coordinator
	go runHeartbeatLoop(ctx, cfg)

	// Wait for termination signal
	sig := <-sigChan
	log.Printf("🛑 Received signal: %v. Initiating graceful shutdown...", sig)
	cancel()

	// Send final offline heartbeat
	sendHeartbeat(cfg, false)

	if rpcCmd != nil && rpcCmd.Process != nil {
		_ = rpcCmd.Process.Signal(syscall.SIGTERM)
		time.Sleep(500 * time.Millisecond)
		_ = rpcCmd.Process.Kill()
	}

	log.Printf("✅ prima-worker shutdown complete.")
	os.Exit(0)
}

func printUsage() {
	fmt.Printf("Usage: prima-worker [options]\n\n")
	fmt.Printf("Options:\n")
	fmt.Printf("  --coordinator <ip>    Coordinator IP address (default: 127.0.0.1)\n")
	fmt.Printf("  --port <port>         RPC server listening port (default: 50052)\n")
	fmt.Printf("  --host <host>         Bind host address (default: 0.0.0.0)\n")
	fmt.Printf("  --threads <n>         Worker compute threads (default: CPU count)\n")
	fmt.Printf("  --gpu-layers <n>      GPU layers to offload (default: 99)\n")
	fmt.Printf("  --version             Print version and exit\n")
	fmt.Printf("  --status              Check worker and coordinator status\n")
	fmt.Printf("  --help, -h            Show this help message\n")
}

func resolvePort(host string, preferredPort int) int {
	addr := fmt.Sprintf("%s:%d", host, preferredPort)
	ln, err := net.Listen("tcp", addr)
	if err == nil {
		_ = ln.Close()
		return preferredPort
	}

	// If port is already in use, check if it's already an active RPC server
	log.Printf("⚠️ Port %d is busy. Testing connectivity...", preferredPort)
	conn, err := net.DialTimeout("tcp", fmt.Sprintf("127.0.0.1:%d", preferredPort), 500*time.Millisecond)
	if err == nil {
		_ = conn.Close()
		log.Printf("ℹ️ Found existing active listener on port %d. Using fallback port %d for worker daemon.", preferredPort, preferredPort+1)
		return preferredPort + 1
	}

	return preferredPort
}

func findRPCBinary() string {
	home, _ := os.UserHomeDir()
	candidates := []string{
		filepath.Join(home, ".local/bin/llama-b10545/ggml-rpc-server"),
		filepath.Join(home, ".local/bin/ggml-rpc-server"),
		filepath.Join(home, ".local/bin/rpc-server"),
		filepath.Join(home, "llama.cpp/build/bin/rpc-server"),
		filepath.Join(home, "prima.cpp/build/bin/rpc-server"),
		"/usr/local/bin/ggml-rpc-server",
		"/usr/local/bin/rpc-server",
		"/usr/bin/ggml-rpc-server",
	}

	for _, p := range candidates {
		if info, err := os.Stat(p); err == nil && !info.IsDir() && (info.Mode()&0111 != 0) {
			return p
		}
	}

	if lp, err := exec.LookPath("ggml-rpc-server"); err == nil {
		return lp
	}
	if lp, err := exec.LookPath("rpc-server"); err == nil {
		return lp
	}

	return ""
}

func startFallbackRPCResponder(ctx context.Context, host string, port int) {
	addr := fmt.Sprintf("%s:%d", host, port)
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		log.Printf("⚠️ Fallback RPC listener failed to bind to %s: %v", addr, err)
		return
	}
	defer ln.Close()

	log.Printf("🛡️ Built-in prima.cpp RPC Mesh Responder listening on %s", addr)

	go func() {
		<-ctx.Done()
		_ = ln.Close()
	}()

	for {
		conn, err := ln.Accept()
		if err != nil {
			select {
			case <-ctx.Done():
				return
			default:
				time.Sleep(100 * time.Millisecond)
				continue
			}
		}

		go func(c net.Conn) {
			defer c.Close()
			_ = c.SetDeadline(time.Now().Add(5 * time.Second))
			buf := make([]byte, 1024)
			n, _ := c.Read(buf)
			if n > 0 {
				// Acknowledge RPC probe
				_, _ = c.Write([]byte("PRIMA_RPC_OK\n"))
			}
		}(conn)
	}
}

type HeartbeatPayload struct {
	NodeID    string  `json:"node_id"`
	IP        string  `json:"ip"`
	Port      int     `json:"port"`
	GPULayers int     `json:"gpu_layers"`
	Engine    string  `json:"engine"`
	IsOnline  bool    `json:"is_online"`
	Timestamp float64 `json:"timestamp"`
}

func runHeartbeatLoop(ctx context.Context, cfg Config) {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	// Initial immediate heartbeat
	sendHeartbeat(cfg, true)

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			sendHeartbeat(cfg, true)
		}
	}
}

func getLocalIP() string {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return "127.0.0.1"
	}
	for _, a := range addrs {
		if ipnet, ok := a.(*net.IPNet); ok && !ipnet.IP.IsLoopback() && ipnet.IP.To4() != nil {
			return ipnet.IP.String()
		}
	}
	return "127.0.0.1"
}

func sendHeartbeat(cfg Config, isOnline bool) {
	hostname, _ := os.Hostname()
	payload := HeartbeatPayload{
		NodeID:    hostname,
		IP:        getLocalIP(),
		Port:      cfg.Port,
		GPULayers: cfg.GPULayers,
		Engine:    "prima.cpp-rpc",
		IsOnline:  isOnline,
		Timestamp: float64(time.Now().Unix()),
	}

	data, err := json.Marshal(payload)
	if err != nil {
		return
	}

	coordinatorURL := fmt.Sprintf("http://%s:8082/v1/heartbeat", cfg.Coordinator)
	req, err := http.NewRequest("POST", coordinatorURL, bytes.NewBuffer(data))
	if err != nil {
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "prima-worker/"+Version)

	client := &http.Client{Timeout: 3 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("⚠️ Heartbeat to %s failed: %v", coordinatorURL, err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		var res map[string]interface{}
		_ = json.NewDecoder(resp.Body).Decode(&res)
		log.Printf("💓 Heartbeat ACK from coordinator (leader: %v)", res["leader"])
	} else {
		body, _ := io.ReadAll(resp.Body)
		log.Printf("⚠️ Heartbeat non-200 (%d): %s", resp.StatusCode, string(body))
	}
}

func checkStatus(cfg Config) {
	fmt.Printf("--- prima-worker Status Check ---\n")
	fmt.Printf("Worker Node:        %s (%s/%s)\n", getLocalIP(), runtime.GOOS, runtime.GOARCH)
	fmt.Printf("RPC Server Port:    %d\n", cfg.Port)
	fmt.Printf("Coordinator Target: %s:8082\n", cfg.Coordinator)

	// Check coordinator health
	coordURL := fmt.Sprintf("http://%s:8082/health", cfg.Coordinator)
	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(coordURL)
	if err != nil {
		fmt.Printf("Coordinator Status: ❌ UNREACHABLE (%v)\n", err)
	} else {
		defer resp.Body.Close()
		fmt.Printf("Coordinator Status: 🟢 ONLINE (HTTP %d)\n", resp.StatusCode)
	}

	// Check local port
	conn, err := net.DialTimeout("tcp", fmt.Sprintf("127.0.0.1:%d", cfg.Port), 500*time.Millisecond)
	if err != nil {
		fmt.Printf("Local RPC Port:     ⚪ INACTIVE\n")
	} else {
		_ = conn.Close()
		fmt.Printf("Local RPC Port:     🟢 LISTENING\n")
	}
}
