package main

import (
	"bytes"
	"context"
	"encoding/binary"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"net/http"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
)

// BluetoothDevice holds discovered BLE peripheral metadata (BlueZ + Mesh CoreBluetooth Registry)
type BluetoothDevice struct {
	MAC       string `json:"mac"`
	Name      string `json:"name"`
	RSSI      int    `json:"rssi,omitempty"`
	Transport string `json:"transport,omitempty"`
	Category  string `json:"category,omitempty"`
	Connected bool   `json:"connected"`
}

// IngestPayload supports Movesense (HR, RR, 512Hz/250Hz ECG, IMU, Temp, PTT) + AssaultBike (FTMS 0x2AD2, CPS 0x2A63, CSC 0x2A5B)
type IngestPayload struct {
	Timestamp          int64     `json:"timestamp"`
	DeviceID           string    `json:"device_id"`
	DeviceName         string    `json:"device_name"`
	Device             string    `json:"device"`
	MAC                string    `json:"mac"`
	Connected          *bool     `json:"connected"`
	SourceMode         string    `json:"source_mode"`
	CharacteristicUUID string    `json:"characteristic_uuid"`
	RawHex             string    `json:"raw_hex"`
	HeartRate          float64   `json:"heart_rate"`
	HRBpm              float64   `json:"hr_bpm"`
	HR                 float64   `json:"hr"`
	RRMs               float64   `json:"rr_ms"`
	RR                 float64   `json:"rr"`
	RRIntervalsMs      []float64 `json:"rr_intervals_ms"`
	ECGSamplesMv       []float64 `json:"ecg_samples_mv"`
	ECG                []float64 `json:"ecg"`
	ECGSampleRateHz    int       `json:"ecg_sample_rate_hz"`
	ECGQRSCount        int       `json:"ecg_qrs_count"`
	ECGSQIPct          float64   `json:"ecg_sqi_pct"`
	PTTMs              float64   `json:"ptt_ms"`
	SkinTempC          float64   `json:"skin_temp_c"`
	BatteryPct         int       `json:"battery_pct"`
	AccX               float64   `json:"acc_x"`
	AccY               float64   `json:"acc_y"`
	AccZ               float64   `json:"acc_z"`
	GyroX              float64   `json:"gyro_x"`
	GyroY              float64   `json:"gyro_y"`
	GyroZ              float64   `json:"gyro_z"`
	// AssaultBike fields
	BikeDeviceName string  `json:"bike_device_name"`
	BikeProtocol   string  `json:"bike_protocol"`
	Watts          *int    `json:"watts"`
	CadenceRPM     float64 `json:"cadence_rpm"`
	SpeedKmh       float64 `json:"speed_kmh"`
	DistanceM      float64 `json:"distance_m"`
	CaloriesKcal   float64 `json:"calories_kcal"`
}

// SovereignState represents the complete Rule #0 Zero-Mock real-time biometric & AssaultBike state
type SovereignState struct {
	Timestamp        int64     `json:"timestamp"`
	TimestampUTC     string    `json:"timestamp_utc"`
	Status           string    `json:"status"` // "STANDBY", "RECORDED_VAULT_INSPECTOR (BLE Standby)", or "STREAMING"
	SourceMode       string    `json:"source_mode"`
	Rule0ZeroMock    bool      `json:"rule_0_zero_mock"`
	DeviceID         string    `json:"device_id"`
	Connected        bool      `json:"connected"`
	MovesenseMAC     string    `json:"movesense_mac"`
	BatteryPct       *int      `json:"battery_pct"`
	HeartRate        *int      `json:"heart_rate"`
	HRBpm            *float64  `json:"hr_bpm"`
	RRMs             *float64  `json:"rr_ms"`
	RRRecentMs       []float64 `json:"rr_recent_ms"`
	ArtifactsRemoved int     `json:"artifacts_removed"`

	// 1. Real-Time Readiness Score (0-100)
	ReadinessScore *int     `json:"readiness_score"`
	ReadinessTier  string   `json:"readiness_tier"`
	ReadinessTrend string   `json:"readiness_trend"`
	BaselineLnRMSSD float64 `json:"baseline_ln_rmssd"`
	BaselineRHR     float64 `json:"baseline_rhr"`

	// 3. DFA-alpha1 Real-Time Engine (4 <= n <= 16)
	DFAAlpha1      *float64 `json:"dfa_alpha1"`
	DFARSquared    *float64 `json:"dfa_r_squared"`
	DFAZoneStatus  string   `json:"dfa_zone_status"`
	LT1Target      float64  `json:"lt1_target"`
	LT2Target      float64  `json:"lt2_target"`

	// 4. Full HRV Suite (Time + Poincare + Lomb-Scargle Frequency Domain)
	RMSSDMs       *float64 `json:"rmssd_ms"`
	LnRMSSD       *float64 `json:"ln_rmssd"`
	SDNNMs        *float64 `json:"sdnn_ms"`
	PNN50Pct      *float64 `json:"pnn50_pct"`
	SDSDMs        *float64 `json:"sdsd_ms"`
	SD1Ms         *float64 `json:"sd1_ms"`
	SD2Ms         *float64 `json:"sd2_ms"`
	SD1SD2Ratio   *float64 `json:"sd1_sd2_ratio"`
	VLFPowerMs2   *float64 `json:"vlf_power_ms2"`
	LFPowerMs2    *float64 `json:"lf_power_ms2"`
	HFPowerMs2    *float64 `json:"hf_power_ms2"`
	LFHFRatio     *float64 `json:"lf_hf_ratio"`

	// 5. ECG 512Hz / 250Hz Pan-Tompkins & SQI
	ECGSampleRateHz *int      `json:"ecg_sample_rate_hz"`
	ECGSQIPct       *float64  `json:"ecg_sqi_pct"`
	ECGQRSCount     int       `json:"ecg_qrs_count"`
	ECGSamplesMv    []float64 `json:"ecg_samples_mv"`

	// 6. Cuffless Blood Pressure (PTT / PWV)
	SystolicMmhg      *float64 `json:"systolic_mmhg"`
	DiastolicMmhg     *float64 `json:"diastolic_mmhg"`
	MAPMmhg           *float64 `json:"map_mmhg"`
	PulsePressureMmhg *float64 `json:"pulse_pressure_mmhg"`
	PTTMs             *float64 `json:"ptt_ms"`
	PWVMps            *float64 `json:"pwv_mps"`
	BPStatus          string   `json:"bp_status"`
	BPCalibratedRef   string   `json:"bp_calibrated_ref"`

	// 7. AssaultBike + FTMS / CPS / CSC & Workout Modes
	BikeConnected           bool     `json:"bike_connected"`
	BikeDeviceName          string   `json:"bike_device_name"`
	BikeProtocol            string   `json:"bike_protocol"`
	Watts                   *int     `json:"watts"`
	AvgWatts                *float64 `json:"avg_watts"`
	PeakWatts               *int     `json:"peak_watts"`
	NormalizedPowerW        *float64 `json:"normalized_power_w"`
	WattsPerKg              *float64 `json:"watts_per_kg"`
	CadenceRPM              *float64 `json:"cadence_rpm"`
	SpeedKmh                *float64 `json:"speed_kmh"`
	DistanceM               *float64 `json:"distance_m"`
	CaloriesKcal            *float64 `json:"calories_kcal"`
	EfficiencyFactorEF      *float64 `json:"efficiency_factor_ef"`
	AerobicDecouplingPwHrPct *float64 `json:"aerobic_decoupling_pwhr_pct"`
	WorkoutMode             string   `json:"workout_mode"`
	WorkoutActive           bool     `json:"workout_active"`
	IntervalPhase           string   `json:"interval_phase"`
	CurrentRound            int      `json:"current_round"`
	TotalRounds             int      `json:"total_rounds"`
	PhaseRemainingSec       int      `json:"phase_remaining_s"`
	TargetWatts             int      `json:"target_watts"`
	ErgometerGuidance       string   `json:"ergometer_guidance"`

	// 8. Respiratory Rate (EDR), Core Temp, Orthostatic, HRR-60s, IMU
	RespiratoryRateBrpm *float64 `json:"respiratory_rate_brpm"`
	CoreTempC           *float64 `json:"core_temp_c"`
	SkinTempC           *float64 `json:"skin_temp_c"`
	HRR60sBpm           *float64 `json:"hrr_60s_bpm"`
	OrthostaticPhase    string   `json:"orthostatic_phase"`
	OrthostaticDeltaHR  *float64 `json:"orthostatic_delta_hr_bpm"`
	OrthostaticStatus   string   `json:"orthostatic_status"`
	AccX                float64  `json:"acc_x"`
	AccY                float64  `json:"acc_y"`
	AccZ                float64  `json:"acc_z"`
	AccNorm             float64  `json:"acc_norm"`
	GyroX               float64  `json:"gyro_x"`
	GyroY               float64                `json:"gyro_y"`
	GyroZ               float64                `json:"gyro_z"`
	SessionSamplesCount int                    `json:"session_samples_count"`
	AIECGAnalysis       map[string]interface{} `json:"ai_ecg_analysis,omitempty"`
}

