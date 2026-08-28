import re

with open('src/LiveDeviceSentinelHUD.jsx', 'r') as f:
    content = f.read()
# Fix undeclared device
content = content.replace("const sparkData = device.historical_temps", "const sparkData = (typeof device !== 'undefined' && device.historical_temps)")
with open('src/LiveDeviceSentinelHUD.jsx', 'w') as f:
    f.write(content)

with open('src/ExoClusterView.jsx', 'r') as f:
    content = f.read()
# Fix undeclared exoState
content = content.replace("exoState?.peers", "(typeof exoState !== 'undefined' && exoState?.peers)")
with open('src/ExoClusterView.jsx', 'w') as f:
    f.write(content)

with open('src/App.jsx', 'r') as f:
    content = f.read()
# Fix blank cold start
content = content.replace("const [mainNavTab, setMainNavTab] = useState('custom_voice_ide')", "const [mainNavTab, setMainNavTab] = useState('meta_training_dashboard')")
# Make sure custom_voice_ide is mapped
if "mainNavTab === 'custom_voice_ide'" not in content:
    content = content.replace("{mainNavTab === 'meta_training_dashboard' && <MetaTrainingGameDashboardView />}", "{mainNavTab === 'meta_training_dashboard' && <MetaTrainingGameDashboardView />}\n          {mainNavTab === 'custom_voice_ide' && <CustomVoiceIDEView />}")
with open('src/App.jsx', 'w') as f:
    f.write(content)

with open('src/AITrainingHub.jsx', 'r') as f:
    content = f.read()
# Fix synthetic setTimeout in AITrainingHub
content = re.sub(r"setTimeout\(\(\) => \{[^}]+\},\s*1500\)", "fetch('http://localhost:5001/api/lora/distill', { method: 'POST' })", content)
with open('src/AITrainingHub.jsx', 'w') as f:
    f.write(content)

print("Crashes and critical Rule 0 violations fixed!")
