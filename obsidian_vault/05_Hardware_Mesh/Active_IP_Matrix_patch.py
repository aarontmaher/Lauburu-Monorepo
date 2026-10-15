import re
with open('/Volumes/Lauburu-Monorepo/obsidian_vault/05_Hardware_Mesh/Active_IP_Matrix.md', 'r') as f:
    content = f.read()

new_row = "| **L10** | `MacMini_M2` | Mac mini (M2) | `Pending` | - | TB: `169.254.45.136` | - | 22 | Active / **ONLINE (TB)** |\n"
content = content.replace("| **GW** | `GLiNet_Router`", new_row + "| **GW** | `GLiNet_Router`")

content = content.replace("total_nodes: 9", "total_nodes: 10")
content = content.replace("mesh_topology_version: \"9-node-probed\"", "mesh_topology_version: \"10-node-probed\"")

with open('/Volumes/Lauburu-Monorepo/obsidian_vault/05_Hardware_Mesh/Active_IP_Matrix.md', 'w') as f:
    f.write(content)