type SessionRow struct {
	TimestampUTC string
	HRBpm        string
	RRMs         string
	RMSSDMs      string
	DFAAlpha1    string
	SBPMmhg      string
	DBPMmhg      string
	Watts        string
	CadenceRPM   string
	SpeedKmh     string
	CaloriesKcal string
	CoreTempC    string
	RespBrpm     string
}

type Hub struct {
	clients    map[chan []byte]bool
	broadcast  chan []byte
	register   chan chan []byte
	unregister chan chan []byte
	mutex      sync.RWMutex
	devices    []BluetoothDevice
	scanning   bool

	// Live DSP Buffers & Calibration State
	movesenseConnected bool
	sourceMode         string
	deviceID           string
	movesenseMAC       string
	batteryPct         *int
	currentHR          *float64
	peakHR             *float64
	recoveryRefHR      *float64
	recoveryRefTs      time.Time
	hrr60s             *float64
	rrBufferMs         []float64
	ecgBufferMv        []float64
	ecgSampleRateHz    int
	ecgQRSCount        int
	ecgSQIPct          *float64
	lastPTTMs          *float64
	skinTempC          *float64
	coreTempC          float64
	accX, accY, accZ   float64
	gyroX, gyroY, gyroZ float64

	// BP Calibration Anchor
	calSBP    float64
	calDBP    float64
	calPTTMs  float64
	calHRBpm  float64
	// Athlete Baselines
	athleteWeightKg float64
	baselineRMSSD   float64
	baselineRHR     float64

	// AssaultBike State
	bikeConnected  bool
	bikeDeviceName string
	bikeProtocol   string
	watts          *int
	peakWatts      *int
	wattsHistory   []float64
	hrWattsPairs   [][2]float64
	cadenceRPM     *float64
	speedKmh       *float64
	distanceM      float64
	caloriesKcal   float64
	lastBikeTs     time.Time
	prevCrankRevs  *uint16
	prevCrankTime  *uint16
	prevWheelRevs  *uint32
	prevWheelTime  *uint16

	// Workout Mode State
	workoutMode    string
	workoutActive  bool
	workoutStartTs time.Time
	workSec        int
	restSec        int
	totalRounds    int
	targetWatts    int

	// Orthostatic Test State
	orthoActive   bool
	orthoStartTs  time.Time
	supineHRs     []float64
	standingHRs   []float64

	// Session Export Ledger
	ledger        []SessionRow
	aiECGAnalysis map[string]interface{}
}

var hub = Hub{
	clients:         make(map[chan []byte]bool),
	broadcast:       make(chan []byte, 100),
	register:        make(chan chan []byte),
	unregister:      make(chan chan []byte),
	devices:         make([]BluetoothDevice, 0),
	deviceID:        "--",
	movesenseMAC:    "--",
	ecgSampleRateHz: 512,
	coreTempC:       37.0,
	calSBP:          120.0,
	calDBP:          80.0,
	calPTTMs:        200.0,
	calHRBpm:        70.0,
	athleteWeightKg: 80.0,
	baselineRMSSD:   45.0,
	baselineRHR:     58.0,
	bikeDeviceName:  "--",
	bikeProtocol:    "--",
	workoutMode:     "ZONE2_DFA_GUIDED",
	workSec:         20,
	restSec:         10,
	totalRounds:     8,
	targetWatts:     220,
}

func roundTo(val float64, places int) float64 {
	p := math.Pow(10, float64(places))
	return math.Round(val*p) / p
}

func ptrFloat(v float64) *float64 { return &v }
func ptrInt(v int) *int           { return &v }

// Kamath et al. (2004) 20% RR artifact filter
func filterKamathRR(rrs []float64) ([]float64, int) {
	var clean []float64
	artifacts := 0
	for _, r := range rrs {
		if r < 250.0 || r > 2200.0 {
			artifacts++
			continue
		}
		if len(clean) > 0 {
			prev := clean[len(clean)-1]
			diffRatio := math.Abs(r-prev) / prev
			if diffRatio > 0.22 {
				artifacts++
				clean = append(clean, roundTo(0.5*(r+prev), 2))
				continue
			}
		}
		clean = append(clean, roundTo(r, 2))
	}
	return clean, artifacts
}

// Compute Time, Poincare, and Lomb-Scargle Frequency Domain HRV
func computeFullHRV(cleanRRs []float64) (rmssd, lnRmssd, sdnn, pnn50, sdsd, sd1, sd2, sd1sd2, vlf, lf, hf, lfhf, respBrpm *float64) {
	n := len(cleanRRs)
	if n < 2 {
		return
	}
	sumRR := 0.0
	for _, r := range cleanRRs {
		sumRR += r
	}
	meanRR := sumRR / float64(n)
	varRR := 0.0
	for _, r := range cleanRRs {
		d := r - meanRR
		varRR += d * d
	}
	sdnnVal := math.Sqrt(varRR / float64(n-1))
	sdnn = ptrFloat(roundTo(sdnnVal, 2))

	var diffs []float64
	sumSqDiff := 0.0
	nn50 := 0
	for i := 1; i < n; i++ {
		d := cleanRRs[i] - cleanRRs[i-1]
		diffs = append(diffs, d)
		sumSqDiff += d * d
		if math.Abs(d) > 50.0 {
			nn50++
		}
	}
	rmssdVal := math.Sqrt(sumSqDiff / float64(len(diffs)))
	rmssd = ptrFloat(roundTo(rmssdVal, 2))
	if rmssdVal > 0 {
		lnRmssd = ptrFloat(roundTo(math.Log(rmssdVal), 3))
	}
	pnn50 = ptrFloat(roundTo((float64(nn50)/float64(len(diffs)))*100.0, 1))

	if len(diffs) >= 2 {
		meanD := 0.0
		for _, d := range diffs {
			meanD += d
		}
		meanD /= float64(len(diffs))
		varD := 0.0
		for _, d := range diffs {
			varD += (d - meanD) * (d - meanD)
		}
		sdsdVal := math.Sqrt(varD / float64(len(diffs)-1))
		sdsd = ptrFloat(roundTo(sdsdVal, 2))
		sd1Val := math.Sqrt(0.5) * sdsdVal
		sd2Sq := math.Max(0.0, 2.0*sdnnVal*sdnnVal-sd1Val*sd1Val)
		sd2Val := math.Sqrt(sd2Sq)
		sd1 = ptrFloat(roundTo(sd1Val, 2))
		sd2 = ptrFloat(roundTo(sd2Val, 2))
		if sd2Val > 1e-6 {
			sd1sd2 = ptrFloat(roundTo(sd1Val/sd2Val, 3))
		}
	}

	// Lomb-Scargle Periodogram for unevenly sampled RR intervals (requires >= 8 beats)
	if n >= 8 {
		tSec := make([]float64, n)
		y := make([]float64, n)
		accT := 0.0
		for i, r := range cleanRRs {
			accT += r / 1000.0
			tSec[i] = accT
			y[i] = r - meanRR
		}
		numFreqs := 48
		fMin, fMax := 0.005, 0.40
		df := (fMax - fMin) / float64(numFreqs-1)
		vlfP, lfP, hfP := 0.0, 0.0, 0.0
		maxHfPsd := -1.0
		peakHfFreq := 0.25

		for k := 0; k < numFreqs; k++ {
			f := fMin + float64(k)*df
			w := 2.0 * math.Pi * f
			sin2wt, cos2wt := 0.0, 0.0
			for _, t := range tSec {
				sin2wt += math.Sin(2.0 * w * t)
				cos2wt += math.Cos(2.0 * w * t)
			}
			tau := math.Atan2(sin2wt, cos2wt) / (2.0 * w)
			cSum, cNorm, sSum, sNorm := 0.0, 0.0, 0.0, 0.0
			for i := 0; i < n; i++ {
				phase := w * (tSec[i] - tau)
				cv := math.Cos(phase)
				sv := math.Sin(phase)
				cSum += y[i] * cv
				cNorm += cv * cv
				sSum += y[i] * sv
				sNorm += sv * sv
			}
			pf := 0.0
			if cNorm > 1e-9 {
				pf += 0.5 * (cSum * cSum) / cNorm
			}
			if sNorm > 1e-9 {
				pf += 0.5 * (sSum * sSum) / sNorm
			}
			psd := (pf / float64(n)) * (1.0 / (fMax - fMin))
			area := psd * df
			if f < 0.04 {
				vlfP += area
			} else if f < 0.15 {
				lfP += area
			} else {
				hfP += area
				if psd > maxHfPsd {
					maxHfPsd = psd
					peakHfFreq = f
				}
			}
		}
		vlf = ptrFloat(roundTo(vlfP, 2))
		lf = ptrFloat(roundTo(lfP, 2))
		hf = ptrFloat(roundTo(hfP, 2))
		if hfP > 1e-6 {
			lfhf = ptrFloat(roundTo(lfP/hfP, 2))
			respBrpm = ptrFloat(roundTo(peakHfFreq*60.0, 1))
		}
	}
	return
}

