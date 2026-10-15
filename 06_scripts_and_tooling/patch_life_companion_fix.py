import sys

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_companion.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace('res = model.generate_content(sys_prompt + "\\n" + prompt)', 'res = model.generate_content(sys_prompt + "\\\\n" + prompt)')

with open(file_path, "w") as f:
    f.write(content)
print("Syntax fixed")
