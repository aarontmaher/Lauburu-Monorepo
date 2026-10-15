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

# Look for views, replies, etc.
# On Gumtree mobile web or app, they usually have "Views", "Replies", "Watchers" near the ad.
start = False
for i, val in enumerate(nodes):
    if "iPhone 16 Pro" in val:
        start = True
    if start:
        print(f"[{i}] {val}")
        if i > nodes.index(val) + 20: # Just print next 20 elements
            break