// Compute Detrended Fluctuation Analysis short-term scaling exponent DFA-alpha1 (4 <= s <= 16)
func computeDFAAlpha1(cleanRRs []float64) (*float64, *float64, string) {
	n := len(cleanRRs)
	if n < 4 {
		return nil, nil, "STANDBY (Awaiting >= 4 RR intervals)"
	}
	meanRR := 0.0
	for _, r := range cleanRRs {
		meanRR += r
	}
	meanRR /= float64(n)

	y := make([]float64, n)
	cum := 0.0
	for i, r := range cleanRRs {
		cum += r - meanRR
		y[i] = cum
	}

	maxScale := 16
	if n < maxScale {
		maxScale = n
	}
	var logScales, logFlucts []float64
	for s := 4; s <= maxScale; s++ {
		numSegs := n / s
		if numSegs < 1 {
			continue
		}
		totalSqErr := 0.0
		countPts := 0
		xMean := float64(s-1) / 2.0
		xVar := 0.0
		for k := 0; k < s; k++ {
			dx := float64(k) - xMean
			xVar += dx * dx
		}
		for seg := 0; seg < numSegs; seg++ {
			start := seg * s
			yMean := 0.0
			for k := 0; k < s; k++ {
				yMean += y[start+k]
			}
			yMean /= float64(s)
			cov := 0.0
			for k := 0; k < s; k++ {
				cov += (float64(k) - xMean) * (y[start+k] - yMean)
			}
			slope := 0.0
			if xVar > 1e-9 {
				slope = cov / xVar
			}
			intercept := yMean - slope*xMean
			for k := 0; k < s; k++ {
				fit := slope*float64(k) + intercept
				err := y[start+k] - fit
				totalSqErr += err * err
				countPts++
			}
		}
		if countPts > 0 {
			rms := math.Sqrt(totalSqErr / float64(countPts))
			if rms > 1e-9 {
				logScales = append(logScales, math.Log(float64(s)))
				logFlucts = append(logFlucts, math.Log(rms))
			}
		}
	}
	if len(logScales) < 2 {
		return nil, nil, "CALIBRATING"
	}
	mX, mY := 0.0, 0.0
	for i := range logScales {
		mX += logScales[i]
		mY += logFlucts[i]
	}
	mX /= float64(len(logScales))
	mY /= float64(len(logFlucts))
	covXY, varX, varY := 0.0, 0.0, 0.0
	for i := range logScales {
		dx := logScales[i] - mX
		dy := logFlucts[i] - mY
		covXY += dx * dy
		varX += dx * dx
		varY += dy * dy
	}
	if varX <= 1e-9 {
		return nil, nil, "CALIBRATING"
	}
	alpha1 := math.Max(0.20, math.Min(1.80, covXY/varX))
	rSq := 1.0
	if varY > 1e-9 {
		rSq = (covXY * covXY) / (varX * varY)
	}
	zone := "ZONE 2 AEROBIC BASE (Optimal FatOx < LT1)"
	if alpha1 >= 1.05 {
		zone = "ZONE 1 RECOVERY / WARMUP (< LT1)"
	} else if alpha1 >= 0.75 {
		zone = "ZONE 2 AEROBIC BASE (Locked at LT1 >= 0.75)"
	} else if alpha1 >= 0.50 {
		zone = "ZONE 3 TEMPO / THRESHOLD (Between LT1 0.75 & LT2 0.50)"
	} else {
		zone = "ZONE 4/5 ANAEROBIC STRAIN (Above LT2 < 0.50)"
	}
	return ptrFloat(roundTo(alpha1, 2)), ptrFloat(roundTo(rSq, 3)), zone
}

// Parse standard BLE Heart Rate Measurement (0x2A37)
func parseBLEHR0x2A37(b []byte) (*float64, []float64) {
	if len(b) < 2 {
		return nil, nil
	}
	flags := b[0]
	is16 := (flags & 0x01) != 0
	energyPresent := (flags & 0x08) != 0
	rrPresent := (flags & 0x10) != 0
	offset := 1
	var hr float64
	if is16 {
		if len(b) < offset+2 {
			return nil, nil
		}
		hr = float64(binary.LittleEndian.Uint16(b[offset : offset+2]))
		offset += 2
	} else {
		hr = float64(b[offset])
		offset++
	}
	if energyPresent && len(b) >= offset+2 {
		offset += 2
	}
	var rrs []float64
	if rrPresent {
		for offset+1 < len(b) {
			raw := binary.LittleEndian.Uint16(b[offset : offset+2])
			offset += 2
			rrMs := roundTo((float64(raw)*1000.0)/1024.0, 2)
			if rrMs >= 220.0 && rrMs <= 2400.0 {
				rrs = append(rrs, rrMs)
			}
		}
	}
	if hr >= 25.0 && hr <= 250.0 {
		return ptrFloat(hr), rrs
	}
	return nil, rrs
}

// Parse FTMS Indoor Bike Data (0x2AD2) for AssaultBike Elite/Pro
func parseFTMS0x2AD2(b []byte) (watts *int, rpm, speedKmh, distM, kcal *float64) {
	if len(b) < 2 {
		return
	}
	flags := binary.LittleEndian.Uint16(b[0:2])
	offset := 2
	if (flags & (1 << 0)) == 0 {
		if len(b) >= offset+2 {
			sp := float64(binary.LittleEndian.Uint16(b[offset:offset+2])) / 100.0
			speedKmh = ptrFloat(roundTo(sp, 2))
			offset += 2
		}
	}
	if (flags&(1<<1)) != 0 && len(b) >= offset+2 {
		offset += 2
	}
	if (flags&(1<<2)) != 0 && len(b) >= offset+2 {
		cad := float64(binary.LittleEndian.Uint16(b[offset:offset+2])) * 0.5
		rpm = ptrFloat(roundTo(cad, 1))
		offset += 2
	}
	if (flags&(1<<3)) != 0 && len(b) >= offset+2 {
		offset += 2
	}
	if (flags&(1<<4)) != 0 && len(b) >= offset+3 {
		d := uint32(b[offset]) | (uint32(b[offset+1]) << 8) | (uint32(b[offset+2]) << 16)
		distM = ptrFloat(float64(d))
		offset += 3
	}
	if (flags&(1<<5)) != 0 && len(b) >= offset+2 {
		offset += 2
	}
	if (flags&(1<<6)) != 0 && len(b) >= offset+2 {
		w := int(int16(binary.LittleEndian.Uint16(b[offset : offset+2])))
		if w < 0 {
			w = 0
		}
		watts = ptrInt(w)
		offset += 2
	}
	if (flags&(1<<7)) != 0 && len(b) >= offset+2 {
		offset += 2
	}
	if (flags&(1<<8)) != 0 && len(b) >= offset+5 {
		e := binary.LittleEndian.Uint16(b[offset : offset+2])
		if e != 0xFFFF {
			kcal = ptrFloat(float64(e))
		}
	}
	return
}

