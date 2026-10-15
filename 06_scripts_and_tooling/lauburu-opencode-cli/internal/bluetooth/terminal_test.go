package bluetooth

import (
	"os"
	"strings"
	"sync"
	"testing"

	"github.com/aarontmaher/lauburu-opencode/internal/biometrics"
)

func TestFormatAntiStaircasing(t *testing.T) {
	cases := []struct {
		input    string
		expected string
	}{
		{"hello\nworld", "hello\r\nworld"},
		{"line1\r\nline2", "line1\r\nline2"}, // Already CRLF, should not double \r
		{"single line", "single line"},
		{"\nstart and end\n", "\r\nstart and end\r\n"},
		{"multi\nline\r\ntest\n", "multi\r\nline\r\ntest\r\n"},
	}

	for _, c := range cases {
		actual := FormatAntiStaircasing(c.input)
		if actual != c.expected {
			t.Errorf("FormatAntiStaircasing(%q) = %q; want %q", c.input, actual, c.expected)
		}
	}
}

func TestExecuteMacro(t *testing.T) {
	bt := NewBluetoothTerminal(nil)

	macros := []string{"status", "telemetry", "ram", "bicep", "reconnect", "clear", "voice test directive", "help"}

	for _, m := range macros {
		resp, ok := bt.ExecuteMacro(m)
		if !ok {
			t.Errorf("Expected macro %q to be recognized, but got ok=false", m)
		}
		if len(resp) == 0 {
			t.Errorf("Expected non-empty response for macro %q", m)
		}
	}

	// Non-macro test
	_, ok := bt.ExecuteMacro("random query for llm")
	if ok {
		t.Errorf("Expected 'random query' to NOT be recognized as macro")
	}
}

func TestWriteCommandAndHistoryBounds(t *testing.T) {
	bt := NewBluetoothTerminal(nil)
	_ = bt.Start()
	defer bt.Stop()

	// Write 150 commands to test ring buffer bounding (MaxHistoryLines = 120)
	for i := 0; i < 150; i++ {
		bt.WriteCommand("status")
	}

	lines := bt.GetLines()
	if len(lines) > MaxHistoryLines {
		t.Errorf("Expected history lines <= %d, got %d", MaxHistoryLines, len(lines))
	}

	stats := bt.GetStats()
	if stats.PacketsSent != 150 {
		t.Errorf("Expected 150 packets sent, got %d", stats.PacketsSent)
	}
	if stats.BytesSent == 0 {
		t.Errorf("Expected positive bytes sent")
	}
}

func TestConcurrentWriters(t *testing.T) {
	bt := NewBluetoothTerminal(nil)
	_ = bt.Start()
	defer bt.Stop()

	var wg sync.WaitGroup
	workers := 10
	iterations := 20

	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			for j := 0; j < iterations; j++ {
				bt.WriteCommand("telemetry")
				_ = bt.GetStats()
				_ = bt.GetLines()
			}
		}(i)
	}

	wg.Wait()
	stats := bt.GetStats()
	expectedPackets := uint64(workers * iterations)
	if stats.PacketsSent != expectedPackets {
		t.Errorf("Expected %d packets sent, got %d", expectedPackets, stats.PacketsSent)
	}
}

func TestStreamPipeCreation(t *testing.T) {
	bt := NewBluetoothTerminal(nil)
	_ = bt.Start()
	defer bt.Stop()

	pipePath := ResolveStreamPipePath()
	if _, err := os.Stat(pipePath); os.IsNotExist(err) {
		t.Fatalf("Stream pipe file does not exist at %s", pipePath)
	}

	bt.WriteCommand("status")

	// Verify stream pipe exists and contains data
	data, err := os.ReadFile(pipePath)
	if err != nil {
		t.Fatalf("Failed to read stream pipe: %v", err)
	}
	if len(data) == 0 {
		t.Errorf("Stream pipe is empty")
	}
	if !strings.Contains(string(data), "MESH STATUS") {
		t.Errorf("Expected stream pipe to contain 'MESH STATUS'")
	}
}

func TestChunkBLEPayload(t *testing.T) {
	// Test payload chunking for 20-byte MTU limit
	data := []byte("12345678901234567890ABCDE") // 25 bytes
	chunks := ChunkBLEPayload(data, 20)

	if len(chunks) != 2 {
		t.Fatalf("Expected 2 chunks, got %d", len(chunks))
	}
	if len(chunks[0]) != 20 {
		t.Errorf("Expected first chunk 20 bytes, got %d", len(chunks[0]))
	}
	if len(chunks[1]) != 5 {
		t.Errorf("Expected second chunk 5 bytes, got %d", len(chunks[1]))
	}

	// Empty payload
	if chunksEmpty := ChunkBLEPayload(nil, 20); chunksEmpty != nil {
		t.Errorf("Expected nil chunks for empty data")
	}
}

func TestMacroM9MTU(t *testing.T) {
	bt := NewBluetoothTerminal(nil)
	resp, ok := bt.ExecuteMacro("mtu")
	if !ok {
		t.Fatalf("Expected macro 'mtu' to be recognized")
	}
	if !strings.Contains(resp, "BLE NUS MTU & TRANSPORT GOVERNANCE") {
		t.Errorf("Expected MTU banner, got: %s", resp)
	}
	if !strings.Contains(resp, "Default Payload MTU: 20 Bytes") {
		t.Errorf("Expected 20 Bytes MTU mention, got: %s", resp)
	}
}

