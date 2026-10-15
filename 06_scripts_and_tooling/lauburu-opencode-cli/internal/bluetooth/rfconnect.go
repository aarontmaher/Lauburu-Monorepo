package bluetooth

import (
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
	"time"

	"tinygo.org/x/bluetooth"
)

// DiscoveredDevice represents a peripheral found during an RFConnect BLE scan
type DiscoveredDevice struct {
	Address   string
	LocalName string
	RSSI      int16
	HasNUS    bool
	HasHR     bool
	LastSeen  time.Time
}

// RFConnectManager governs BLE Nordic UART Service (NUS), GATT discovery, and RFCOMM terminal I/O
type RFConnectManager struct {
	mu                sync.RWMutex
	adapter           *bluetooth.Adapter
	adapterEnabled    bool
	activeDevice      *bluetooth.Device
	rxChar            *bluetooth.DeviceCharacteristic
	txChar            *bluetooth.DeviceCharacteristic
	isScanning        bool
	isConnected       bool
	connectedAddress  string
	connectedName     string
	discoveredDevices map[string]DiscoveredDevice
	onReceive         func([]byte)
	onStatusChange    func(string)
}

var (
	nusUUID, _       = bluetooth.ParseUUID(NordicUARTServiceUUID)
	nusRxUUID, _     = bluetooth.ParseUUID(NordicUARTRXCharUUID)
	nusTxUUID, _     = bluetooth.ParseUUID(NordicUARTTXCharUUID)
	hrServiceUUID    = bluetooth.ServiceUUIDHeartRate
)

// NewRFConnectManager creates a new RFConnect manager with receiving callbacks
func NewRFConnectManager(onReceive func([]byte), onStatusChange func(string)) *RFConnectManager {
	return &RFConnectManager{
		adapter:           bluetooth.DefaultAdapter,
		discoveredDevices: make(map[string]DiscoveredDevice),
		onReceive:         onReceive,
		onStatusChange:    onStatusChange,
	}
}

// EnsureAdapter attempts to enable the physical Bluetooth adapter (Darwin CoreBluetooth / Linux BlueZ)
func (rf *RFConnectManager) EnsureAdapter() error {
	rf.mu.Lock()
	defer rf.mu.Unlock()

	if rf.adapterEnabled {
		return nil
	}

	err := rf.adapter.Enable()
	if err != nil {
		return fmt.Errorf("bluetooth hardware adapter enable failed: %w", err)
	}
	rf.adapterEnabled = true
	return nil
}

// StartScan executes an asynchronous BLE scan for devices broadcasting NUS, Movesense, or HR
func (rf *RFConnectManager) StartScan(timeout time.Duration) ([]DiscoveredDevice, error) {
	if err := rf.EnsureAdapter(); err != nil {
		return nil, err
	}

	rf.mu.Lock()
	if rf.isScanning {
		rf.mu.Unlock()
		return rf.GetDiscoveredDevices(), nil
	}
	rf.isScanning = true
	rf.mu.Unlock()

	if rf.onStatusChange != nil {
		rf.onStatusChange("SCANNING")
	}

	go func() {
		defer func() {
			rf.mu.Lock()
			rf.isScanning = false
			rf.mu.Unlock()
			if rf.onStatusChange != nil {
				if rf.IsConnected() {
					rf.onStatusChange("CONNECTED")
				} else {
					rf.onStatusChange("STANDBY")
				}
			}
		}()

		scanErr := rf.adapter.Scan(func(adapter *bluetooth.Adapter, result bluetooth.ScanResult) {
			addrStr := result.Address.String()
			name := strings.TrimSpace(result.LocalName())
			rssi := result.RSSI

			hasNUS := result.HasServiceUUID(nusUUID)
			hasHR := result.HasServiceUUID(hrServiceUUID)
			lowerName := strings.ToLower(name)
			if strings.Contains(lowerName, "movesense") || strings.Contains(lowerName, "nordic") || strings.Contains(lowerName, "uart") {
				hasNUS = true
			}

			rf.mu.Lock()
			rf.discoveredDevices[addrStr] = DiscoveredDevice{
				Address:   addrStr,
				LocalName: name,
				RSSI:      rssi,
				HasNUS:    hasNUS,
				HasHR:     hasHR,
				LastSeen:  time.Now(),
			}
			rf.mu.Unlock()
		})

		if scanErr != nil {
			log.Printf("[RFCONNECT] Scan error: %v", scanErr)
		}
	}()

	time.Sleep(timeout)
	_ = rf.adapter.StopScan()

	return rf.GetDiscoveredDevices(), nil
}

