import re

with open('src/UnifiedGenieTatamiArenaView.jsx', 'r') as f:
    content = f.read()

content = re.sub(r'<Genie3DSpatialWorldView[^>]*>', '<div style={{padding: "2rem", color: "#94a3b8"}}>Consolidated into Spatial Sandbox (SpatialGrapplingMapEditorView)</div>', content)

with open('src/UnifiedGenieTatamiArenaView.jsx', 'w') as f:
    f.write(content)

with open('src/Spatial3DMapView.jsx', 'r') as f:
    content = f.read()

content = re.sub(r'<Genie3DSpatialWorldView[^>]*>', '<div style={{padding: "2rem", color: "#94a3b8"}}>Consolidated into Spatial Sandbox (SpatialGrapplingMapEditorView)</div>', content)

with open('src/Spatial3DMapView.jsx', 'w') as f:
    f.write(content)
