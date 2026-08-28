import math
import time
from typing import List, Dict, Any, Optional

class EdgeTrendsEngine:
    """Computes real-time physiological & biomechanical trends from raw Movesense data
    and feeds calculations back to all connected sub-apps."""

    @staticmethod
    def calculate_rmssd(rr_intervals_ms: List[float]) -> float:
        """Root Mean Square of Successive Differences (Parasympathetic HRV)."""
        if len(rr_intervals_ms) < 2:
            return 0.0
        diffs = [rr_intervals_ms[i+1] - rr_intervals_ms[i] for i in range(len(rr_intervals_ms) - 1)]
        sum_sq = sum(d * d for d in diffs)
        return math.sqrt(sum_sq / len(diffs))

    @staticmethod
    def calculate_dfa_alpha1(rr_intervals_ms: List[float]) -> float:
        """Simplified Detrended Fluctuation Analysis scaling exponent for aerobic threshold.
        alpha1 > 0.75: Aerobic Zone 2 / Below Aerobic Threshold
        alpha1 <= 0.75: Aerobic Threshold crossed (Zone 3 / Threshold)
        alpha1 <= 0.50: Severe Intensity Domain (Zone 4/5)
        """
        if len(rr_intervals_ms) < 16:
            return 1.0  # Default baseline when buffering
        
        # Mean subtraction
        mean_rr = sum(rr_intervals_ms) / len(rr_intervals_ms)
        centered = [r - mean_rr for r in rr_intervals_ms]
        
        # Cumulative sum profile
        y = [0.0]
        for c in centered:
            y.append(y[-1] + c)
        
        # Approximate short-range scaling
        n_small = 4
        n_large = 16
        
        def root_mean_square_fluctuation(window_size: int) -> float:
            num_windows = len(y) // window_size
            if num_windows == 0:
                return 1.0
            total_var = 0.0
            for w in range(num_windows):
                seg = y[w * window_size : (w + 1) * window_size]
                # Linear trend approximation
                x = list(range(len(seg)))
                x_mean = sum(x) / len(x)
                y_mean = sum(seg) / len(seg)
                numer = sum((x[i] - x_mean) * (seg[i] - y_mean) for i in range(len(seg)))
                denom = sum((x[i] - x_mean) ** 2 for i in range(len(seg)))
                slope = numer / denom if denom != 0 else 0.0
                intercept = y_mean - slope * x_mean
                var = sum((seg[i] - (slope * x[i] + intercept)) ** 2 for i in range(len(seg))) / len(seg)
                total_var += var
            return math.sqrt(total_var / num_windows) if total_var > 0 else 1.0

        f_small = root_mean_square_fluctuation(n_small)
        f_large = root_mean_square_fluctuation(n_large)

        if f_small > 0 and f_large > 0:
            alpha1 = (math.log(f_large) - math.log(f_small)) / (math.log(n_large) - math.log(n_small))
            return max(0.2, min(1.8, alpha1))
        return 1.0

    @staticmethod
    def evaluate_combat_impact(acc_x: float, acc_y: float, acc_z: float, gyro_magnitude: float) -> Optional[Dict[str, Any]]:
        """Evaluates 9-DoF IMU movement for combat throws, sprawls, and kinetic spikes."""
        total_acc = math.sqrt(acc_x * acc_x + acc_y * acc_y + acc_z * acc_z)
        g_force = total_acc / 9.80665

        if g_force >= 3.5:
            classification = "General Kinetic Spike"
            if gyro_magnitude > 350.0 and g_force > 4.5:
                classification = "Takedown / High-Velocity Throw"
            elif g_force > 5.0:
                classification = "Heavy Ground Impact / Sprawl"
            elif gyro_magnitude > 200.0:
                classification = "Rapid Scramble / Guard Pass Transition"

            return {
                "impact_id": f"imp_{int(time.time()*1000)}",
                "timestamp": time.time(),
                "peak_g_force": round(g_force, 2),
                "peak_angular_velocity": round(gyro_magnitude, 1),
                "classification": classification,
                "intensity_score": min(100.0, round((g_force / 8.0) * 100.0, 1))
            }
        return None