// GetDiscoveredDevices returns a snapshot of all discovered peripherals
func (rf *RFConnectManager) GetDiscoveredDevices() []DiscoveredDevice {
	rf.mu.RLock()
	defer rf.mu.RUnlock()

	devices := make([]DiscoveredDevice, 0, len(rf.discoveredDevices))
	for _, dev := range rf.discoveredDevices {
		devices = append(devices, dev)
	}
	return devices
}

// IsMovesenseTarget returns true if the target string matches a Movesense sensor name, serial, or MAC/UUID
func IsMovesenseTarget(target string) bool {
	t := strings.ToLower(strings.TrimSpace(target))
	if t == "" {
		return false
	}
	movesenseMarkers := []string{
		"movesense",
		"261030002013",
		"233330000722",
		"74:92:ba:11:36:d6",
		"74-92-ba-11-36-d6",
		"0c:8c:dc:3e:23:96",
		"0c-8c-dc-3e-23-96",
		"c1db5043-8f89-88e8-46a3-bbd4ed83fc88",
	}
	for _, m := range movesenseMarkers {
		if strings.Contains(t, m) {
			return true
		}
	}
	return false
}

// IsPixelMovesenseBLEOwner returns true only when running on the Pixel 10 Pro XL (L6 / Termux)
func IsPixelMovesenseBLEOwner(hostnameOverride string, termuxPrefixOverride string) bool {
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

// Connect initiates GATT connection to device by MAC address or local name prefix
func (rf *RFConnectManager) Connect(target string) error {
	// Enforce strict Pixel-Only (`L6`) BLE GATT Connection Guard for Movesense sensors:
	if IsMovesenseTarget(target) && !IsPixelMovesenseBLEOwner("", "") {
		return fmt.Errorf(
			"direct BLE GATT connection to Movesense (%s) is blocked on non-Pixel host (STRICT_PIXEL_L6_EXCLUSIVE_BLE_GATT_OWNER); Pixel 10 Pro XL (L6 100.114.215.68) owns the sole BLE GATT link and streams telemetry into :4005 Bluetooth Serial Terminal",
			target,
		)
	}

	if err := rf.EnsureAdapter(); err != nil {
		return err
	}

	targetAddr := target
	targetName := target

	// Search discovered devices cache first
	rf.mu.RLock()
	for addr, dev := range rf.discoveredDevices {
		if strings.EqualFold(addr, target) || strings.EqualFold(dev.LocalName, target) ||
			(dev.LocalName != "" && strings.Contains(strings.ToLower(dev.LocalName), strings.ToLower(target))) {
			targetAddr = addr
			targetName = dev.LocalName
			break
		}
	}
	rf.mu.RUnlock()

	if (IsMovesenseTarget(targetAddr) || IsMovesenseTarget(targetName)) && !IsPixelMovesenseBLEOwner("", "") {
		return fmt.Errorf(
			"direct BLE GATT connection to Movesense (%s / %s) is blocked on non-Pixel host; pull GATT telemetry via :4005 Bluetooth Serial Terminal",
			targetName, targetAddr,
		)
	}

	var bleAddr bluetooth.Address
	bleAddr.Set(targetAddr)

	if rf.onStatusChange != nil {
		rf.onStatusChange("CONNECTING")
	}

	device, err := rf.adapter.Connect(bleAddr, bluetooth.ConnectionParams{})
	if err != nil {
		if rf.onStatusChange != nil {
			rf.onStatusChange("ERROR")
		}
		return fmt.Errorf("failed to connect to %s: %w", targetAddr, err)
	}

	// Discover Nordic UART Service
	services, err := device.DiscoverServices([]bluetooth.UUID{nusUUID})
	if err != nil || len(services) == 0 {
		_ = device.Disconnect()
		return fmt.Errorf("device %s does not expose Nordic UART Service (6E400001)", targetAddr)
	}

	chars, err := services[0].DiscoverCharacteristics([]bluetooth.UUID{nusRxUUID, nusTxUUID})
	if err != nil || len(chars) == 0 {
		_ = device.Disconnect()
		return fmt.Errorf("failed to discover NUS RX/TX characteristics on %s", targetAddr)
	}

	var rx, tx *bluetooth.DeviceCharacteristic
	for i := range chars {
		if chars[i].UUID() == nusRxUUID {
			rx = &chars[i]
		} else if chars[i].UUID() == nusTxUUID {
			tx = &chars[i]
		}
	}

	if rx == nil || tx == nil {
		_ = device.Disconnect()
		return fmt.Errorf("missing NUS RX or TX characteristic on %s", targetAddr)
	}

	// Subscribe to TX notifications (device -> host)
	err = tx.EnableNotifications(func(buf []byte) {
		if len(buf) > 0 && rf.onReceive != nil {
			rf.onReceive(buf)
		}
	})
	if err != nil {
		_ = device.Disconnect()
		return fmt.Errorf("failed to enable NUS TX notifications: %w", err)
	}

	rf.mu.Lock()
	rf.activeDevice = &device
	rf.rxChar = rx
	rf.txChar = tx
	rf.isConnected = true
	rf.connectedAddress = targetAddr
	rf.connectedName = targetName
	rf.mu.Unlock()

	if rf.onStatusChange != nil {
		rf.onStatusChange("CONNECTED")
	}

	return nil
}

// Disconnect gracefully disconnects from the peripheral
func (rf *RFConnectManager) Disconnect() error {
	rf.mu.Lock()
	defer rf.mu.Unlock()

	if !rf.isConnected || rf.activeDevice == nil {
		return nil
	}

	err := rf.activeDevice.Disconnect()
	rf.activeDevice = nil
	rf.rxChar = nil
	rf.txChar = nil
	rf.isConnected = false
	rf.connectedAddress = ""
	rf.connectedName = ""

	if rf.onStatusChange != nil {
		rf.onStatusChange("DISCONNECTED")
	}
	return err
}

// WriteUART transmits data in MTU-sized chunks over BLE NUS
func (rf *RFConnectManager) WriteUART(data []byte) (int, error) {
	rf.mu.RLock()
	defer rf.mu.RUnlock()

	if !rf.isConnected || rf.rxChar == nil {
		return 0, fmt.Errorf("not connected to BLE NUS peripheral")
	}

	chunks := ChunkBLEPayload(data, DefaultBLEPayloadMTU)
	totalSent := 0

	for _, chunk := range chunks {
		n, err := rf.rxChar.Write(chunk)
		if err != nil {
			return totalSent, err
		}
		totalSent += n
	}

	return totalSent, nil
}

// IsConnected returns whether an active BLE NUS session is established
func (rf *RFConnectManager) IsConnected() bool {
	rf.mu.RLock()
	defer rf.mu.RUnlock()
	return rf.isConnected
}

// GetConnectionInfo returns connection metadata
func (rf *RFConnectManager) GetConnectionInfo() (string, string, bool) {
	rf.mu.RLock()
	defer rf.mu.RUnlock()
	return rf.connectedName, rf.connectedAddress, rf.isConnected
}

// FormatDiscoveredDevices returns a clean ASCII table of discovered peripherals
func (rf *RFConnectManager) FormatDiscoveredDevices() string {
	devices := rf.GetDiscoveredDevices()
	if len(devices) == 0 {
		return "\033[33m[RFCONNECT SCAN]\033[0m No BLE peripherals discovered. Tip: bridge sensor contacts or bring device into range."
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("\033[1;32m[RFCONNECT SCAN RESULTS: %d PERIPHERAL(S) FOUND]\033[0m\r\n", len(devices)))
	sb.WriteString("┌──────────────────────────┬────────────────────────────────┬──────┬─────────┬─────────┐\r\n")
	sb.WriteString("│ Device Name              │ MAC / UUID Address             │ RSSI │ BLE NUS │ HeartRt │\r\n")
	sb.WriteString("├──────────────────────────┼────────────────────────────────┼──────┼─────────┼─────────┤\r\n")

	for _, d := range devices {
		name := d.LocalName
		if name == "" {
			name = "(Unknown)"
		}
		if len(name) > 24 {
			name = name[:21] + "..."
		}

		nusStr := " No "
		if d.HasNUS {
			nusStr = "\033[32m YES\033[0m"
		}
		hrStr := " No "
		if d.HasHR {
			hrStr = "\033[32m YES\033[0m"
		}

		sb.WriteString(fmt.Sprintf("│ %-24s │ %-30s │ %4d │ %-7s │ %-7s │\r\n",
			name, d.Address, d.RSSI, nusStr, hrStr))
	}
	sb.WriteString("└──────────────────────────┴────────────────────────────────┴──────┴─────────┴─────────┘\r\n")
	sb.WriteString("\033[90mTip: Type 'connect <MAC>' or 'connect <Name>' to establish full-duplex NUS session.\033[0m")

	return sb.String()
}

// CheckSerialPortFallback checks if local Darwin or Linux RFCOMM/PTY devices exist
func CheckSerialPortFallback() string {
	candidates := []string{
		PTYSymlinkPath,
		SerialPortDarwin,
		SerialPortDarwinAlt,
		"/dev/rfcomm0",
		"/dev/ttyUSB0",
	}

	for _, p := range candidates {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	return ""
}
