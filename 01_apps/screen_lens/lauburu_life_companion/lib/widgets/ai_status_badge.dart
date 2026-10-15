import 'package:flutter/material.dart';
import '../models/ecommerce_models.dart';

/// Visual badge displaying the operational health, port, latency, and model name
/// for a local Sovereign AI mesh node.
class AiStatusBadge extends StatelessWidget {
  final AiModelStatus status;
  final VoidCallback? onTap;

  const AiStatusBadge({
    super.key,
    required this.status,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isOnline = status.isOnline;
    final MaterialColor color = isOnline ? Colors.green : Colors.red;
    final latencyText = isOnline ? '${status.latencyMs}ms' : '--';

    final roleTitle = status.port == 8082
        ? 'Sovereign Master'
        : status.port == 8083
            ? 'Metal Worker'
            : 'Syntax Node';

    return InkWell(
      key: Key('ai_badge_${status.port}'),
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: color.withAlpha(25),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withAlpha(120), width: 1.2),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Status indicator dot
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
                boxShadow: isOnline
                    ? [
                        BoxShadow(
                          color: color.withAlpha(160),
                          blurRadius: 4,
                          spreadRadius: 1,
                        )
                      ]
                    : null,
              ),
            ),
            const SizedBox(width: 8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      'Port ${status.port}',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                        color: color.shade800,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      roleTitle,
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.grey.shade700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      isOnline ? 'Online' : 'Offline',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: isOnline ? Colors.green.shade800 : Colors.red.shade800,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      '($latencyText)',
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.grey.shade600,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Status bar containing badges for all active AI inference endpoints in the mesh.
class AiMeshStatusBar extends StatelessWidget {
  final List<AiModelStatus> statuses;
  final VoidCallback? onRefresh;

  const AiMeshStatusBar({
    super.key,
    required this.statuses,
    this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('ai_mesh_status_bar'),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.grey.shade100,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.hub_outlined, size: 18, color: Colors.blueAccent),
                  const SizedBox(width: 6),
                  const Text(
                    'Local AI Mesh Telemetry',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
              if (onRefresh != null)
                IconButton(
                  icon: const Icon(Icons.refresh, size: 18),
                  tooltip: 'Probe Mesh Health',
                  onPressed: onRefresh,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: statuses.map((status) => AiStatusBadge(status: status)).toList(),
          ),
        ],
      ),
    );
  }
}