func TestMacroM4MovesenseLiveAndStandby(t *testing.T) {
	bt := NewBluetoothTerminal(nil)
	tb := biometrics.NewTelemetryBuffer()
	bt.SetTelemetryBuffer(tb)

	// 1. Standby test
	respStandby, ok := bt.ExecuteMacro("bicep")
	if !ok || !strings.Contains(respStandby, "STANDBY") {
		t.Fatalf("Expected STANDBY response when buffer is empty, got: %s", respStandby)
	}

	// 2. Connected live test
	tb.UpdateLiveMetrics("Movesense 261030002013", "74:92:BA:11:36:D6", true, 77, 42.5, 0.88, "bicep_strap", 91.0, "Brachial muscle EMG detected", "Brachial Bicep ECG", "LIVE_BLE_HARDWARE")
	tb.AddPoint(74, []int{810, 812})

	respLive, ok := bt.ExecuteMacro("bicep")
	if !ok || !strings.Contains(respLive, "CONNECTED") || !strings.Contains(respLive, "74 BPM") {
		t.Fatalf("Expected CONNECTED with 74 BPM, got: %s", respLive)
	}
}

func TestMacroM10ScanAndRFConnect(t *testing.T) {
	bt := NewBluetoothTerminal(nil)
	resp, ok := bt.ExecuteMacro("scan")
	if !ok {
		t.Fatalf("Expected macro 'scan' to be recognized")
	}
	if !strings.Contains(resp, "RFCONNECT") {
		t.Errorf("Expected scan response to mention RFCONNECT, got: %s", resp)
	}

	resp0, ok0 := bt.ExecuteMacro("0")
	if !ok0 || !strings.Contains(resp0, "RFCONNECT") {
		t.Fatalf("Expected macro '0' to trigger RFConnect scan")
	}

	respDevs, okDevs := bt.ExecuteMacro("devices")
	if !okDevs {
		t.Fatalf("Expected 'devices' macro to be recognized")
	}
	if len(respDevs) == 0 {
		t.Errorf("Expected non-empty devices response")
	}
}

func TestRFConnectConnectUsageAndDisconnect(t *testing.T) {
	bt := NewBluetoothTerminal(nil)

	// Usage message when no address is provided
	resp, ok := bt.ExecuteMacro("connect")
	if !ok || !strings.Contains(resp, "USAGE") {
		t.Fatalf("Expected connect usage message, got: %s", resp)
	}

	// Disconnect when not connected
	respDisc, okDisc := bt.ExecuteMacro("disconnect")
	if !okDisc || !strings.Contains(respDisc, "DISCONNECTED") {
		t.Fatalf("Expected disconnect response, got: %s", respDisc)
	}
}

func TestRFConnectManagerDiscoveredDevicesFormatting(t *testing.T) {
	rf := NewRFConnectManager(nil, nil)
	// Add mock discovered devices to test table formatting
	rf.discoveredDevices["74:92:BA:11:36:D6"] = DiscoveredDevice{
		Address:   "74:92:BA:11:36:D6",
		LocalName: "Movesense 261030002013",
		RSSI:      -58,
		HasNUS:    true,
		HasHR:     true,
	}

	table := rf.FormatDiscoveredDevices()
	if !strings.Contains(table, "Movesense 261030002013") {
		t.Errorf("Expected formatted table to contain device name, got: %s", table)
	}
	if !strings.Contains(table, "74:92:BA:11:36:D6") {
		t.Errorf("Expected formatted table to contain MAC address, got: %s", table)
	}
	if !strings.Contains(table, "YES") {
		t.Errorf("Expected formatted table to show YES for NUS")
	}
}

func TestCheckSerialPortFallback(t *testing.T) {
	// Should return a string (empty or path) without panicking
	port := CheckSerialPortFallback()
	_ = port
}

func TestRFConnectPixelOnlyMovesenseBLEGuard(t *testing.T) {
	if !IsMovesenseTarget("Movesense 261030002013") || !IsMovesenseTarget("74:92:BA:11:36:D6") || !IsMovesenseTarget("0C:8C:DC:3E:23:96") {
		t.Fatalf("Expected Movesense names and MACs to be recognized by IsMovesenseTarget")
	}
	if IsMovesenseTarget("SomeOtherDevice") {
		t.Fatalf("Expected non-Movesense device not to match IsMovesenseTarget")
	}
	if IsPixelMovesenseBLEOwner("mac-air-4.local", "") {
		t.Fatalf("Expected mac-air-4.local (L5) to be blocked by IsPixelMovesenseBLEOwner")
	}
	if !IsPixelMovesenseBLEOwner("pixel-10-pro-xl", "/data/data/com.termux/files/usr") {
		t.Fatalf("Expected Pixel 10 Pro XL (L6) to be permitted by IsPixelMovesenseBLEOwner")
	}

	// Verify Connect() on non-Pixel host immediately blocks direct BLE GATT connection to Movesense
	if !IsPixelMovesenseBLEOwner("", "") {
		rf := NewRFConnectManager(nil, nil)
		err := rf.Connect("74:92:BA:11:36:D6")
		if err == nil || !strings.Contains(err.Error(), "STRICT_PIXEL_L6_EXCLUSIVE_BLE_GATT_OWNER") {
			t.Fatalf("Expected Connect(74:92:BA:11:36:D6) to be blocked by Pixel-only guard, got: %v", err)
		}
	}
}


