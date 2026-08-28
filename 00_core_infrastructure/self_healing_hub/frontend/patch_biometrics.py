import re

with open('src/GrapplingVisionBiometricsView.jsx', 'r') as f:
    content = f.read()

# Replace the state initialization with an extra state for compute hub link
state_target = "const [wsStatus, setWsStatus] = useState('disconnected');"
state_replacement = "const [wsStatus, setWsStatus] = useState('disconnected');\n  const [computeHubLinked, setComputeHubLinked] = useState(false);"
content = content.replace(state_target, state_replacement)

# Add a button
button_target = """<div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={toggleConnection}"""
button_replacement = """<div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => setComputeHubLinked(!computeHubLinked)}
            style={{
              background: computeHubLinked ? 'rgba(16,185,129,0.2)' : 'rgba(255,255,255,0.05)',
              color: computeHubLinked ? '#10b981' : '#94a3b8',
              border: `1px solid ${computeHubLinked ? '#10b981' : 'rgba(255,255,255,0.1)'}`,
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem'
            }}
          >
            🔌 {computeHubLinked ? 'Compute Hub Linked (Movesense Active)' : 'Link to Compute Hub (Movesense Source)'}
          </button>
          <button
            onClick={toggleConnection}"""
content = content.replace(button_target, button_replacement)

with open('src/GrapplingVisionBiometricsView.jsx', 'w') as f:
    f.write(content)
print("Grappling Vision patched!")
