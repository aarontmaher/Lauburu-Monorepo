import re

with open('src/GlobalMeshShardingProfiler.jsx', 'r') as f:
    content = f.read()

target = "<span style={{ fontSize: '0.7rem', background: 'rgba(192,132,252,0.2)', color: '#c084fc', padding: '2px 8px', borderRadius: '10px', fontWeight: 'bold' }}>"
replacement = """<span style={{ 
      fontSize: '0.7rem', 
      background: (m.vram_req_gb / 82.8) > 0.85 ? 'rgba(239, 68, 68, 0.4)' : 'rgba(192,132,252,0.2)', 
      color: (m.vram_req_gb / 82.8) > 0.85 ? '#fca5a5' : '#c084fc', 
      padding: '2px 8px', 
      borderRadius: '10px', 
      fontWeight: 'bold',
      animation: (m.vram_req_gb / 82.8) > 0.85 ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none'
    }}>"""

content = content.replace(target, replacement)

with open('src/GlobalMeshShardingProfiler.jsx', 'w') as f:
    f.write(content)
print("Profiler patched!")
