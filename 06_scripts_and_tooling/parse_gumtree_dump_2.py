import xml.etree.ElementTree as ET

tree = ET.parse('window_dump.xml')
root = tree.getroot()

nodes = []
for node in root.iter('node'):
    text = node.get('text', '')
    content_desc = node.get('content-desc', '')
    val = text if text else content_desc
    if val:
        nodes.append(val)

for i, val in enumerate(nodes):
    if "view" in val.lower() or "repl" in val.lower() or "visit" in val.lower():
        print(f"Match: {val}")
