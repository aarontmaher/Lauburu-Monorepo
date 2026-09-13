package bluetooth

import (
	"bufio"
	"net"
	"strings"
	"testing"
	"time"

	"github.com/aarontmaher/lauburu-opencode/internal/biometrics"
)

func TestTCPBridgeDirectServerAndCommandRouting(t *testing.T) {
	bioBuffer := biometrics.NewTelemetryBuffer()
	bioBuffer.UpdateLiveMetrics("Movesense 261030002013", "74:92:BA:11:36:D6", true, 89, 45.2, 0.98, "Left Bicep", "ECG-512Hz")
	bioBuffer.AddPoint(125, []int{480, 485, 482})

	term := NewBluetoothTerminal(nil)
	term.SetTelemetryBuffer(bioBuffer)
	_ = term.Start()
	defer term.Stop()

	bridge := NewTCPBridge(term, bioBuffer)
	testPort := 14050
	err := bridge.Start(testPort)
	if err != nil {
		t.Fatalf("Failed to start TCPBridge on :%d: %v", testPort, err)
	}
	defer bridge.Stop()

	// Wait for listener to bind
	time.Sleep(50 * time.Millisecond)

	// 1. Connect TCP Client
	conn, err := net.Dial("tcp", "127.0.0.1:14050")
	if err != nil {
		t.Fatalf("Failed to connect to TCPBridge: %v", err)
	}
	defer conn.Close()

	reader := bufio.NewReader(conn)

	// Read initial banner line
	bannerLine, err := reader.ReadString('\n')
	if err != nil {
		t.Fatalf("Failed to read banner from TCP bridge: %v", err)
	}
	if !strings.Contains(bannerLine, "LAUBURU") && !strings.Contains(bannerLine, "╔") {
		t.Errorf("Expected banner line, got: %s", bannerLine)
	}

	// Drain remaining banner lines with a short deadline
	_ = conn.SetReadDeadline(time.Now().Add(100 * time.Millisecond))
	for {
		_, err := reader.ReadString('\n')
		if err != nil {
			break
		}
	}
	_ = conn.SetReadDeadline(time.Time{})

	// 2. Test M1 Status Command over TCP
	_, err = conn.Write([]byte("status\r\n"))
	if err != nil {
		t.Fatalf("Failed to write command to TCP bridge: %v", err)
	}

	// Read response
	_ = conn.SetReadDeadline(time.Now().Add(300 * time.Millisecond))
	var m1Response strings.Builder
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			break
		}
		m1Response.WriteString(line)
		if strings.Contains(line, "Host Memory Sanctuary") {
			break
		}
	}
	// Drain remainder
	for {
		_, err := reader.ReadString('\n')
		if err != nil {
			break
		}
	}
	_ = conn.SetReadDeadline(time.Time{})

	m1Str := m1Response.String()
	if !strings.Contains(m1Str, "MESH STATUS: 8-LAYER TOPOLOGY") {
		t.Errorf("Expected MESH STATUS in response, got: %s", m1Str)
	}

	// 3. Test M4 Movesense Command over TCP
	_, err = conn.Write([]byte("bicep\r\n"))
	if err != nil {
		t.Fatalf("Failed to write bicep command: %v", err)
	}

	_ = conn.SetReadDeadline(time.Now().Add(300 * time.Millisecond))
	var m4Response strings.Builder
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			break
		}
		m4Response.WriteString(line)
		if strings.Contains(line, "Zone 2") || strings.Contains(line, "125 BPM") {
			break
		}
	}
	// Drain remainder
	for {
		_, err := reader.ReadString('\n')
		if err != nil {
			break
		}
	}
	_ = conn.SetReadDeadline(time.Time{})

	m4Str := m4Response.String()
	if !strings.Contains(m4Str, "Movesense 261030002013") || !strings.Contains(m4Str, "125 BPM") {
		t.Errorf("Expected Movesense 125 BPM in response, got: %s", m4Str)
	}

	// 4. Test Live Broadcast
	bridge.Broadcast([]byte("[TEST-BROADCAST] Movesense Heartbeat\r\n"))

	_ = conn.SetReadDeadline(time.Now().Add(300 * time.Millisecond))
	var broadcastLine string
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			break
		}
		if strings.Contains(line, "Movesense Heartbeat") {
			broadcastLine = line
			break
		}
	}
	_ = conn.SetReadDeadline(time.Time{})
	if broadcastLine == "" {
		t.Errorf("Expected broadcast line with 'Movesense Heartbeat', got empty")
	}

	// 5. Verify Metrics & Stats
	clientCount, mode, bytesPiped, packetsPiped := bridge.GetStats()
	if clientCount != 1 {
		t.Errorf("Expected 1 active client, got %d", clientCount)
	}
	if !strings.Contains(mode, "DIRECT_TCP_SERVER") {
		t.Errorf("Expected DIRECT_TCP_SERVER mode, got %s", mode)
	}
	if bytesPiped == 0 || packetsPiped == 0 {
		t.Errorf("Expected non-zero bytes/packets piped, got %d/%d", bytesPiped, packetsPiped)
	}
}
