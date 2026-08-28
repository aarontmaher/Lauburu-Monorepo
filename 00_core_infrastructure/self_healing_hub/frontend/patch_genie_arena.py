import re

with open('src/UnifiedGenieTatamiArenaView.jsx', 'r') as f:
    content = f.read()

# Add a state for vision inspector
state_target = "const [activeView, setActiveView] = useState('3d_tatami');"
state_replacement = "const [activeView, setActiveView] = useState('3d_tatami');\n  const [visionInspectorEnabled, setVisionInspectorEnabled] = useState(false);"
content = content.replace(state_target, state_replacement)

# Add a button
button_target = """<button
              onClick={() => setActiveView('3d_tatami')}"""
button_replacement = """<button
              onClick={() => setVisionInspectorEnabled(!visionInspectorEnabled)}
              style={{
                background: visionInspectorEnabled ? 'rgba(56,189,248,0.2)' : 'rgba(255,255,255,0.05)',
                color: visionInspectorEnabled ? '#38bdf8' : '#94a3b8',
                border: `1px solid ${visionInspectorEnabled ? '#38bdf8' : 'rgba(255,255,255,0.1)'}`,
                padding: '0.4rem 0.8rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: 'bold',
                marginRight: '0.5rem'
              }}
            >
              👁️ {visionInspectorEnabled ? 'Vision Inspector: ON' : 'Vision Inspector: OFF'}
            </button>\n<button
              onClick={() => setActiveView('3d_tatami')}"""
content = content.replace(button_target, button_replacement)

# Overlay bounding boxes if active
canvas_target = """{/* 3D TATAMI CANVAS MOCKUP */}
        <div style={{ flex: 1, position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>"""
canvas_replacement = """{/* 3D TATAMI CANVAS MOCKUP */}
        <div style={{ flex: 1, position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          {visionInspectorEnabled && (
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 10, pointerEvents: 'none' }}>
              <div style={{ position: 'absolute', top: '30%', left: '40%', width: '120px', height: '180px', border: '2px dashed #00FF9D', backgroundColor: 'rgba(0,255,157,0.1)' }}>
                <span style={{ position: 'absolute', top: '-20px', left: 0, color: '#00FF9D', fontSize: '10px', background: 'rgba(0,0,0,0.7)', padding: '2px 4px' }}>Uke: Center Mass (98%)</span>
              </div>
              <div style={{ position: 'absolute', top: '50%', left: '55%', width: '80px', height: '80px', border: '2px dashed #FF3366', backgroundColor: 'rgba(255,51,102,0.1)' }}>
                <span style={{ position: 'absolute', top: '-20px', left: 0, color: '#FF3366', fontSize: '10px', background: 'rgba(0,0,0,0.7)', padding: '2px 4px' }}>Tori: Gripping Hand (92%)</span>
              </div>
            </div>
          )}"""

content = content.replace(canvas_target, canvas_replacement)

with open('src/UnifiedGenieTatamiArenaView.jsx', 'w') as f:
    f.write(content)
print("Genie Arena patched!")
