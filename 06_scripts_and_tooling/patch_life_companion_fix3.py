import sys

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_companion.py"
with open(file_path, "r") as f:
    lines = f.readlines()

with open(file_path, "w") as f:
    for i, line in enumerate(lines):
        if "res = model.generate_content(sys_prompt +" in line:
            f.write('                    res = model.generate_content(sys_prompt + "\\n" + prompt)\n')
        elif '" + prompt)' in line and "res = model.generate_content(sys_prompt +" in lines[i-1]:
            continue # skip the next line which was the broken continuation
        else:
            f.write(line)
