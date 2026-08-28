with open('src/index.css', 'r') as f:
    lines = f.readlines()

import_line = None
for i, line in enumerate(lines):
    if "@import url('https://fonts.googleapis.com/css2" in line:
        import_line = line
        lines.pop(i)
        break

if import_line:
    lines.insert(0, import_line)

with open('src/index.css', 'w') as f:
    f.writelines(lines)