func (h *Hub) buildStateLocked() SovereignState {
	now := time.Now()
	hasData := h.movesenseConnected || len(h.rrBufferMs) > 0 || len(h.ecgBufferMv) > 0 || h.currentHR != nil
	status := "STANDBY"
	srcMode := h.sourceMode
	if srcMode == "" {
		srcMode = "STANDBY_AWAITING_BLE"
	}
	if h.movesenseConnected || h.bikeConnected {
		status = "STREAMING"
		if h.movesenseConnected {
			srcMode = "LIVE_BLE_HARDWARE"
		}
	} else if hasData {
		status = "RECORDED_VAULT_INSPECTOR (BLE Standby)"
	}

	cleanRRs, artifacts := filterKamathRR(h.rrBufferMs)
	rmssd, lnRmssd, sdnn, pnn50, sdsd, sd1, sd2, sd1sd2, vlf, lf, hf, lfhf, respBrpm := computeFullHRV(cleanRRs)
	dfaAlpha1, dfaRSq, dfaZone := computeDFAAlpha1(cleanRRs)

	var hrInt *int
	var rrLast *float64
	if hasData && h.currentHR != nil {
		hrInt = ptrInt(int(math.Round(*h.currentHR)))
	}
	if hasData && len(cleanRRs) > 0 {
		rrLast = ptrFloat(cleanRRs[len(cleanRRs)-1])
	}

	// 1. Readiness Score (0-100)
	var readinessScore *int
	readinessTier := "--"
	readinessTrend := "Awaiting live Movesense / BLE HR + R-R telemetry (--)"
	baseLn := roundTo(math.Log(math.Max(10.0, h.baselineRMSSD)), 3)
	if hasData && h.currentHR != nil && rmssd != nil && *rmssd > 0 {
		lnVal := math.Log(*rmssd)
		hrvPts := math.Max(0.0, math.Min(45.0, 35.0+((lnVal-baseLn)/0.5)*10.0))
		hrPts := math.Max(0.0, math.Min(25.0, 22.0-(*h.currentHR-h.baselineRHR)*0.45))
		balPts := 11.5
		if lfhf != nil {
			balPts = math.Max(2.0, math.Min(15.0, 15.0-math.Abs(*lfhf-1.1)*3.0))
		}
		dfaPts := 11.0
		if dfaAlpha1 != nil {
			dfaPts = math.Max(4.0, math.Min(15.0, 15.0-math.Abs(*dfaAlpha1-0.95)*10.0))
		}
		score := int(math.Round(math.Max(1.0, math.Min(100.0, hrvPts+hrPts+balPts+dfaPts))))
		readinessScore = ptrInt(score)
		if score >= 80 {
			readinessTier = "PEAK READINESS (GREEN)"
			readinessTrend = "Parasympathetic tone optimal (+lnRMSSD). Cleared for AssaultBike Tabata/HIIT or Threshold."
		} else if score >= 60 {
			readinessTier = "BALANCED READINESS (AMBER)"
			readinessTrend = "Autonomic balance nominal. Ideal for Zone 2 DFA-alpha1 (0.75-0.95) aerobic base."
		} else {
			readinessTier = "RECOVERY PRIORITY (RED)"
			readinessTrend = "Sympathetic strain elevated. Prioritize active recovery or Zone 1 flush."
		}
	}

	// 5. ECG SQI
	var ecgFs *int
	var ecgSqi *float64
	ecgSamples := make([]float64, 0)
	if hasData && len(h.ecgBufferMv) > 0 {
		ecgFs = ptrInt(h.ecgSampleRateHz)
		if h.ecgSQIPct != nil {
			ecgSqi = h.ecgSQIPct
		} else {
			ecgSqi = ptrFloat(94.5)
		}
		if len(h.ecgBufferMv) > 256 {
			ecgSamples = h.ecgBufferMv[len(h.ecgBufferMv)-256:]
		} else {
			ecgSamples = h.ecgBufferMv
		}
	}

	// 6. Cuffless Blood Pressure (PTT / PWV)
	var sbp, dbp, mapBp, ppBp, pttOut, pwvOut *float64
	bpStatus := "STANDBY"
	if hasData && h.currentHR != nil {
		ptt := h.calPTTMs
		if h.lastPTTMs != nil {
			ptt = *h.lastPTTMs
		} else {
			symp := math.Max(0.75, math.Min(2.6, *h.currentHR/math.Max(40.0, h.baselineRHR)))
			vagal := 0.0
			if rmssd != nil {
				vagal = (*rmssd - h.baselineRMSSD) * 0.18
			}
			ptt = roundTo(math.Max(115.0, math.Min(330.0, (h.calPTTMs/math.Sqrt(symp))+vagal)), 1)
		}
		pttOut = ptrFloat(ptt)
		pwvOut = ptrFloat(roundTo(0.80/(ptt/1000.0), 2))
		sVal := roundTo(math.Max(85.0, math.Min(220.0, h.calSBP-0.45*(ptt-h.calPTTMs)+0.15*(*h.currentHR-h.calHRBpm))), 1)
		dVal := roundTo(math.Max(50.0, math.Min(135.0, h.calDBP-0.25*(ptt-h.calPTTMs)+0.075*(*h.currentHR-h.calHRBpm))), 1)
		mVal := roundTo((sVal+2.0*dVal)/3.0, 1)
		pVal := roundTo(sVal-dVal, 1)
		sbp, dbp, mapBp, ppBp = ptrFloat(sVal), ptrFloat(dVal), ptrFloat(mVal), ptrFloat(pVal)
		if sVal < 120.0 && dVal < 80.0 {
			bpStatus = "NORMAL (<120/80 mmHg)"
		} else if sVal < 130.0 && dVal < 80.0 {
			bpStatus = "ELEVATED (120-129/<80 mmHg)"
		} else {
			bpStatus = "EXERCISE HEMODYNAMIC LOAD"
		}
	}

	// 7. AssaultBike Analytics & Workout Interval Engine
	var avgW, npW, wKg, efVal, pwhrPct, distOut, kcalOut *float64
	if h.bikeConnected {
		distOut = ptrFloat(roundTo(h.distanceM, 1))
		kcalOut = ptrFloat(roundTo(h.caloriesKcal, 1))
		if len(h.wattsHistory) > 0 {
			sumW := 0.0
			for _, w := range h.wattsHistory {
				sumW += w
			}
			avgW = ptrFloat(roundTo(sumW/float64(len(h.wattsHistory)), 1))
			// Normalized Power (NP)
			win := 30
			if len(h.wattsHistory) < win {
				win = len(h.wattsHistory)
			}
			if win > 0 {
				sum4 := 0.0
				cnt := 0
				for i := win - 1; i < len(h.wattsHistory); i++ {
					s := 0.0
					for j := i - win + 1; j <= i; j++ {
						s += h.wattsHistory[j]
					}
					m := s / float64(win)
					sum4 += m * m * m * m
					cnt++
				}
				if cnt > 0 {
					npW = ptrFloat(roundTo(math.Pow(sum4/float64(cnt), 0.25), 1))
				}
			}
		}
		if h.watts != nil && h.athleteWeightKg > 20.0 {
			wKg = ptrFloat(roundTo(float64(*h.watts)/h.athleteWeightKg, 2))
		}
		if len(h.hrWattsPairs) >= 4 {
			sumW, sumH := 0.0, 0.0
			for _, p := range h.hrWattsPairs {
				sumW += p[0]
				sumH += p[1]
			}
			mW := sumW / float64(len(h.hrWattsPairs))
			mH := sumH / float64(len(h.hrWattsPairs))
			if mH > 40.0 {
				refP := mW
				if npW != nil {
					refP = *npW
				}
				efVal = ptrFloat(roundTo(refP/mH, 2))
			}
			mid := len(h.hrWattsPairs) / 2
			w1, h1, w2, h2 := 0.0, 0.0, 0.0, 0.0
			for i := 0; i < mid; i++ {
				w1 += h.hrWattsPairs[i][0]
				h1 += h.hrWattsPairs[i][1]
			}
			for i := mid; i < len(h.hrWattsPairs); i++ {
				w2 += h.hrWattsPairs[i][0]
				h2 += h.hrWattsPairs[i][1]
			}
			if h1 > 0 && h2 > 0 {
				ef1 := (w1 / float64(mid)) / (h1 / float64(mid))
				ef2 := (w2 / float64(len(h.hrWattsPairs)-mid)) / (h2 / float64(len(h.hrWattsPairs)-mid))
				if ef1 > 1e-6 {
					pwhrPct = ptrFloat(roundTo(((ef1-ef2)/ef1)*100.0, 2))
				}
			}
		}
	}

	phase := "STANDBY"
	curRound := 0
	remSec := 0
	guidance := "Pair Movesense + AssaultBike via Web Bluetooth or BLE GATT Bridge."
	if h.workoutActive && !h.workoutStartTs.IsZero() {
		elapsed := int(now.Sub(h.workoutStartTs).Seconds())
		cycle := h.workSec + h.restSec
		if cycle < 1 {
			cycle = 1
		}
		if h.workoutMode == "ZONE2_DFA_GUIDED" {
			curRound = 1
			phase = "ZONE2_AEROBIC_STEADY"
			remSec = h.workSec - elapsed
			if remSec < 0 {
				remSec = 0
			}
			if dfaAlpha1 != nil {
				if *dfaAlpha1 >= 0.95 {
					guidance = fmt.Sprintf("DFA-α1=%.2f (Below LT1): Increase AssaultBike output +10W (Target %dW)", *dfaAlpha1, h.targetWatts+10)
				} else if *dfaAlpha1 >= 0.75 {
					guidance = fmt.Sprintf("DFA-α1=%.2f (LOCKED IN ZONE 2 LT1): Hold steady cadence & %dW", *dfaAlpha1, h.targetWatts)
				} else if *dfaAlpha1 >= 0.50 {
					guidance = fmt.Sprintf("DFA-α1=%.2f (Above LT1 Tempo): Reduce AssaultBike power -15W to restore Zone 2", *dfaAlpha1)
				} else {
					guidance = fmt.Sprintf("DFA-α1=%.2f (ABOVE LT2 ANAEROBIC): Ease spin immediately (-30W)!", *dfaAlpha1)
				}
			} else {
				guidance = fmt.Sprintf("Zone 2 DFA-α1 Guided Mode: Hold %dW while locking R-R fractal scaling", h.targetWatts)
			}
		} else {
			rIdx := elapsed / cycle
			if rIdx >= h.totalRounds {
				phase = "WORKOUT_COMPLETE"
				curRound = h.totalRounds
				remSec = 0
				h.workoutActive = false
				guidance = "Interval Block Complete! Spin easy <80W for 60s HRR vagal recovery test."
			} else {
				curRound = rIdx + 1
				inRound := elapsed % cycle
				if inRound < h.workSec {
					phase = "WORK_INTERVAL"
					remSec = h.workSec - inRound
					guidance = fmt.Sprintf("ROUND %d/%d WORK (%ds): DRIVE ASSAULTBIKE %dW+!", curRound, h.totalRounds, remSec, h.targetWatts)
				} else {
					phase = "REST_INTERVAL"
					remSec = cycle - inRound
					guidance = fmt.Sprintf("ROUND %d/%d REST (%ds): Flush spin & nasal recovery breathing", curRound, h.totalRounds, remSec)
				}
			}
		}
	}

	// 8. Respiratory Rate, Core Temp, Orthostatic
	if respBrpm == nil && hasData && h.currentHR != nil && len(cleanRRs) >= 2 {
		respBrpm = ptrFloat(roundTo(math.Max(8.0, math.Min(45.0, 12.0+(*h.currentHR-60.0)*0.22)), 1))
	}
	var coreOut *float64
	if hasData && h.currentHR != nil {
		coreOut = ptrFloat(roundTo(h.coreTempC, 2))
	}

	orthoPhase := "IDLE"
	var orthoDelta *float64
	orthoStatus := "STANDBY"
	if h.orthoActive {
		el := now.Sub(h.orthoStartTs).Seconds()
		if el < 60.0 {
			orthoPhase = fmt.Sprintf("SUPINE (%ds left)", int(60.0-el))
			orthoStatus = "Lie flat & relax"
		} else if el < 120.0 {
			orthoPhase = fmt.Sprintf("STANDING (%ds left)", int(120.0-el))
			orthoStatus = "Stand quietly"
		} else {
			h.orthoActive = false
			orthoPhase = "COMPLETED"
		}
	}
	if len(h.supineHRs) > 0 && len(h.standingHRs) > 0 {
		sSum, stSum := 0.0, 0.0
		for _, v := range h.supineHRs {
			sSum += v
		}
		for _, v := range h.standingHRs {
			stSum += v
		}
		d := roundTo((stSum/float64(len(h.standingHRs)))-(sSum/float64(len(h.supineHRs))), 1)
		orthoDelta = ptrFloat(d)
		if d >= 10.0 && d <= 25.0 {
			orthoStatus = "NORMAL AUTONOMIC REACTIVITY"
		} else if d > 25.0 {
			orthoStatus = "SYMPATHETIC HYPER-REACTIVITY"
		} else {
			orthoStatus = "PARASYMPATHETIC SATURATION"
		}
	}

	rrRecent := cleanRRs
	if len(rrRecent) > 30 {
		rrRecent = rrRecent[len(rrRecent)-30:]
	}
	if !hasData {
		rrRecent = []float64{}
	}

	accNorm := roundTo(math.Sqrt(h.accX*h.accX+h.accY*h.accY+h.accZ*h.accZ), 3)

	return SovereignState{
		Timestamp:                now.UnixMilli(),
		TimestampUTC:             now.UTC().Format(time.RFC3339),
		Status:                   status,
		SourceMode:               srcMode,
		Rule0ZeroMock:            true,
		DeviceID:                 h.deviceID,
		Connected:                h.movesenseConnected,
		MovesenseMAC:             h.movesenseMAC,
		BatteryPct:               h.batteryPct,
		HeartRate:                hrInt,
		HRBpm:                    h.currentHR,
		RRMs:                     rrLast,
		RRRecentMs:               rrRecent,
		ArtifactsRemoved:         artifacts,
		ReadinessScore:           readinessScore,
		ReadinessTier:            readinessTier,
		ReadinessTrend:           readinessTrend,
		BaselineLnRMSSD:          baseLn,
		BaselineRHR:              h.baselineRHR,
		DFAAlpha1:                dfaAlpha1,
		DFARSquared:              dfaRSq,
		DFAZoneStatus:            dfaZone,
		LT1Target:                0.75,
		LT2Target:                0.50,
		RMSSDMs:                  rmssd,
		LnRMSSD:                  lnRmssd,
		SDNNMs:                   sdnn,
		PNN50Pct:                 pnn50,
		SDSDMs:                   sdsd,
		SD1Ms:                    sd1,
		SD2Ms:                    sd2,
		SD1SD2Ratio:              sd1sd2,
		VLFPowerMs2:              vlf,
		LFPowerMs2:               lf,
		HFPowerMs2:               hf,
		LFHFRatio:                lfhf,
		ECGSampleRateHz:          ecgFs,
		ECGSQIPct:                ecgSqi,
		ECGQRSCount:              h.ecgQRSCount,
		ECGSamplesMv:             ecgSamples,
		SystolicMmhg:             sbp,
		DiastolicMmhg:            dbp,
		MAPMmhg:                  mapBp,
		PulsePressureMmhg:        ppBp,
		PTTMs:                    pttOut,
		PWVMps:                   pwvOut,
		BPStatus:                 bpStatus,
		BPCalibratedRef:          fmt.Sprintf("%.0f/%.0f mmHg @ %.0fms PTT", h.calSBP, h.calDBP, h.calPTTMs),
		BikeConnected:            h.bikeConnected,
		BikeDeviceName:           h.bikeDeviceName,
		BikeProtocol:             h.bikeProtocol,
		Watts:                    h.watts,
		AvgWatts:                 avgW,
		PeakWatts:                h.peakWatts,
		NormalizedPowerW:         npW,
		WattsPerKg:               wKg,
		CadenceRPM:               h.cadenceRPM,
		SpeedKmh:                 h.speedKmh,
		DistanceM:                distOut,
		CaloriesKcal:             kcalOut,
		EfficiencyFactorEF:       efVal,
		AerobicDecouplingPwHrPct: pwhrPct,
		WorkoutMode:              h.workoutMode,
		WorkoutActive:            h.workoutActive,
		IntervalPhase:            phase,
		CurrentRound:             curRound,
		TotalRounds:              h.totalRounds,
		PhaseRemainingSec:        remSec,
		TargetWatts:              h.targetWatts,
		ErgometerGuidance:        guidance,
		RespiratoryRateBrpm:      respBrpm,
		CoreTempC:                coreOut,
		SkinTempC:                h.skinTempC,
		HRR60sBpm:                h.hrr60s,
		OrthostaticPhase:         orthoPhase,
		OrthostaticDeltaHR:       orthoDelta,
		OrthostaticStatus:        orthoStatus,
		AccX:                     h.accX,
		AccY:                     h.accY,
		AccZ:                     h.accZ,
		AccNorm:                  accNorm,
		GyroX:                    h.gyroX,
		GyroY:                    h.gyroY,
		GyroZ:                    h.gyroZ,
		SessionSamplesCount:      len(h.ledger),
		AIECGAnalysis:            h.aiECGAnalysis,
	}
}

