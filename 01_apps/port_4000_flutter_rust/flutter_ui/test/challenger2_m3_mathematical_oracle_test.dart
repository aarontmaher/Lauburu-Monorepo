import 'dart:math';
import 'package:test/test.dart';

/// Dart Mathematical Oracle Implementation for Client-Side DSP Algorithms
class DspMathematicalOracle {
  static List<double> applyKamathFilter(List<double>? rrList) {
    if (rrList == null || rrList.length < 2) return rrList != null ? List<double>.from(rrList) : <double>[];
    final clean = <double>[rrList[0]];
    for (int i = 1; i < rrList.length; i++) {
      final prev = clean.last;
      final curr = rrList[i];
      if (prev > 0 && (curr - prev).abs() / prev <= 0.20) {
        clean.add(curr);
      } else {
        clean.add(prev);
      }
    }
    return clean;
  }

  static double? computeRmssd(List<double>? rrList) {
    if (rrList == null || rrList.length < 2) return null;
    double sumSq = 0.0;
    for (int i = 1; i < rrList.length; i++) {
      final diff = rrList[i] - rrList[i - 1];
      sumSq += diff * diff;
    }
    return sqrt(sumSq / (rrList.length - 1));
  }

  static double? computeDfaAlpha1(List<double>? rrList) {
    if (rrList == null || rrList.length < 16) return null;
    final n = rrList.length;
    final mean = rrList.reduce((a, b) => a + b) / n;
    double cumsum = 0.0;
    final y = <double>[];
    for (int i = 0; i < n; i++) {
      cumsum += rrList[i] - mean;
      y.add(cumsum);
    }

    const scales = [4, 6, 8, 12, 16];
    final logScales = <double>[];
    final logFlucts = <double>[];

    for (final scale in scales) {
      if (scale >= n) continue;
      final segments = (n / scale).floor();
      if (segments == 0) continue;

      double sumSqErr = 0.0;
      int totalPoints = 0;

      for (int s = 0; s < segments; s++) {
        final start = s * scale;
        final seg = y.sublist(start, start + scale);
        final segLen = seg.length;

        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
        for (int i = 0; i < segLen; i++) {
          sumX += i;
          sumY += seg[i];
          sumXY += i * seg[i];
          sumX2 += i * i;
        }

        final denom = segLen * sumX2 - sumX * sumX;
        final slope = denom != 0 ? (segLen * sumXY - sumX * sumY) / denom : 0.0;
        final intercept = (sumY - slope * sumX) / segLen;

        for (int i = 0; i < segLen; i++) {
          final trend = slope * i + intercept;
          final diff = seg[i] - trend;
          sumSqErr += diff * diff;
          totalPoints++;
        }
      }

      if (totalPoints > 0) {
        final fluct = sqrt(sumSqErr / totalPoints);
        if (fluct > 1e-5) {
          logScales.add(log(scale.toDouble()));
          logFlucts.add(log(fluct));
        }
      }
    }

    if (logScales.length < 2) return null;

    double sX = 0, sY = 0, sXY = 0, sX2 = 0;
    final count = logScales.length;
    for (int i = 0; i < count; i++) {
      sX += logScales[i];
      sY += logFlucts[i];
      sXY += logScales[i] * logFlucts[i];
      sX2 += logScales[i] * logScales[i];
    }

    final d = count * sX2 - sX * sX;
    if (d == 0) return 1.0;
    final rawSlope = (count * sXY - sX * sY) / d;
    final rounded = (rawSlope * 100).round() / 100;
    return max(0.25, min(1.75, rounded));
  }

  static int? computeReadinessScore(double? hrVal, double? rmssdVal, double? alpha1Val) {
    if (hrVal == null || hrVal <= 0 || rmssdVal == null || rmssdVal <= 0) return null;
    final hrvPart = min(1.0, max(0.0, (rmssdVal - 15.0) / 65.0)) * 50.0;
    final hrPart = min(1.0, max(0.0, (85.0 - hrVal) / 40.0)) * 30.0;
    double dfaPart = 5.0;
    if (alpha1Val != null) {
      if (alpha1Val >= 0.9 && alpha1Val <= 1.3) {
        dfaPart = 20.0;
      } else if (alpha1Val > 0.75) {
        dfaPart = 15.0;
      }
    }
    return min(100, max(0, (hrvPart + hrPart + dfaPart).round()));
  }

  static String classifyZone2(double? alpha1Val, double? hrVal) {
    if (hrVal == null || hrVal <= 0) return 'Resting / Disconnected';
    if (alpha1Val == null) return 'Calibrating RR Stream...';
    if (alpha1Val >= 0.85) return 'Zone 1: Active Recovery';
    if (alpha1Val >= 0.70) return 'Zone 2: Optimal Aerobic (LT1)';
    if (alpha1Val >= 0.50) return 'Zone 3: Tempo / Aerobic Threshold';
    return 'Zone 4/5: Anaerobic / Above LT2';
  }
}

