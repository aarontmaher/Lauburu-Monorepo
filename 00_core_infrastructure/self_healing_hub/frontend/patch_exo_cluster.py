import re

with open('src/ExoClusterView.jsx', 'r') as f:
    content = f.read()

# Add import
import_statement = "import React, { useState, useEffect } from 'react';\nimport ForceGraph2D from 'react-force-graph-2d';"
content = content.replace("import React, { useState, useEffect } from 'react';", import_statement)

# Build a graphData object for ForceGraph2D
graph_data_str = """
  const graphData = {
    nodes: exoState?.peers ? Object.keys(exoState.peers).map(k => ({ id: k, val: 5 })) : [],
    links: exoState?.peers ? Object.keys(exoState.peers).slice(1).map(k => ({ source: Object.keys(exoState.peers)[0], target: k })) : []
  };
"""

content = content.replace("export default function ExoClusterView() {", "export default function ExoClusterView() {" + graph_data_str)

# Replace the visual cards mapping with the graph if the user clicks a tab or just inject it at the top
visual_box_target = """        {/* Nodes Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>"""

visual_box_replacement = """        {/* 2D Force Graph */}
        <div style={{ width: '100%', height: '300px', background: '#090d16', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', overflow: 'hidden', marginBottom: '1rem' }}>
          {graphData.nodes.length > 0 ? (
            <ForceGraph2D
              graphData={graphData}
              width={800}
              height={300}
              nodeColor={() => '#38bdf8'}
              linkColor={() => 'rgba(255,255,255,0.2)'}
              backgroundColor="#090d16"
            />
          ) : (
            <div style={{ color: '#94a3b8', padding: '1rem' }}>Waiting for peers to build graph...</div>
          )}
        </div>

        {/* Nodes Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>"""

content = content.replace(visual_box_target, visual_box_replacement)

with open('src/ExoClusterView.jsx', 'w') as f:
    f.write(content)
print("ExoClusterView patched!")
