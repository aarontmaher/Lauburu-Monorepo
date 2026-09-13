package bluetooth

import (
	"bufio"
	"context"
	"fmt"
	"log"
	"net"
	"net/url"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/coder/websocket"
	"github.com/aarontmaher/lauburu-opencode/internal/biometrics"
)

// TCPBridge manages bi-directional TCP/WebSocket piping between Port 4050,
// out-of-band Bluetooth stream pipes, and live Movesense biometrics.
type TCPBridge struct {
	terminal      *BluetoothTerminal
	bioBuffer     *biometrics.TelemetryBuffer
	mu            sync.RWMutex
	tcpListener   net.Listener
	tcpPort       int
	tcpClients    map[net.Conn]struct{}
	wsConn        *websocket.Conn
	running       bool
	stopChan      chan struct{}
	bytesPiped    uint64
	packetsPiped  uint64
	activeMode    string // "DIRECT_SERVER_4050", "PORT_FALLBACK_4051", "WS_CLIENT_BRIDGE"
}

// NewTCPBridge creates a new headless background bridge for the Bluetooth Terminal.
func NewTCPBridge(term *BluetoothTerminal, buffer *biometrics.TelemetryBuffer) *TCPBridge {
	return &TCPBridge{
		terminal:   term,
		bioBuffer:  buffer,
		tcpClients: make(map[net.Conn]struct{}),
		stopChan:   make(chan struct{}),
		activeMode: "STANDBY",
	}
}

// Start launches the background TCP listeners and WebSocket bridges.
func (b *TCPBridge) Start(preferredPort int) error {
	b.mu.Lock()
	if b.running {
		b.mu.Unlock()
		return nil
	}
	b.running = true
	b.mu.Unlock()

	// 1. Attempt to bind preferredPort (4050), or fall back to preferredPort+1 (4051)
	ln, err := net.Listen("tcp", fmt.Sprintf(":%d", preferredPort))
	if err != nil {
		log.Printf("[TCP-BRIDGE] Port :%d occupied (%v). Activating fallback on :%d & WS Client Bridge to :4050...", preferredPort, err, preferredPort+1)
		ln2, err2 := net.Listen("tcp", fmt.Sprintf(":%d", preferredPort+1))
		if err2 == nil {
			b.tcpListener = ln2
			b.tcpPort = preferredPort + 1
			b.activeMode = fmt.Sprintf("FALLBACK_TCP_%d_AND_WS_4050", b.tcpPort)
		} else {
			log.Printf("[TCP-BRIDGE] Warning: Fallback TCP port also unavailable: %v", err2)
			b.activeMode = "WS_CLIENT_4050_ONLY"
		}
		// Also connect as an active WebSocket client to Port 4050 IDE server
		go b.maintainWebSocketClient("ws://127.0.0.1:4050/ws/terminal")
	} else {
		b.tcpListener = ln
		b.tcpPort = preferredPort
		b.activeMode = fmt.Sprintf("DIRECT_TCP_SERVER_%d", b.tcpPort)
	}

	if b.tcpListener != nil {
		go b.acceptLoop()
	}

	// 2. Start continuous Movesense & Bluetooth frame pipe broadcaster
	go b.broadcastTelemetryLoop()

	log.Printf("[TCP-BRIDGE] Headless Mesh Worker Bridge Active (Mode: %s)", b.activeMode)
	return nil
}

// Stop cleanly terminates the bridge
func (b *TCPBridge) Stop() {
	b.mu.Lock()
	if !b.running {
		b.mu.Unlock()
		return
	}
	b.running = false
	close(b.stopChan)

	if b.tcpListener != nil {
		_ = b.tcpListener.Close()
	}
	for conn := range b.tcpClients {
		_ = conn.Close()
	}
	if b.wsConn != nil {
		_ = b.wsConn.Close(websocket.StatusNormalClosure, "bridge shutting down")
	}
	b.mu.Unlock()
}

func (b *TCPBridge) acceptLoop() {
	for {
		conn, err := b.tcpListener.Accept()
		if err != nil {
			select {
			case <-b.stopChan:
				return
			default:
				log.Printf("[TCP-BRIDGE] Accept error: %v", err)
				return
			}
		}

		b.mu.Lock()
		b.tcpClients[conn] = struct{}{}
		b.mu.Unlock()

		go b.handleTCPConnection(conn)
	}
}