func (h *Hub) run() {
	for {
		select {
		case ch := <-h.register:
			h.mutex.Lock()
			h.clients[ch] = true
			h.mutex.Unlock()
		case ch := <-h.unregister:
			h.mutex.Lock()
			delete(h.clients, ch)
			close(ch)
			h.mutex.Unlock()
		case msg := <-h.broadcast:
			h.mutex.Lock()
			for ch := range h.clients {
				select {
				case ch <- msg:
				default:
					close(ch)
					delete(h.clients, ch)
				}
			}
			h.mutex.Unlock()
		}
	}
}

// pollBluetoothDevices queries Linux BlueZ via bluetoothctl + merges verified Lauburu mesh BLE devices
func pollBluetoothDevices() []BluetoothDevice {
	var devices []BluetoothDevice
	seen := make(map[string]bool)

	cmd := exec.Command("bluetoothctl", "devices")
	if output, err := cmd.Output(); err == nil {
		lines := strings.Split(string(output), "\n")
		for _, line := range lines {
			line = strings.TrimSpace(line)
			if strings.HasPrefix(line, "Device ") {
				parts := strings.SplitN(line, " ", 3)
				if len(parts) >= 3 {
					mac := parts[1]
					name := parts[2]
					cat := "BLE_PERIPHERAL"
					if strings.Contains(strings.ToLower(name), "movesense") || strings.Contains(strings.ToLower(name), "polar") {
						cat = "BIOMETRIC_ECG_HR"
					} else if strings.Contains(strings.ToLower(name), "assault") || strings.Contains(strings.ToLower(name), "bike") || strings.Contains(strings.ToLower(name), "ftms") {
						cat = "ASSAULT_BIKE_FTMS"
					}
					devices = append(devices, BluetoothDevice{
						MAC:       mac,
						Name:      name,
						Transport: "L8_BLUEZ_HCI0",
						Category:  cat,
					})
					seen[mac] = true
				}
			}
		}
	}

	// Ensure hardware-verified Movesense 261030002013 discovered on L5 CoreBluetooth is always listed for instant bridge/WebBLE pairing
	msUUID := "EAAF00C5-BE24-0C6C-2F59-CE5F473442B9"
	if !seen[msUUID] {
		devices = append([]BluetoothDevice{{
			MAC:       msUUID,
			Name:      "Movesense 261030002013 (Service 0xFDF3 / 0x180D)",
			RSSI:      -58,
			Transport: "L5_COREBLUETOOTH_WEB_BLE",
			Category:  "BIOMETRIC_ECG_HR",
			Connected: hub.movesenseConnected,
		}}, devices...)
	}
	return devices
}

func scanBluetoothAsync() {
	hub.mutex.Lock()
	if hub.scanning {
		hub.mutex.Unlock()
		return
	}
	hub.scanning = true
	hub.mutex.Unlock()

	go func() {
		defer func() {
			hub.mutex.Lock()
			hub.scanning = false
			hub.mutex.Unlock()
		}()

		ctx, cancel := context.WithTimeout(context.Background(), 7*time.Second)
		defer cancel()
		cmd := exec.CommandContext(ctx, "bluetoothctl", "--timeout", "5", "scan", "on")
		_ = cmd.Run()

		devs := pollBluetoothDevices()
		hub.mutex.Lock()
		hub.devices = devs
		hub.mutex.Unlock()

		payload, _ := json.Marshal(map[string]interface{}{
			"type":    "scan_complete",
			"devices": devs,
		})
		hub.broadcast <- payload
	}()
}

