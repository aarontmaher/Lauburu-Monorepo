package biometrics

import (
	"fmt"
	"math"
	"strings"
	"sync"
)

// PlacementResult holds the dynamic classification verdict
type PlacementResult struct {
	Placement     string  // "chest_strap" or "bicep_strap"
	ConfidencePct float64 // 60.0% - 99.0%
	Rationale     string
	RejectionRate float64
	GATTLocation  string
	DSPProfile    string
}

// AnatomicPlacementClassifier distinguishes between chest and bicep placement
// based on GATT 0x2A38, Kamath 20% artifact rejection, and Respiratory Sinus Arrhythmia (RSA).
type AnatomicPlacementClassifier struct {
	mu               sync.RWMutex
	gattLocationCode int // -1 if unknown, 1 = Chest, 2 = Wrist/Arm
	gattLocationStr  string
	rrWindow         []float64
	rejectionHistory []int
	placement        string
	confidencePct    float64
	rationale        string
	dspProfile       string
}

// NewAnatomicPlacementClassifier initializes the classifier
func NewAnatomicPlacementClassifier() *AnatomicPlacementClassifier {
	return &AnatomicPlacementClassifier{
		gattLocationCode: -1,
		gattLocationStr:  "Unknown",
		rrWindow:         make([]float64, 0, 30),
		rejectionHistory: make([]int, 0, 50),
		placement:        "chest_strap",
		confidencePct:    85.0,
		rationale:        "Evaluating initial biometric waveform...",
		dspProfile:       "Dual Sternal/Brachial Auto-Classifier Standby",
	}
}

// SetGATTLocation sets the location from GATT Characteristic 0x2A38
func (c *AnatomicPlacementClassifier) SetGATTLocation(code int) {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.gattLocationCode = code
	mapping := map[int]string{
		0: "Other",
		1: "Chest",
		2: "Wrist/Arm",
		3: "Finger",
		4: "Hand",
		5: "Ear Lobe",
		6: "Foot",
	}
	if str, ok := mapping[code]; ok {
		c.gattLocationStr = str
	} else {
		c.gattLocationStr = fmt.Sprintf("Code_%d", code)
	}
}

// Update evaluates a newly received RR interval and returns the dynamic placement verdict
func (c *AnatomicPlacementClassifier) Update(latestRR float64, isRejected bool, rmssd float64) PlacementResult {
	c.mu.Lock()
	defer c.mu.Unlock()

	// 1. Maintain bounded rejection history (last 40 beats)
	rejVal := 0
	if isRejected {
		rejVal = 1
	}
	c.rejectionHistory = append(c.rejectionHistory, rejVal)
	if len(c.rejectionHistory) > 40 {
		c.rejectionHistory = c.rejectionHistory[1:]
	}

	// 2. Maintain bounded clean RR window (last 25 clean beats)
	if !isRejected && latestRR > 0 {
		c.rrWindow = append(c.rrWindow, latestRR)
		if len(c.rrWindow) > 25 {
			c.rrWindow = c.rrWindow[1:]
		}
	}

	// Calculate artifact rejection rate
	rejCount := 0
	for _, v := range c.rejectionHistory {
		rejCount += v
	}
	rejectionRate := float64(rejCount) / math.Max(1.0, float64(len(c.rejectionHistory)))

	// 3. Check for Respiratory Sinus Arrhythmia (smooth thoracic oscillations)
	rsaScore := 0.0
	if len(c.rrWindow) >= 6 {
		diffs := make([]float64, 0, len(c.rrWindow)-1)
		var sumDiff float64
		for i := 1; i < len(c.rrWindow); i++ {
			d := math.Abs(c.rrWindow[i] - c.rrWindow[i-1])
			diffs = append(diffs, d)
			sumDiff += d
		}
		meanDiff := sumDiff / float64(len(diffs))

		var varSum float64
		for _, d := range diffs {
			varSum += (d - meanDiff) * (d - meanDiff)
		}
		stdDiff := math.Sqrt(varSum / float64(len(diffs)))

		if meanDiff >= 15.0 && meanDiff <= 85.0 && stdDiff < 45.0 {
			rsaScore = 1.2
		} else if meanDiff > 110.0 || stdDiff >= 45.0 {
			rsaScore = -1.5
		}
	}

	// 4. Weighted scoring matrix
	score := 0.0
	var reasons []string

	if c.gattLocationCode == 1 {
		score += 1.2
		reasons = append(reasons, "GATT 0x2A38 declares Chest")
	} else if c.gattLocationCode == 0 || c.gattLocationCode == 2 {
		score -= 1.0
		reasons = append(reasons, "GATT 0x2A38 declares Arm/Peripheral")
	}

	if rejectionRate < 0.08 {
		score += 1.8
		reasons = append(reasons, fmt.Sprintf("Low artifact rate (%.1f%%), strong sternal SNR", rejectionRate*100))
	} else if rejectionRate > 0.18 {
		score -= 2.2
		reasons = append(reasons, fmt.Sprintf("Elevated artifact rate (%.1f%%), bicep EMG spikes", rejectionRate*100))
	}

	if rsaScore > 0 {
		score += 1.5
		reasons = append(reasons, "Thoracic respiratory sinus arrhythmia active")
	} else if rsaScore < 0 {
		score -= 1.5
		reasons = append(reasons, "Erratic beat-to-beat delta characteristic of brachial arm flexion")
	}

	// 5. Final Decision
	if score >= 0.0 {
		c.placement = "chest_strap"
		c.confidencePct = math.Min(99.0, math.Max(60.0, 50.0+score*14.0))
		c.dspProfile = "Thoracic Sternal ECG (Lead II Vector)"
	} else {
		c.placement = "bicep_strap"
		c.confidencePct = math.Min(99.0, math.Max(60.0, 50.0-score*14.0))
		c.dspProfile = "Brachial Bicep ECG (Kamath 20% Vector Correction)"
	}

	if len(reasons) > 0 {
		c.rationale = strings.Join(reasons, "; ")
	} else {
		c.rationale = "Evaluating initial RR intervals..."
	}

	return PlacementResult{
		Placement:     c.placement,
		ConfidencePct: math.Round(c.confidencePct*10) / 10,
		Rationale:     c.rationale,
		RejectionRate: math.Round(rejectionRate*1000) / 1000,
		GATTLocation:  c.gattLocationStr,
		DSPProfile:    c.dspProfile,
	}
}
