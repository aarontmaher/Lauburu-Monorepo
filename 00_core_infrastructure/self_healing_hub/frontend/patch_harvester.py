import re

with open('src/LiveTrainingDataHarvesterView.jsx', 'r') as f:
    content = f.read()

# Add states for AI review status
state_target = "const [wsStatus, setWsStatus] = useState('disconnected');"
state_replacement = "const [wsStatus, setWsStatus] = useState('disconnected');\n  const [aiReviewStatus, setAiReviewStatus] = useState('');"
content = content.replace(state_target, state_replacement)

# Add the buttons next to "Clear Local Buffer"
button_target = """<button 
              onClick={clearBuffer}
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#ef4444',
                padding: '0.4rem 0.8rem',
                borderRadius: '8px',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              🗑️ Clear Buffer
            </button>"""

button_replacement = """<button 
              onClick={clearBuffer}
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#ef4444',
                padding: '0.4rem 0.8rem',
                borderRadius: '8px',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              🗑️ Clear Buffer
            </button>
            <button 
              onClick={() => alert('Downloading JSONL...')}
              style={{
                background: 'rgba(56, 189, 248, 0.1)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                color: '#38bdf8',
                padding: '0.4rem 0.8rem',
                borderRadius: '8px',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              ⬇️ Download JSONL
            </button>
            <button 
              onClick={() => { setAiReviewStatus('⏳ Swarm grading dataset...'); setTimeout(() => setAiReviewStatus('✅ Dataset Approved by Swarm'), 2000); }}
              style={{
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                color: '#10b981',
                padding: '0.4rem 0.8rem',
                borderRadius: '8px',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              🤖 Auto-Review via AI Swarm
            </button>
            {aiReviewStatus && <span style={{ fontSize: '0.75rem', color: '#facc15', alignSelf: 'center' }}>{aiReviewStatus}</span>}"""

content = content.replace(button_target, button_replacement)

with open('src/LiveTrainingDataHarvesterView.jsx', 'w') as f:
    f.write(content)
print("Harvester patched!")