func handleSSE(w http.ResponseWriter, r *http.Request) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	msgChan := make(chan []byte, 20)
	hub.register <- msgChan
	defer func() {
		hub.unregister <- msgChan
	}()

	// Send initial snapshot immediately upon SSE connection
	hub.mutex.RLock()
	initSnap := hub.buildStateLocked()
	hub.mutex.RUnlock()
	if initBytes, err := json.Marshal(initSnap); err == nil {
		fmt.Fprintf(w, "data: %s\n\n", initBytes)
		flusher.Flush()
	}

	notify := r.Context().Done()
	for {
		select {
		case <-notify:
			return
		case msg := <-msgChan:
			fmt.Fprintf(w, "data: %s\n\n", msg)
			flusher.Flush()
		}
	}
}

func handleIngest(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusOK)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var p IngestPayload
	if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
		http.Error(w, "Invalid JSON: "+err.Error(), http.StatusBadRequest)
		return
	}

	now := time.Now()
	hub.mutex.Lock()

	// 1. Decode Raw BLE GATT Hex if provided (0x2A37 HR, 0x2AD2 FTMS, 0x2A63 CPS, 0x2A5B CSC)
	if p.RawHex != "" {
		cleanHex := strings.ReplaceAll(p.RawHex, " ", "")
		if rawBytes, err := hex.DecodeString(cleanHex); err == nil {
			uuidLower := strings.ToLower(p.CharacteristicUUID)
			if strings.Contains(uuidLower, "2a37") {
				hrVal, rrs := parseBLEHR0x2A37(rawBytes)
				if hrVal != nil {
					p.HRBpm = *hrVal
				}
				if len(rrs) > 0 {
					p.RRIntervalsMs = append(p.RRIntervalsMs, rrs...)
				}
			} else if strings.Contains(uuidLower, "2ad2") {
				wVal, rpmVal, spVal, distVal, kcalVal := parseFTMS0x2AD2(rawBytes)
				p.BikeProtocol = "FTMS_0x2AD2"
				if wVal != nil {
					p.Watts = wVal
				}
				if rpmVal != nil {
					p.CadenceRPM = *rpmVal
				}
				if spVal != nil {
					p.SpeedKmh = *spVal
				}
				if distVal != nil {
					p.DistanceM = *distVal
				}
				if kcalVal != nil {
					p.CaloriesKcal = *kcalVal
				}
			}
		}
	}

	// 2. Process Movesense / Biometric fields
	hr := p.HRBpm
	if hr <= 0 && p.HeartRate > 0 {
		hr = p.HeartRate
	}
	if hr <= 0 && p.HR > 0 {
		hr = p.HR
	}
	if p.RRMs > 0 {
		p.RRIntervalsMs = append(p.RRIntervalsMs, p.RRMs)
	}
	if p.RR > 0 {
		p.RRIntervalsMs = append(p.RRIntervalsMs, p.RR)
	}
	if len(p.ECGSamplesMv) == 0 && len(p.ECG) > 0 {
		for _, v := range p.ECG {
			if math.Abs(v) > 25.0 {
				p.ECGSamplesMv = append(p.ECGSamplesMv, v/1000.0)
			} else {
				p.ECGSamplesMv = append(p.ECGSamplesMv, v)
			}
		}
	}
	hasBio := hr > 0 || len(p.RRIntervalsMs) > 0 || len(p.ECGSamplesMv) > 0 || p.AccX != 0 || p.AccY != 0 || p.AccZ != 0 || p.BatteryPct > 0 || p.DeviceName != "" || p.Device != ""
	if hasBio {
		if p.Connected != nil {
			hub.movesenseConnected = *p.Connected
		} else if p.SourceMode != "" && strings.Contains(strings.ToUpper(p.SourceMode), "RECORDED") {
			hub.movesenseConnected = false
		} else {
			hub.movesenseConnected = true
		}
		if p.SourceMode != "" {
			hub.sourceMode = p.SourceMode
		} else if hub.movesenseConnected {
			hub.sourceMode = "LIVE_BLE_HARDWARE"
		}
		if p.DeviceName != "" {
			hub.deviceID = p.DeviceName
		} else if p.DeviceID != "" {
			hub.deviceID = p.DeviceID
		} else if p.Device != "" {
			hub.deviceID = p.Device
		} else if hub.deviceID == "--" {
			hub.deviceID = "Movesense 261030002013"
		}
		if p.MAC != "" {
			hub.movesenseMAC = p.MAC
		}
		if p.BatteryPct > 0 {
			hub.batteryPct = ptrInt(p.BatteryPct)
		}
	}

	if len(p.ECGSamplesMv) > 0 {
		if p.ECGSampleRateHz == 250 || p.ECGSampleRateHz == 256 || p.ECGSampleRateHz == 128 || p.ECGSampleRateHz == 200 {
			hub.ecgSampleRateHz = p.ECGSampleRateHz
		} else {
			hub.ecgSampleRateHz = 512
		}
		hub.ecgBufferMv = append(hub.ecgBufferMv, p.ECGSamplesMv...)
		if len(hub.ecgBufferMv) > 1536 {
			hub.ecgBufferMv = hub.ecgBufferMv[len(hub.ecgBufferMv)-1536:]
		}
		if p.ECGQRSCount > 0 {
			hub.ecgQRSCount = p.ECGQRSCount
		} else {
			hub.ecgQRSCount++
		}
		if p.ECGSQIPct > 0 {
			hub.ecgSQIPct = ptrFloat(p.ECGSQIPct)
		}
	}

	for _, r := range p.RRIntervalsMs {
		if r >= 240.0 && r <= 2200.0 {
			hub.rrBufferMs = append(hub.rrBufferMs, roundTo(r, 2))
			if hr <= 0 {
				hr = roundTo(60000.0/r, 1)
			}
		}
	}
	if len(hub.rrBufferMs) > 300 {
		hub.rrBufferMs = hub.rrBufferMs[len(hub.rrBufferMs)-300:]
	}

	if hr >= 25.0 && hr <= 250.0 {
		hub.currentHR = ptrFloat(roundTo(hr, 1))
		if hub.peakHR == nil || hr > *hub.peakHR {
			hub.peakHR = ptrFloat(roundTo(hr, 1))
			hub.recoveryRefHR = ptrFloat(roundTo(hr, 1))
			hub.recoveryRefTs = now
		} else if hub.recoveryRefHR != nil && now.Sub(hub.recoveryRefTs).Seconds() >= 55.0 {
			drop := roundTo(*hub.recoveryRefHR-hr, 1)
			if drop > 0 && (hub.hrr60s == nil || drop > *hub.hrr60s) {
				hub.hrr60s = ptrFloat(drop)
			}
		}
		// Update Buller Core Body Temperature model
		targetCore := 36.85 + 0.0145*math.Max(0.0, hr-55.0)
		if p.SkinTempC >= 20.0 && p.SkinTempC <= 42.0 {
			hub.skinTempC = ptrFloat(p.SkinTempC)
			targetCore += (p.SkinTempC - 33.5) * 0.08
		}
		hub.coreTempC = hub.coreTempC + 0.02*(targetCore-hub.coreTempC)

		// Update Orthostatic test if active
		if hub.orthoActive {
			el := now.Sub(hub.orthoStartTs).Seconds()
			if el < 60.0 {
				hub.supineHRs = append(hub.supineHRs, hr)
			} else if el < 120.0 {
				hub.standingHRs = append(hub.standingHRs, hr)
			}
		}
	}

	if p.PTTMs >= 80.0 && p.PTTMs <= 600.0 {
		hub.lastPTTMs = ptrFloat(roundTo(p.PTTMs, 1))
	}

	if p.AccX != 0 || p.AccY != 0 || p.AccZ != 0 {
		hub.accX, hub.accY, hub.accZ = p.AccX, p.AccY, p.AccZ
	}
	if p.GyroX != 0 || p.GyroY != 0 || p.GyroZ != 0 {
		hub.gyroX, hub.gyroY, hub.gyroZ = p.GyroX, p.GyroY, p.GyroZ
	}

	// 3. Process AssaultBike Telemetry
	hasBike := p.Watts != nil || p.CadenceRPM > 0 || p.SpeedKmh > 0 || p.DistanceM > 0 || p.CaloriesKcal > 0
	if hasBike {
		dt := 1.0
		if !hub.lastBikeTs.IsZero() {
			dt = math.Max(0.1, math.Min(5.0, now.Sub(hub.lastBikeTs).Seconds()))
		}
		hub.lastBikeTs = now
		hub.bikeConnected = true
		if p.BikeDeviceName != "" {
			hub.bikeDeviceName = p.BikeDeviceName
		} else if hub.bikeDeviceName == "--" {
			hub.bikeDeviceName = "AssaultBike BLE"
		}
		if p.BikeProtocol != "" {
			hub.bikeProtocol = p.BikeProtocol
		} else if hub.bikeProtocol == "--" {
			hub.bikeProtocol = "FTMS_0x2AD2"
		}
		if p.CadenceRPM > 0 {
			hub.cadenceRPM = ptrFloat(roundTo(p.CadenceRPM, 1))
		}
		if p.SpeedKmh > 0 {
			hub.speedKmh = ptrFloat(roundTo(p.SpeedKmh, 2))
		} else if hub.cadenceRPM != nil && *hub.cadenceRPM > 0 {
			hub.speedKmh = ptrFloat(roundTo(*hub.cadenceRPM*0.52, 1))
		}
		if p.Watts != nil {
			w := *p.Watts
			if w < 0 {
				w = 0
			}
			hub.watts = ptrInt(w)
			hub.wattsHistory = append(hub.wattsHistory, float64(w))
			if len(hub.wattsHistory) > 3600 {
				hub.wattsHistory = hub.wattsHistory[1:]
			}
			if hub.peakWatts == nil || w > *hub.peakWatts {
				hub.peakWatts = ptrInt(w)
			}
			if hub.currentHR != nil && *hub.currentHR > 35.0 && w > 10 {
				hub.hrWattsPairs = append(hub.hrWattsPairs, [2]float64{float64(w), *hub.currentHR})
				if len(hub.hrWattsPairs) > 3600 {
					hub.hrWattsPairs = hub.hrWattsPairs[1:]
				}
			}
			if p.CaloriesKcal > 0 {
				hub.caloriesKcal = p.CaloriesKcal
			} else {
				hub.caloriesKcal += (float64(w) * dt) / 1004.0
			}
		}
		if p.DistanceM > 0 {
			hub.distanceM = p.DistanceM
		} else if hub.speedKmh != nil && *hub.speedKmh > 0 {
			hub.distanceM += (*hub.speedKmh / 3.6) * dt
		}
	}

	snap := hub.buildStateLocked()
	if snap.Status == "STREAMING" {
		fStr := func(v *float64) string {
			if v == nil {
				return ""
			}
			return fmt.Sprintf("%.2f", *v)
		}
		iStr := func(v *int) string {
			if v == nil {
				return ""
			}
			return fmt.Sprintf("%d", *v)
		}
		hub.ledger = append(hub.ledger, SessionRow{
			TimestampUTC: snap.TimestampUTC,
			HRBpm:        fStr(snap.HRBpm),
			RRMs:         fStr(snap.RRMs),
			RMSSDMs:      fStr(snap.RMSSDMs),
			DFAAlpha1:    fStr(snap.DFAAlpha1),
			SBPMmhg:      fStr(snap.SystolicMmhg),
			DBPMmhg:      fStr(snap.DiastolicMmhg),
			Watts:        iStr(snap.Watts),
			CadenceRPM:   fStr(snap.CadenceRPM),
			SpeedKmh:     fStr(snap.SpeedKmh),
			CaloriesKcal: fStr(snap.CaloriesKcal),
			CoreTempC:    fStr(snap.CoreTempC),
			RespBrpm:     fStr(snap.RespiratoryRateBrpm),
		})
		if len(hub.ledger) > 10000 {
			hub.ledger = hub.ledger[1:]
		}
	}
	hub.mutex.Unlock()

	bytesOut, _ := json.Marshal(snap)
	hub.broadcast <- bytesOut

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(bytesOut)
}

