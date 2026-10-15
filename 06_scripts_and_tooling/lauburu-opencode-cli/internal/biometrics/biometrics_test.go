package biometrics

import (
	"testing"
	"time"
)

func TestTelemetryBufferLiveMetrics(t *testing.T) {
	tb := NewTelemetryBuffer()
	if tb.DeviceName != "Movesense 261030002013" {
		t.Fatalf("Expected default DeviceName Movesense 261030002013, got %s", tb.DeviceName)
	}
	if tb.Connected {
		t.Fatalf("Expected Connected to be false initially")
	}

	// Initial update sets bicep_strap
	tb.UpdateLiveMetrics("Movesense 261030002013", "74:92:BA:11:36:D6", true, 77, 42.5, 0.88, "bicep_strap", 92.0, "High artifact rate", "Brachial Bicep ECG", "LIVE_BLE_HARDWARE")

	// Adding clean RR points engages the real-time classifier
	tb.AddPoint(72, []int{833, 831, 835})

	snap := tb.GetSnapshot()
	if !snap.Connected {
		t.Fatalf("Expected snapshot Connected=true")
	}
	if snap.LatestBPM != 72 {
		t.Fatalf("Expected LatestBPM=72, got %d", snap.LatestBPM)
	}
	if snap.BatteryPct != 77 {
		t.Fatalf("Expected BatteryPct=77, got %d", snap.BatteryPct)
	}
	if snap.RMSSD != 42.5 {
		t.Fatalf("Expected RMSSD=42.5, got %f", snap.RMSSD)
	}
	if snap.DFAAlpha1 != 0.88 {
		t.Fatalf("Expected DFAAlpha1=0.88, got %f", snap.DFAAlpha1)
	}
	if snap.Placement == "" {
		t.Fatalf("Expected non-empty Placement, got empty string")
	}
	if snap.TotalPoints != 1 {
		t.Fatalf("Expected TotalPoints=1, got %d", snap.TotalPoints)
	}
}

func TestAnatomicPlacementClassifier(t *testing.T) {
	c := NewAnatomicPlacementClassifier()

	// Test 1: Sternal Chest Profile (Low artifact rate, smooth RSA oscillations)
	c.SetGATTLocation(1) // 1 = Chest
	var chestRes PlacementResult
	for i := 0; i < 20; i++ {
		rr := 850.0 + float64(i%5)*10.0 // Smooth RSA variation (meanDiff ~10-40ms)
		chestRes = c.Update(rr, false, 35.0)
	}
	if chestRes.Placement != "chest_strap" {
		t.Fatalf("Expected chest_strap placement for clean thoracic signal, got %s", chestRes.Placement)
	}
	if chestRes.ConfidencePct < 70.0 {
		t.Fatalf("Expected confidence >= 70%%, got %.1f%%", chestRes.ConfidencePct)
	}

	// Test 2: Bicep Profile (Elevated artifact rate from brachial muscle flexion)
	c2 := NewAnatomicPlacementClassifier()
	c2.SetGATTLocation(2) // 2 = Wrist/Arm
	var bicepRes PlacementResult
	for i := 0; i < 25; i++ {
		isRej := (i%4 == 0) // 25% rejection rate (>18% threshold)
		rr := 800.0
		if isRej {
			rr = 1250.0 // Ectopic spike
		}
		bicepRes = c2.Update(rr, isRej, 15.0)
	}
	if bicepRes.Placement != "bicep_strap" {
		t.Fatalf("Expected bicep_strap placement for elevated artifact signal, got %s", bicepRes.Placement)
	}
	if bicepRes.ConfidencePct < 65.0 {
		t.Fatalf("Expected confidence >= 65%%, got %.1f%%", bicepRes.ConfidencePct)
	}
}

func TestResolveLiveStreamPath(t *testing.T) {
	path := ResolveLiveStreamPath()
	if path == "" {
		t.Fatalf("Expected non-empty live stream path")
	}
}

func TestTelemetryBufferWindowPruning(t *testing.T) {
	tb := NewTelemetryBuffer()
	for i := 1; i <= 950; i++ {
		tb.AddPoint(i%120, nil)
	}
	pts := tb.GetLatest()
	if len(pts) > 900 {
		t.Fatalf("Expected maximum 900 points, got %d", len(pts))
	}
	if tb.LastUpdated.IsZero() {
		t.Fatalf("Expected LastUpdated to be set")
	}
	if time.Since(tb.LastUpdated) > time.Minute {
		t.Fatalf("Expected recent LastUpdated time")
	}
}

func TestPixelOnlyMovesenseGattOwnerGuard(t *testing.T) {
	// Non-Pixel nodes (Macs L1/L1b/L5/L2, Linux L3/L8) must NOT be permitted to open direct BLE GATT connections
	if IsPixelMovesenseGattOwnerHost("mac-air-4.local", "") {
		t.Fatalf("Expected mac-air-4.local (L5) to be blocked from direct Movesense BLE GATT connection")
	}
	if IsPixelMovesenseGattOwnerHost("Mac-mini.local", "") {
		t.Fatalf("Expected Mac-mini.local (L1) to be blocked from direct Movesense BLE GATT connection")
	}
	if IsPixelMovesenseGattOwnerHost("linux-head", "") {
		t.Fatalf("Expected linux-head (L3) to be blocked from direct Movesense BLE GATT connection")
	}
	// Pixel 10 Pro XL (L6 / Termux) must be permitted
	if !IsPixelMovesenseGattOwnerHost("pixel-10-pro-xl", "") {
		t.Fatalf("Expected pixel-10-pro-xl (L6) to be permitted as sole Movesense BLE GATT owner")
	}
	if !IsPixelMovesenseGattOwnerHost("localhost", "/data/data/com.termux/files/usr") {
		t.Fatalf("Expected Termux prefix on Pixel L6 to be permitted as sole Movesense BLE GATT owner")
	}
}

