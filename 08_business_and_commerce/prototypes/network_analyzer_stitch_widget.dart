import 'package:flutter/material.dart';

/// Flutter / Dart Widget Prototype — Stitch 2.0 Pro Edition
/// Governing mobile & desktop apps in the Lauburu Ecosystem (Zone 2, Movesense, Port 4000).
class NetworkAnalyzerStitchWidget extends StatefulWidget {
  const NetworkAnalyzerStitchWidget({super.key});

  @override
  State<NetworkAnalyzerStitchWidget> createState() => _NetworkAnalyzerStitchWidgetState();
}

class _NetworkAnalyzerStitchWidgetState extends State<NetworkAnalyzerStitchWidget> {
  int totalNodes = 12;
  int onlineNodes = 7;
  double pooledRamGb = 148.1;
  double usedRamGb = 42.7;
  double tb4LatencyMs = 0.27;
  int nodeCountSlider = 12;

  @override
  Widget build(BuildContext context) {
    final annualSavings = nodeCountSlider * 3480;

    return Scaffold(
      backgroundColor: const Color(0xFF07090E),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F172A).withOpacity(0.8),
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF06B6D4).withOpacity(0.2),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF06B6D4).withOpacity(0.4)),
              ),
              child: const Text('⚡', style: TextStyle(fontSize: 16)),
            ),
            const SizedBox(width: 10),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'CABLE & MESH ANALYZER',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: Colors.white),
                ),
                Text(
                  'STITCH 2.0 PRO FLUTTER',
                  style: TextStyle(fontSize: 10, fontFamily: 'monospace', color: Color(0xFF06B6D4)),
                ),
              ],
            ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16.0),
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF10B981),
                foregroundColor: const Color(0xFF07090E),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              onPressed: () {},
              child: const Text('UPGRADE TO NOC', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11)),
            ),
          )
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // KPI Stat Grid
            GridView.count(
              crossAxisCount: 2,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              children: [
                _buildStatCard('POOLED AI RAM', '${pooledRamGb.toStringAsFixed(1)} GB', '$onlineNodes/$totalNodes Nodes Online', const Color(0xFF06B6D4)),
                _buildStatCard('TB4 DMA BRIDGE', '40.0 Gbps', '${tb4LatencyMs.toStringAsFixed(2)} ms Line-Rate', const Color(0xFF10B981)),
                _buildStatCard('VERIFIED CABLES', '9 Links', '8 Optimal • 1 Throttled', const Color(0xFFF59E0B)),
                _buildStatCard('DOWNTIME AVERTED', '\$3,480 /mo', '99.999% SLA Guarantee', const Color(0xFFA855F7)),
              ],
            ),

            const SizedBox(height: 20),

            // ROI Calculator Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A).withOpacity(0.6),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFF06B6D4).withOpacity(0.3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'COMMERCIAL CONVERSION ENGINE',
                    style: TextStyle(fontSize: 10, fontFamily: 'monospace', fontWeight: FontWeight.bold, color: Color(0xFF06B6D4)),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Prevent \$1,240/hr Cable & Switch Bottlenecks',
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.between,
                    children: [
                      const Text('Mesh Nodes Under Sentinel:', style: TextStyle(fontSize: 12, color: Colors.white70)),
                      Text('$nodeCountSlider Nodes', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF06B6D4))),
                    ],
                  ),
                  Slider(
                    value: nodeCountSlider.toDouble(),
                    min: 1,
                    max: 50,
                    activeColor: const Color(0xFF06B6D4),
                    onChanged: (val) => setState(() => nodeCountSlider = val.toInt()),
                  ),
                  const Divider(color: Colors.white10),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.between,
                    children: [
                      const Text('Estimated Annual Loss Prevented:', style: TextStyle(fontSize: 12, color: Colors.white70)),
                      Text('\$$annualSavings AUD', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Color(0xFF10B981))),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatCard(String label, String value, String subtitle, Color accentColor) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withOpacity(0.6),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(label, style: const TextStyle(fontSize: 10, fontFamily: 'monospace', color: Colors.white60)),
          const SizedBox(height: 4),
          Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: accentColor)),
          const SizedBox(height: 4),
          Text(subtitle, style: const TextStyle(fontSize: 9, fontFamily: 'monospace', color: Colors.white54)),
        ],
      ),
    );
  }
}
