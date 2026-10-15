package biometrics

import (
	"encoding/json"
	"log"
	"os"
	"strings"
	"sync"
	"time"

	"tinygo.org/x/bluetooth"
)

var adapter = bluetooth.DefaultAdapter
var ActiveDevice bluetooth.Device
var isConnected bool
var hrUUID = bluetooth.ServiceUUIDHeartRate

type movesenseStreamPayload struct {
	Connected          bool      `json:"connected"`
	DeviceName         string    `json:"device_name"`
	DeviceAddress      string    `json:"device_address"`
	HeartRateBPM       *float64  `json:"heart_rate_bpm"`
	BatteryPct         int       `json:"battery_pct"`
	RMSSD              *float64  `json:"rmssd_ms"`
	DFAAlpha1          *float64  `json:"dfa_alpha1"`
	RRIntervalsRecent  []float64 `json:"rr_intervals_recent"`
	Placement          string    `json:"placement"`
	PlacementConf      float64   `json:"placement_confidence_pct"`
	PlacementRationale string    `json:"placement_rationale"`
	DSPProfile         string    `json:"dsp_profile"`
	StreamMode         string    `json:"stream_mode"`
	TimestampUTC       string    `json:"timestamp_utc"`
}

func IsPixelMovesenseGattOwnerHost(hostnameOverride string, termuxPrefixOverride string) bool {
	h := strings.ToLower(strings.TrimSpace(hostnameOverride))
	if h == "" {
		if host, err := os.Hostname(); err == nil {
			h = strings.ToLower(host)
		}
	}
	tPrefix := strings.TrimSpace(termuxPrefixOverride)
	if tPrefix == "" {
		tPrefix = os.Getenv("PREFIX")
	}
	if strings.Contains(tPrefix, "com.termux") {
		return true
	}
	if strings.Contains(h, "pixel") || strings.Contains(h, "komodo") || strings.Contains(h, "caiman") || strings.Contains(h, "l6") {
		return true
	}
	return false
}

func ResolveLiveStreamPath() string {
	candidates := []string{
		"/Volumes/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/movesense_live_stream.json",
		"/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/movesense_live_stream.json",
		"/data/data/com.termux/files/usr/tmp/movesense_live_stream.json",
		os.Getenv("PREFIX") + "/tmp/movesense_live_stream.json",
		"/tmp/movesense_live_stream.json",
	}
	for _, p := range candidates {
		if p != "" && p != "/tmp/movesense_live_stream.json" {
			if _, err := os.Stat(p); err == nil {
				return p
			}
		}
	}
	// Default to monorepo canonical path or first valid writable directory
	if _, err := os.Stat("/Volumes/Lauburu-Monorepo"); err == nil {
		return "/Volumes/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/movesense_live_stream.json"
	}
	if _, err := os.Stat("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"); err == nil {
		return "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/movesense_live_stream.json"
	}
	if termuxPrefix := os.Getenv("PREFIX"); termuxPrefix != "" {
		return termuxPrefix + "/tmp/movesense_live_stream.json"
	}
	return "/tmp/movesense_live_stream.json"
}

func StartScanner(buffer *TelemetryBuffer) error {
	// 1. Always start background Mesh Stream Syncer (pulls Movesense GATT from Pixel L6 / :4005 bridge)
	go StartMeshStreamWatcher(buffer)

	// 2. Enforce strict Pixel-Only (`L6`) BLE GATT Connection Guard:
	// Movesense supports only 1 concurrent BLE peripheral GATT connection.
	// Non-Pixel nodes (Macs L1/L1b/L5/L2, Linux L3/L8) MUST NOT connect directly to Movesense BLE GATT.
	if !IsPixelMovesenseGattOwnerHost("", "") {
		log.Println("[BLE-GUARD] Direct Movesense BLE GATT connection blocked on non-Pixel host (STRICT_PIXEL_L6_EXCLUSIVE_BLE_GATT_OWNER). Pulling GATT telemetry via Pixel L6 (100.114.215.68) -> :4005 Serial Bridge.")
		return nil
	}

	// 3. On Pixel L6 only: Attempt direct Bluetooth adapter enablement
	err := adapter.Enable()
	if err != nil {
		log.Printf("[BLE] Hardware adapter unavailable on this host platform (%v). Mesh stream watcher is ACTIVE.", err)
		return nil
	}

	log.Println("[BLE] Pixel L6 Hardware adapter enabled. Scanning for Movesense (0x180D)...")

	var connectOnce sync.Once
	go func() {
		_ = adapter.Scan(func(adapter *bluetooth.Adapter, device bluetooth.ScanResult) {
			name := strings.ToLower(device.LocalName())
			isMovesense := strings.Contains(name, "movesense") ||
				strings.Contains(name, "261030002013") ||
				strings.Contains(name, "233330000722") ||
				strings.Contains(name, "suunto")

			if device.HasServiceUUID(hrUUID) || isMovesense {
				connectOnce.Do(func() {
					log.Printf("[BLE] Found Movesense/HR Device: %s (%s)", device.LocalName(), device.Address.String())
					buffer.Mu.Lock()
					buffer.DeviceName = device.LocalName()
					buffer.DeviceAddress = device.Address.String()
					buffer.Connected = true
					buffer.Mu.Unlock()
					_ = adapter.StopScan()
					go connectAndStream(device.Address, buffer)
				})
			}
		})
	}()

	return nil
}

