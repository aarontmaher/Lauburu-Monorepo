import re

# 1. Remove ModelDownloadSidebar from App.jsx
with open('src/App.jsx', 'r') as f:
    app_content = f.read()

app_content = re.sub(r"import ModelDownloadSidebar from '\./ModelDownloadSidebar'\n?", "", app_content)
app_content = re.sub(r"<ModelDownloadSidebar />\n?", "", app_content)

with open('src/App.jsx', 'w') as f:
    f.write(app_content)
print("Removed ModelDownloadSidebar from App.jsx")

