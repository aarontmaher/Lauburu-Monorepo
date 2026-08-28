import re

with open('src/LiveDeviceSentinelHUD.jsx', 'r') as f:
    content = f.read()

# Fix mock sparkData in LiveDeviceSentinelHUD
# We should map telemetry data if available, otherwise empty array
mock_data = "const sparkData = [{v: 40}, {v: 45}, {v: 42}, {v: 50}, {v: 48}, {v: 55}, {v: 52}];"
real_data = "const sparkData = device.historical_temps ? device.historical_temps.map(t => ({ v: t })) : [];"
content = content.replace(mock_data, real_data)

with open('src/LiveDeviceSentinelHUD.jsx', 'w') as f:
    f.write(content)

with open('src/LiveTrainingDataHarvesterView.jsx', 'r') as f:
    content2 = f.read()

# Fix mock setTimeout in LiveTrainingDataHarvesterView
mock_timeout = "setTimeout(() => setAiReviewStatus('✅ Dataset Approved by Swarm'), 2000)"
real_fetch = "fetch('http://localhost:5001/api/dataset/auto_review', { method: 'POST' }).then(r => r.json()).then(d => setAiReviewStatus('✅ ' + d.status)).catch(e => setAiReviewStatus('❌ Error: ' + e.message))"
content2 = content2.replace(mock_timeout, real_fetch)

with open('src/LiveTrainingDataHarvesterView.jsx', 'w') as f:
    f.write(content2)

print("Rule 0 violations fixed!")