func StartMeshStreamWatcher(buffer *TelemetryBuffer) {
	ticker := time.NewTicker(300 * time.Millisecond)
	defer ticker.Stop()

	streamPath := ResolveLiveStreamPath()
	var lastModified time.Time

	for range ticker.C {
		// Re-check path if current does not exist
		if _, err := os.Stat(streamPath); err != nil {
			streamPath = ResolveLiveStreamPath()
		}

		info, err := os.Stat(streamPath)
		if err != nil || info.ModTime().Equal(lastModified) {
			continue
		}
		lastModified = info.ModTime()

		data, err := os.ReadFile(streamPath)
		if err != nil || len(data) == 0 {
			continue
		}

		var payload movesenseStreamPayload
		if err := json.Unmarshal(data, &payload); err != nil {
			continue
		}

		var rmssdVal, dfaVal float64
		if payload.RMSSD != nil {
			rmssdVal = *payload.RMSSD
		}
		if payload.DFAAlpha1 != nil {
			dfaVal = *payload.DFAAlpha1
		}

		devName := payload.DeviceName
		if devName == "" {
			devName = "Movesense 261030002013"
		}
		devAddr := payload.DeviceAddress
		if devAddr == "" {
			devAddr = "74:92:BA:11:36:D6"
		}

		buffer.UpdateLiveMetrics(
			devName,
			devAddr,
			payload.Connected,
			payload.BatteryPct,
			rmssdVal,
			dfaVal,
			payload.Placement,
			payload.PlacementConf,
			payload.PlacementRationale,
			payload.DSPProfile,
			payload.StreamMode,
		)

		if payload.Connected && payload.HeartRateBPM != nil && *payload.HeartRateBPM > 0 {
			rris := make([]int, 0, len(payload.RRIntervalsRecent))
			for _, rr := range payload.RRIntervalsRecent {
				rris = append(rris, int(rr))
			}
			buffer.AddPoint(int(*payload.HeartRateBPM), rris)
		}
	}
}

func ResetScanner(buffer *TelemetryBuffer) {
	if isConnected {
		_ = ActiveDevice.Disconnect()
		isConnected = false
	}

	buffer.Mu.Lock()
	buffer.Connected = false
	buffer.Points = []HeartRatePoint{}
	buffer.Mu.Unlock()

	go StartScanner(buffer)
}

func connectAndStream(address bluetooth.Address, buffer *TelemetryBuffer) {
	log.Printf("[BLE] Attempting direct GATT connect to %s...", address.String())

	var err error
	ActiveDevice, err = adapter.Connect(address, bluetooth.ConnectionParams{})
	if err != nil {
		log.Printf("[BLE] Failed to connect directly: %v", err)
		return
	}
	isConnected = true
	device := ActiveDevice
	log.Printf("[BLE] Connected successfully to %s", address.String())

	services, err := device.DiscoverServices([]bluetooth.UUID{bluetooth.ServiceUUIDHeartRate})
	if err != nil || len(services) == 0 {
		return
	}

	chars, err := services[0].DiscoverCharacteristics([]bluetooth.UUID{bluetooth.CharacteristicUUIDHeartRateMeasurement})
	if err != nil || len(chars) == 0 {
		return
	}

	err = chars[0].EnableNotifications(func(buf []byte) {
		if len(buf) < 2 {
			return
		}
		flags := buf[0]
		bpm := 0
		if (flags & 0x01) == 0 {
			bpm = int(buf[1])
		} else {
			if len(buf) >= 3 {
				bpm = int(buf[1]) | (int(buf[2]) << 8)
			}
		}
		if bpm > 0 {
			buffer.AddPoint(bpm, []int{})
			buffer.Mu.Lock()
			buffer.Connected = true
			buffer.Mu.Unlock()
		}
	})

	if err != nil {
		log.Printf("[BLE] Notification error: %v", err)
	}
	select {}
}