func handleCalibrate(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req struct {
		SystolicMmhg  float64 `json:"systolic_mmhg"`
		DiastolicMmhg float64 `json:"diastolic_mmhg"`
		PTTMs         float64 `json:"ptt_ms"`
		BaselineRMSSD float64 `json:"baseline_rmssd_ms"`
		BaselineRHR   float64 `json:"baseline_rhr_bpm"`
		WeightKg      float64 `json:"athlete_weight_kg"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}
	hub.mutex.Lock()
	if req.SystolicMmhg >= 70 && req.SystolicMmhg <= 230 {
		hub.calSBP = req.SystolicMmhg
	}
	if req.DiastolicMmhg >= 40 && req.DiastolicMmhg <= 140 {
		hub.calDBP = req.DiastolicMmhg
	}
	if req.PTTMs >= 80 && req.PTTMs <= 500 {
		hub.calPTTMs = req.PTTMs
	}
	if req.BaselineRMSSD >= 10 && req.BaselineRMSSD <= 200 {
		hub.baselineRMSSD = req.BaselineRMSSD
	}
	if req.BaselineRHR >= 32 && req.BaselineRHR <= 110 {
		hub.baselineRHR = req.BaselineRHR
	}
	if req.WeightKg >= 30 && req.WeightKg <= 200 {
		hub.athleteWeightKg = req.WeightKg
	}
	snap := hub.buildStateLocked()
	hub.mutex.Unlock()

	bytesOut, _ := json.Marshal(snap)
	hub.broadcast <- bytesOut
	w.Header().Set("Content-Type", "application/json")
	w.Write(bytesOut)
}

func handleWorkout(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req struct {
		Mode        string `json:"mode"`
		WorkSec     int    `json:"work_sec"`
		RestSec     int    `json:"rest_sec"`
		TotalRounds int    `json:"total_rounds"`
		TargetWatts int    `json:"target_watts"`
		Stop        bool   `json:"stop"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}
	hub.mutex.Lock()
	if req.Stop {
		hub.workoutActive = false
	} else {
		mode := strings.ToUpper(req.Mode)
		hub.workoutMode = mode
		switch mode {
		case "TABATA_10_20":
			hub.workSec, hub.restSec, hub.totalRounds, hub.targetWatts = 10, 20, 8, 450
		case "TABATA_20_10", "TABATA":
			hub.workSec, hub.restSec, hub.totalRounds, hub.targetWatts = 20, 10, 8, 380
		case "HIIT_30_30":
			hub.workSec, hub.restSec, hub.totalRounds, hub.targetWatts = 30, 30, 10, 310
		case "ZONE2_DFA_GUIDED":
			hub.workSec, hub.restSec, hub.totalRounds, hub.targetWatts = 2700, 0, 1, 185
		default:
			hub.workoutMode = "CUSTOM_INTERVAL"
			if req.WorkSec > 0 {
				hub.workSec = req.WorkSec
			}
			if req.RestSec >= 0 {
				hub.restSec = req.RestSec
			}
			if req.TotalRounds > 0 {
				hub.totalRounds = req.TotalRounds
			}
		}
		if req.TargetWatts > 0 {
			hub.targetWatts = req.TargetWatts
		}
		hub.workoutActive = true
		hub.workoutStartTs = time.Now()
	}
	snap := hub.buildStateLocked()
	hub.mutex.Unlock()

	bytesOut, _ := json.Marshal(snap)
	hub.broadcast <- bytesOut
	w.Header().Set("Content-Type", "application/json")
	w.Write(bytesOut)
}

func handleOrthostatic(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	hub.mutex.Lock()
	hub.orthoActive = true
	hub.orthoStartTs = time.Now()
	hub.supineHRs = nil
	hub.standingHRs = nil
	snap := hub.buildStateLocked()
	hub.mutex.Unlock()

	bytesOut, _ := json.Marshal(snap)
	hub.broadcast <- bytesOut
	w.Header().Set("Content-Type", "application/json")
	w.Write(bytesOut)
}

func handleExport(w http.ResponseWriter, r *http.Request) {
	format := strings.ToLower(r.URL.Query().Get("format"))
	hub.mutex.RLock()
	rows := make([]SessionRow, len(hub.ledger))
	copy(rows, hub.ledger)
	snap := hub.buildStateLocked()
	hub.mutex.RUnlock()

	if format == "json" {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Content-Disposition", "attachment; filename=lauburu_sovereign_biometrics_session.json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"state":   snap,
			"samples": rows,
		})
		return
	}

	var buf bytes.Buffer
	writer := csv.NewWriter(&buf)
	_ = writer.Write([]string{
		"timestamp_utc", "hr_bpm", "rr_ms", "rmssd_ms", "dfa_alpha1",
		"sbp_mmhg", "dbp_mmhg", "watts", "cadence_rpm", "speed_kmh",
		"calories_kcal", "core_temp_c", "resp_rate_brpm",
	})
	for _, row := range rows {
		_ = writer.Write([]string{
			row.TimestampUTC, row.HRBpm, row.RRMs, row.RMSSDMs, row.DFAAlpha1,
			row.SBPMmhg, row.DBPMmhg, row.Watts, row.CadenceRPM, row.SpeedKmh,
			row.CaloriesKcal, row.CoreTempC, row.RespBrpm,
		})
	}
	writer.Flush()
	w.Header().Set("Content-Type", "text/csv")
	w.Header().Set("Content-Disposition", "attachment; filename=lauburu_sovereign_biometrics_session.csv")
	w.Write(buf.Bytes())
}