void main() {
  group('Challenger 2 M3: Mathematical DSP Oracle & Adversarial Verification', () {
    test('1. Kamath 20% Outlier Filter Invariants & Boundary Precision', () {
      expect(DspMathematicalOracle.applyKamathFilter([]), isEmpty);
      expect(DspMathematicalOracle.applyKamathFilter([800.0]), equals([800.0]));

      // Boundary tests
      expect(DspMathematicalOracle.applyKamathFilter([1000.0, 1200.0]), equals([1000.0, 1200.0]));
      expect(DspMathematicalOracle.applyKamathFilter([1000.0, 800.0]), equals([1000.0, 800.0]));
      expect(DspMathematicalOracle.applyKamathFilter([1000.0, 1200.1]), equals([1000.0, 1000.0]));
      expect(DspMathematicalOracle.applyKamathFilter([1000.0, 799.9]), equals([1000.0, 1000.0]));

      // Cascading ectopic bursts
      final dirty = [800.0, 1800.0, 1800.0, 1800.0, 850.0];
      expect(DspMathematicalOracle.applyKamathFilter(dirty), equals([800.0, 800.0, 800.0, 800.0, 850.0]));
    });

    test('2. RMSSD Exact Formula Invariants sqrt(1/(N-1) * sum(delta^2))', () {
      expect(DspMathematicalOracle.computeRmssd(null), isNull);
      expect(DspMathematicalOracle.computeRmssd([]), isNull);
      expect(DspMathematicalOracle.computeRmssd([800.0]), isNull);

      // Analytical cases
      expect(DspMathematicalOracle.computeRmssd([800.0, 850.0]), equals(50.0));
      expect(DspMathematicalOracle.computeRmssd([800.0, 850.0, 800.0]), equals(50.0));
      expect(DspMathematicalOracle.computeRmssd([1000.0, 1000.0, 1000.0]), equals(0.0));

      final triangle = [1000.0, 1010.0, 1030.0, 1060.0, 1100.0];
      final expected = sqrt(3000 / 4);
      expect((DspMathematicalOracle.computeRmssd(triangle)! - expected).abs(), lessThan(1e-10));
    });

    test('3. DFA-Alpha1 Multi-Scale Regression Invariants (N >= 16)', () {
      final rrs15 = List.generate(15, (i) => 800.0 + (i % 2 == 0 ? 30.0 : -30.0));
      expect(DspMathematicalOracle.computeDfaAlpha1(rrs15), isNull);

      final rrs16 = List.generate(16, (i) => 800.0 + (i % 2 == 0 ? 30.0 : -30.0));
      final alpha16 = DspMathematicalOracle.computeDfaAlpha1(rrs16);
      expect(alpha16, isNotNull);
      expect(alpha16!, inInclusiveRange(0.25, 1.75));

      // Degenerate flat series
      final flat = List.generate(64, (_) => 800.0);
      expect(DspMathematicalOracle.computeDfaAlpha1(flat), isNull);
    });

    test('4. Compound Readiness Score Bounds & Weighting [0, 100]', () {
      expect(DspMathematicalOracle.computeReadinessScore(null, 50.0, 1.0), isNull);
      expect(DspMathematicalOracle.computeReadinessScore(0.0, 50.0, 1.0), isNull);
      expect(DspMathematicalOracle.computeReadinessScore(60.0, null, 1.0), isNull);
      expect(DspMathematicalOracle.computeReadinessScore(60.0, 0.0, 1.0), isNull);

      // Max: HR=45, RMSSD=80, alpha1=1.0 -> 30 + 50 + 20 = 100
      expect(DspMathematicalOracle.computeReadinessScore(45.0, 80.0, 1.0), equals(100));
      // Min: HR=85, RMSSD=15, alpha1=0.40 -> 0 + 0 + 5 = 5
      expect(DspMathematicalOracle.computeReadinessScore(85.0, 15.0, 0.40), equals(5));

      // DFA tier transitions
      expect(DspMathematicalOracle.computeReadinessScore(65.0, 47.5, null), equals(45));
      expect(DspMathematicalOracle.computeReadinessScore(65.0, 47.5, 0.70), equals(45));
      expect(DspMathematicalOracle.computeReadinessScore(65.0, 47.5, 0.80), equals(55));
      expect(DspMathematicalOracle.computeReadinessScore(65.0, 47.5, 0.90), equals(60));
      expect(DspMathematicalOracle.computeReadinessScore(65.0, 47.5, 1.30), equals(60));
      expect(DspMathematicalOracle.computeReadinessScore(65.0, 47.5, 1.35), equals(55));
    });

    test('5. Zone 2 Boundary Transitions & Calibration Guards', () {
      expect(DspMathematicalOracle.classifyZone2(1.0, 0.0), equals('Resting / Disconnected'));
      expect(DspMathematicalOracle.classifyZone2(1.0, -10.0), equals('Resting / Disconnected'));
      expect(DspMathematicalOracle.classifyZone2(null, 130.0), equals('Calibrating RR Stream...'));

      const hr = 135.0;
      expect(DspMathematicalOracle.classifyZone2(0.85, hr), equals('Zone 1: Active Recovery'));
      expect(DspMathematicalOracle.classifyZone2(0.8499, hr), equals('Zone 2: Optimal Aerobic (LT1)'));
      expect(DspMathematicalOracle.classifyZone2(0.70, hr), equals('Zone 2: Optimal Aerobic (LT1)'));
      expect(DspMathematicalOracle.classifyZone2(0.6999, hr), equals('Zone 3: Tempo / Aerobic Threshold'));
      expect(DspMathematicalOracle.classifyZone2(0.50, hr), equals('Zone 3: Tempo / Aerobic Threshold'));
      expect(DspMathematicalOracle.classifyZone2(0.4999, hr), equals('Zone 4/5: Anaerobic / Above LT2'));
    });
  });
}
