import sys
import re

file_path = "/Volumes/Lauburu-Monorepo/01_apps/notebooks/generate_glassmorphic_master_studio.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace("iframe_html = '''", 'iframe_html = """')
content = content.replace("    '''\n    with out:", '    """\n    with out:')

with open(file_path, "w") as f:
    f.write(content)