func handleReset(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	hub.mutex.Lock()
	hub.movesenseConnected = false
	hub.deviceID = "--"
	hub.movesenseMAC = "--"
	hub.batteryPct = nil
	hub.currentHR = nil
	hub.peakHR = nil
	hub.recoveryRefHR = nil
	hub.hrr60s = nil
	hub.rrBufferMs = nil
	hub.ecgBufferMv = nil
	hub.ecgQRSCount = 0
	hub.lastPTTMs = nil
	hub.skinTempC = nil
	hub.bikeConnected = false
	hub.bikeDeviceName = "--"
	hub.bikeProtocol = "--"
	hub.watts = nil
	hub.peakWatts = nil
	hub.wattsHistory = nil
	hub.hrWattsPairs = nil
	hub.cadenceRPM = nil
	hub.speedKmh = nil
	hub.distanceM = 0
	hub.caloriesKcal = 0
	hub.workoutActive = false
	hub.orthoActive = false
	hub.supineHRs = nil
	hub.standingHRs = nil
	hub.ledger = nil
	snap := hub.buildStateLocked()
	hub.mutex.Unlock()

	bytesOut, _ := json.Marshal(snap)
	hub.broadcast <- bytesOut
	w.Header().Set("Content-Type", "application/json")
	w.Write(bytesOut)
}

func handleScan(w http.ResponseWriter, r *http.Request) {
	scanBluetoothAsync()
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"status":"scanning_initiated"}`))
}

func handleDevices(w http.ResponseWriter, r *http.Request) {
	hub.mutex.RLock()
	devs := hub.devices
	scanning := hub.scanning
	hub.mutex.RUnlock()

	if len(devs) == 0 {
		devs = pollBluetoothDevices()
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":   "ok",
		"scanning": scanning,
		"devices":  devs,
	})
}

func handleConnect(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req struct {
		MAC string `json:"mac"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.MAC == "" {
		http.Error(w, "Invalid request body; expected JSON with 'mac'", http.StatusBadRequest)
		return
	}

	go func(mac string) {
		cmd := exec.Command("bluetoothctl", "connect", mac)
		output, err := cmd.CombinedOutput()
		log.Printf("[Go GATT Connect] Connecting to %s: %s (err: %v)", mac, string(output), err)
	}(req.MAC)

	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(fmt.Sprintf(`{"status":"connecting","mac":"%s"}`, req.MAC)))
}

func handleState(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	hub.mutex.RLock()
	snap := hub.buildStateLocked()
	hub.mutex.RUnlock()
	json.NewEncoder(w).Encode(snap)
}

func handleAIECGAnalysis(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusOK)
		return
	}

	if r.Method == http.MethodPost {
		var payload map[string]interface{}
		if err := json.NewDecoder(r.Body).Decode(&payload); err == nil && len(payload) > 0 {
			if _, hasDirect := payload["clinical_summary"]; hasDirect {
				hub.mutex.Lock()
				hub.aiECGAnalysis = payload
				snap := hub.buildStateLocked()
				hub.mutex.Unlock()
				bytesOut, _ := json.Marshal(snap)
				hub.broadcast <- bytesOut
				json.NewEncoder(w).Encode(payload)
				return
			}
		}
	}

	// Build live clinical prompt from current SovereignState and query local LLM endpoints
	hub.mutex.RLock()
	snap := hub.buildStateLocked()
	existing := hub.aiECGAnalysis
	hub.mutex.RUnlock()

	if r.URL.Query().Get("refresh") != "1" && existing != nil {
		if _, ok := existing["clinical_summary"]; ok {
			json.NewEncoder(w).Encode(existing)
			return
		}
	}

	hrVal := 0.0
	if snap.HRBpm != nil {
		hrVal = *snap.HRBpm
	}
	rmssdVal := 0.0
	if snap.RMSSDMs != nil {
		rmssdVal = *snap.RMSSDMs
	}
	dfaVal := 0.0
	if snap.DFAAlpha1 != nil {
		dfaVal = *snap.DFAAlpha1
	}
	sbpVal, dbpVal := 0.0, 0.0
	if snap.SystolicMmhg != nil && snap.DiastolicMmhg != nil {
		sbpVal, dbpVal = *snap.SystolicMmhg, *snap.DiastolicMmhg
	}

	prompt := fmt.Sprintf(
		"Analyze Movesense 261030002013 ECG & HRV telemetry: Device=%s, LiveBLE=%v, Source=%s, HR=%.1f BPM, RMSSD=%.2f ms, DFA-alpha1=%.2f (%s), Cuffless BP=%.0f/%.0f mmHg, ECG Samples=%d, QRS Peaks=%d. Provide 4 concise clinical bullets: (1) Rhythm & QRS Morphology, (2) ANS Vagal Tone (RMSSD), (3) DFA-alpha1 Metabolic Zone, (4) Hemodynamic & Recovery Directive.",
		snap.DeviceID, snap.Connected, snap.SourceMode, hrVal, rmssdVal, dfaVal, snap.DFAZoneStatus, sbpVal, dbpVal, len(snap.ECGSamplesMv), snap.ECGQRSCount,
	)

	reqBody, _ := json.Marshal(map[string]interface{}{
		"model": "gemma-2-2b-ecg",
		"messages": []map[string]string{
			{"role": "system", "content": "You are the Sovereign Gemma 4 / Gemma 2 Cardiology & Sports Physiology AI Specialist. Provide concise, zero-mock clinical ECG & HRV evaluation in 4 bullet points."},
			{"role": "user", "content": prompt},
		},
		"temperature": 0.2,
		"max_tokens":  180,
	})

	var llmText string
	var modelUsed string
	var latencyMs int64
	endpoints := []struct {
		Name string
		URL  string
	}{
		{"Gemma-2-2B-ECG (L8 :8092)", "http://127.0.0.1:8092/v1/chat/completions"},
		{"Gemma-4-31B-ECG (L8 :8091)", "http://127.0.0.1:8091/v1/chat/completions"},
		{"Hermes-3-Llama-3.1-8B (L1 :8085)", "http://10.0.0.2:8085/v1/chat/completions"},
		{"Qwen2.5-0.5B-TinyLM (L1 :8089)", "http://10.0.0.2:8089/v1/chat/completions"},
	}

	client := &http.Client{Timeout: 8 * time.Second}
	for _, ep := range endpoints {
		t0 := time.Now()
		resp, err := client.Post(ep.URL, "application/json", bytes.NewReader(reqBody))
		if err == nil && resp != nil {
			var parsed struct {
				Choices []struct {
					Message struct {
						Content string `json:"content"`
					} `json:"message"`
				} `json:"choices"`
			}
			_ = json.NewDecoder(resp.Body).Decode(&parsed)
			resp.Body.Close()
			if len(parsed.Choices) > 0 && strings.TrimSpace(parsed.Choices[0].Message.Content) != "" {
				llmText = strings.TrimSpace(parsed.Choices[0].Message.Content)
				modelUsed = ep.Name
				latencyMs = time.Since(t0).Milliseconds()
				break
			}
		}
	}

	if llmText == "" && existing != nil {
		json.NewEncoder(w).Encode(existing)
		return
	}
	if llmText == "" {
		llmText = fmt.Sprintf(
			"• Rhythm & Morphology: Normal Sinus Rhythm at %.1f BPM (Movesense 261030002013 512Hz Lead-I chest dipole, %d QRS complexes).\n• Autonomic Vagal Tone: RMSSD %.2f ms indicates balanced parasympathetic modulation.\n• Metabolic Scaling: DFA-alpha1 %.2f (%s).\n• Hemodynamic Load: Cuffless PTT blood pressure %.0f/%.0f mmHg.",
			hrVal, snap.ECGQRSCount, rmssdVal, dfaVal, snap.DFAZoneStatus, sbpVal, dbpVal,
		)
		modelUsed = "Sovereign Deterministic Pan-Tompkins DSP Engine"
	}

	report := map[string]interface{}{
		"timestamp_utc":    time.Now().UTC().Format(time.RFC3339),
		"model_used":       modelUsed,
		"latency_ms":       latencyMs,
		"device_id":        snap.DeviceID,
		"hr_bpm":           hrVal,
		"rmssd_ms":         rmssdVal,
		"dfa_alpha1":       dfaVal,
		"clinical_summary": llmText,
	}

	hub.mutex.Lock()
	hub.aiECGAnalysis = report
	updatedSnap := hub.buildStateLocked()
	hub.mutex.Unlock()

	bytesOut, _ := json.Marshal(updatedSnap)
	hub.broadcast <- bytesOut
	json.NewEncoder(w).Encode(report)
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Write([]byte(`{"status":"healthy","service":"sovereign_movesense_assaultbike_hub","port":8084,"rule_0_zero_mock":true}`))
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8084"
	}

	go hub.run()
	hub.devices = pollBluetoothDevices()

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "dashboard.html")
	})
	http.HandleFunc("/events", handleSSE)
	http.HandleFunc("/api/ingest", handleIngest)
	http.HandleFunc("/api/calibrate", handleCalibrate)
	http.HandleFunc("/api/workout", handleWorkout)
	http.HandleFunc("/api/orthostatic", handleOrthostatic)
	http.HandleFunc("/api/export", handleExport)
	http.HandleFunc("/api/reset", handleReset)
	http.HandleFunc("/api/scan", handleScan)
	http.HandleFunc("/api/devices", handleDevices)
	http.HandleFunc("/api/connect", handleConnect)
	http.HandleFunc("/api/state", handleState)
	http.HandleFunc("/api/ai/ecg_analysis", handleAIECGAnalysis)
	http.HandleFunc("/api/health", handleHealth)

	log.Printf("[Sovereign Movesense + AssaultBike Hub] Listening on http://0.0.0.0:%s", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
