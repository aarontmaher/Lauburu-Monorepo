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
    if "Visits:" in val or "Replies:" in val:
        # Print a few nodes before and after
        start = max(0, i - 2)
        end = min(len(nodes), i + 3)
        for j in range(start, end):
            print(f"[{j}] {nodes[j]}")
        print("---")
