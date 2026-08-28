import re

with open('src/App.jsx', 'r') as f:
    content = f.read()

imports = """import GlobalFloatingDrawer from './components/GlobalFloatingDrawer';
import DeveloperSettingsView from './DeveloperSettingsView';
"""

if 'import GlobalFloatingDrawer' not in content:
    content = content.replace("import './index.css'\n", "import './index.css'\n" + imports)

with open('src/App.jsx', 'w') as f:
    f.write(content)
