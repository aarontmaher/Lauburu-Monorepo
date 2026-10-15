import 'package:flutter/material.dart';
import '../widgets/generative_ui_factory.dart';

class ChatScreen extends StatelessWidget {
  final List<String> messageStreams = [
    '{"widget_type": "ecg_graph", "data": [0.1, 0.4, 0.9, -0.2, 0.0]}',
    '{"widget_type": "mesh_topology", "nodes": ["L1", "L2", "L3"]}',
    'Standard text response from Qwen 3.8 Max.'
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Port 4000 Hub - Sovereign Chat')),
      body: ListView.builder(
        itemCount: messageStreams.length,
        itemBuilder: (context, index) {
          final stream = messageStreams[index];
          return Padding(
            padding: const EdgeInsets.all(8.0),
            // Dynamically inject Generative UI instead of raw text
            child: GenerativeUiFactory.build(stream),
          );
        },
      ),
    );
  }
}
