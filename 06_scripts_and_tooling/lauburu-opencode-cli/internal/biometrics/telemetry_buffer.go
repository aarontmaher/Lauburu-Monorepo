package biometrics

import (
	"sync"
	"time"
)

type HeartRatePoint struct {
	Timestamp time.Time
	BPM       int
	RR        []int
}

type TelemetryBuffer struct {
	Mu                  sync.RWMutex
	DeviceName          string
	DeviceAddress       string
	Connected           bool
	BatteryPct          int
	RMSSD               float64
	DFAAlpha1           float64
	Placement           string
	PlacementConfidence float64
	PlacementRationale  string
	DSPProfile          string
	GATTLocation        string
	StreamMode          string
	LastUpdated         time.Time
	Points              []HeartRatePoint
	Classifier          *AnatomicPlacementClassifier
}

func NewTelemetryBuffer() *TelemetryBuffer {
	return &TelemetryBuffer{
		DeviceName:          "Movesense 261030002013",
		DeviceAddress:       "74:92:BA:11:36:D6",
		Placement:           "chest_strap",
		PlacementConfidence: 85.0,
		PlacementRationale:  "Awaiting initial biometric waveform...",
		DSPProfile:          "Thoracic Sternal ECG (Lead II Vector)",
		GATTLocation:        "Unknown",
		StreamMode:          "STANDBY",
		Points:              make([]HeartRatePoint, 0),
		Classifier:          NewAnatomicPlacementClassifier(),
	}
}

func (tb *TelemetryBuffer) AddPoint(bpm int, rr []int) {
	tb.Mu.Lock()
	defer tb.Mu.Unlock()

	tb.Points = append(tb.Points, HeartRatePoint{
		Timestamp: time.Now(),
		BPM:       bpm,
		RR:        rr,
	})
	tb.LastUpdated = time.Now()

	// Update classifier dynamically if RR intervals are present
	if len(rr) > 0 && tb.Classifier != nil {
		for _, rVal := range rr {
			res := tb.Classifier.Update(float64(rVal), false, tb.RMSSD)
			tb.Placement = res.Placement
			tb.PlacementConfidence = res.ConfidencePct
			tb.PlacementRationale = res.Rationale
			tb.DSPProfile = res.DSPProfile
			tb.GATTLocation = res.GATTLocation
		}
	}

	// Maintain 15 minute window max points
	if len(tb.Points) > 900 {
		tb.Points = tb.Points[1:]
	}
}

func (tb *TelemetryBuffer) UpdateLiveMetrics(
	deviceName, address string,
	connected bool,
	battery int,
	rmssd, dfa float64,
	placement string,
	placementConf float64,
	placementRationale string,
	dspProfile string,
	streamMode string,
) {
	tb.Mu.Lock()
	defer tb.Mu.Unlock()

	if deviceName != "" {
		tb.DeviceName = deviceName
	}
	if address != "" {
		tb.DeviceAddress = address
	}
	tb.Connected = connected
	if battery > 0 {
		tb.BatteryPct = battery
	}
	if rmssd > 0 {
		tb.RMSSD = rmssd
	}
	if dfa > 0 {
		tb.DFAAlpha1 = dfa
	}
	if placement != "" {
		tb.Placement = placement
	}
	if placementConf > 0 {
		tb.PlacementConfidence = placementConf
	}
	if placementRationale != "" {
		tb.PlacementRationale = placementRationale
	}
	if dspProfile != "" {
		tb.DSPProfile = dspProfile
	}
	if streamMode != "" {
		tb.StreamMode = streamMode
	}
	tb.LastUpdated = time.Now()
}

func (tb *TelemetryBuffer) GetLatest() []HeartRatePoint {
	tb.Mu.RLock()
	defer tb.Mu.RUnlock()
	return tb.Points
}

type TelemetrySnapshot struct {
	DeviceName          string
	DeviceAddress       string
	Connected           bool
	BatteryPct          int
	LatestBPM           int
	RMSSD               float64
	DFAAlpha1           float64
	Placement           string
	PlacementConfidence float64
	PlacementRationale  string
	DSPProfile          string
	GATTLocation        string
	StreamMode          string
	LastUpdated         time.Time
	TotalPoints         int
}

func (tb *TelemetryBuffer) GetSnapshot() TelemetrySnapshot {
	tb.Mu.RLock()
	defer tb.Mu.RUnlock()

	latestBPM := 0
	if len(tb.Points) > 0 {
		latestBPM = tb.Points[len(tb.Points)-1].BPM
	}

	return TelemetrySnapshot{
		DeviceName:          tb.DeviceName,
		DeviceAddress:       tb.DeviceAddress,
		Connected:           tb.Connected,
		BatteryPct:          tb.BatteryPct,
		LatestBPM:           latestBPM,
		RMSSD:               tb.RMSSD,
		DFAAlpha1:           tb.DFAAlpha1,
		Placement:           tb.Placement,
		PlacementConfidence: tb.PlacementConfidence,
		PlacementRationale:  tb.PlacementRationale,
		DSPProfile:          tb.DSPProfile,
		GATTLocation:        tb.GATTLocation,
		StreamMode:          tb.StreamMode,
		LastUpdated:         tb.LastUpdated,
		TotalPoints:         len(tb.Points),
	}
}