func (b *TCPBridge) handleTCPConnection(conn net.Conn) {
	defer func() {
		b.mu.Lock()
		delete(b.tcpClients, conn)
		b.mu.Unlock()
		_ = conn.Close()
	}()

	// Send Kai Morich Anti-Staircasing Welcome Banner
	banner := fmt.Sprintf("\033[1;36m╔══════════════════════════════════════════════════════════════════╗\033[0m\r\n"+
		"\033[1;36m║   ⚡ LAUBURU AUTONOMOUS HEADLESS MESH WORKER (TCP :%d) ⚡  ║\033[0m\r\n"+
		"\033[1;36m╚══════════════════════════════════════════════════════════════════╝\033[0m\r\n"+
		"\033[32m• Role:\033[0m          Autonomous Headless Mesh Worker & Biometrics Pipe\r\n"+
		"\033[32m• Transports:\033[0m    BLE NUS (6E400001), RFCOMM SPP, TCP :4050/4051\r\n"+
		"\033[32m• Movesense:\033[0m     512Hz Pan-Tompkins QRS DSP & Zone 2 Telemetry\r\n"+
		"\033[32m• IP-less Link:\033[0m  Layer 0 Bluetooth Radio MAC (0.0.0.0)\r\n"+
		"\033[32m• Local AI Core:\033[0m Qwen 3.8 Max (:8082 Master Local Orchestrator)\r\n"+
		"\033[90m──────────────────────────────────────────────────────────────────\033[0m\r\n"+
		"Type 'status' (M1), 'bicep' (M4 Movesense), 'help' (M8), or prompt local AI.\r\n\r\n", b.tcpPort)
	_, _ = conn.Write([]byte(FormatAntiStaircasing(banner)))

	scanner := bufio.NewScanner(conn)
	for scanner.Scan() {
		rawCmd := scanner.Text()
		trimmed := strings.TrimSpace(rawCmd)
		if trimmed == "" {
			continue
		}

		atomic.AddUint64(&b.bytesPiped, uint64(len(trimmed)))
		atomic.AddUint64(&b.packetsPiped, 1)

		// Echo command in terminal green
		_, _ = conn.Write([]byte(fmt.Sprintf("\033[32mlauburu-tcp>\033[0m %s\r\n", trimmed)))

		// Execute through BluetoothTerminal (Macros M1-M10, Movesense, or Local AI)
		resp := b.terminal.WriteCommand(trimmed)
		if resp != "" {
			out := FormatAntiStaircasing(resp) + "\r\n"
			_, _ = conn.Write([]byte(out))
		}
	}
}

// maintainWebSocketClient connects to Port 4050 IDE WebSocket if active
func (b *TCPBridge) maintainWebSocketClient(wsURL string) {
	u, err := url.Parse(wsURL)
	if err != nil {
		return
	}

	for {
		select {
		case <-b.stopChan:
			return
		default:
		}

		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		c, _, err := websocket.Dial(ctx, u.String(), nil)
		cancel()
		if err != nil {
			time.Sleep(3 * time.Second)
			continue
		}

		b.mu.Lock()
		b.wsConn = c
		b.mu.Unlock()

		log.Printf("[TCP-BRIDGE] Connected to Bluetooth Terminal IDE WebSocket (%s)", wsURL)

		// Read loop from WebSocket
		for {
			_, msg, err := c.Read(context.Background())
			if err != nil {
				break
			}

			cmd := strings.TrimSpace(string(msg))
			if cmd != "" && !strings.Contains(cmd, "⚡ LAUBURU") {
				resp := b.terminal.WriteCommand(cmd)
				if resp != "" {
					_ = c.Write(context.Background(), websocket.MessageText, []byte(resp))
				}
			}
		}

		b.mu.Lock()
		b.wsConn = nil
		b.mu.Unlock()
		time.Sleep(2 * time.Second)
	}
}

// broadcastTelemetryLoop streams live Movesense biometrics to all TCP clients & stream pipes
func (b *TCPBridge) broadcastTelemetryLoop() {
	ticker := time.NewTicker(500 * time.Millisecond)
	defer ticker.Stop()

	var lastBPM int
	var lastRMSSD float64

	for {
		select {
		case <-b.stopChan:
			return
		case <-ticker.C:
			if b.bioBuffer == nil {
				continue
			}

			snap := b.bioBuffer.GetSnapshot()
			if !snap.Connected || snap.LatestBPM == 0 {
				continue
			}

			// If biometrics changed or periodically, emit frame
			if snap.LatestBPM != lastBPM || snap.RMSSD != lastRMSSD {
				lastBPM = snap.LatestBPM
				lastRMSSD = snap.RMSSD

				zone := "Zone 1 (Recovery)"
				if snap.LatestBPM >= 100 && snap.LatestBPM < 140 {
					zone = "Zone 2 (Aerobic Endurance)"
				} else if snap.LatestBPM >= 140 {
					zone = "Zone 3+ (Threshold/Anaerobic)"
				}

				frame := fmt.Sprintf(
					"\033[1;32m[MOVESENSE-512Hz]\033[0m HR: \033[1;31m%d BPM\033[0m | RMSSD: %.1fms | DFA-α1: %.2f | Batt: %d%% | %s\r\n",
					snap.LatestBPM, snap.RMSSD, snap.DFAAlpha1, snap.BatteryPct, zone,
				)

				// Broadcast to all active TCP clients
				b.Broadcast([]byte(frame))

				// Mirror to out-of-band stream pipe for Layer 0 Bluetooth terminal
				pipePath := ResolveStreamPipePath()
				if f, err := os.OpenFile(pipePath, os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0644); err == nil {
					_, _ = f.WriteString(frame)
					_ = f.Close()
				}
			}
		}
	}
}

// Broadcast sends raw bytes to all connected TCP clients with anti-staircasing CRLF
func (b *TCPBridge) Broadcast(data []byte) {
	b.mu.RLock()
	defer b.mu.RUnlock()

	for conn := range b.tcpClients {
		_, _ = conn.Write(data)
	}

	if b.wsConn != nil {
		_ = b.wsConn.Write(context.Background(), websocket.MessageText, data)
	}
}

// GetStats returns live bridge throughput metrics
func (b *TCPBridge) GetStats() (int, string, uint64, uint64) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return len(b.tcpClients), b.activeMode, atomic.LoadUint64(&b.bytesPiped), atomic.LoadUint64(&b.packetsPiped)
}
