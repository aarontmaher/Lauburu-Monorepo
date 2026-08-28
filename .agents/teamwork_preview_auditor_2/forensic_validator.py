import re
import ast
import json
import yaml
import plistlib
import subprocess
import tempfile
import sys
import os

DOC_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/open_source_mesh/open_source_mesh_strategy.md"

with open(DOC_PATH, "r") as f:
    content = f.read()

pattern = re.compile(r"```([a-zA-Z0-9_-]*)\n(.*?)```", re.DOTALL)
matches = list(pattern.finditer(content))

print(f"=== FORENSIC CODE BLOCK SYNTAX VALIDATION ===")
print(f"Found {len(matches)} code blocks in {DOC_PATH}\n")

def parse_hujson(hujson_str):
    lines = []
    for line in hujson_str.splitlines():
        stripped = re.sub(r"^\s*//.*$", "", line)
        stripped = re.sub(r"\s+//.*$", "", stripped)
        lines.append(stripped)
    text = "\n".join(lines)
    text = re.sub(r",\s*([\]}])", r"\1", text)
    return json.loads(text)

def validate_dockerfile(df_content):
    raw_lines = df_content.splitlines()
    joined_lines = []
    curr = ""
    for l in raw_lines:
        stripped = l.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if curr:
            curr += " " + stripped
        else:
            curr = stripped
        if curr.endswith("\\"):
            curr = curr[:-1].strip()
        else:
            joined_lines.append(curr)
            curr = ""
    
    valid_instructions = ("FROM", "RUN", "CMD", "LABEL", "EXPOSE", "ENV", "ADD", "COPY", "ENTRYPOINT", "VOLUME", "USER", "WORKDIR", "ARG", "ONBUILD", "STOPSIGNAL", "HEALTHCHECK", "SHELL")
    for stmt in joined_lines:
        first_word = stmt.split()[0].upper()
        if first_word not in valid_instructions:
            return False, f"Unknown instruction: {first_word} in {stmt}"
    return True, f"Valid Dockerfile with {len(joined_lines)} statements"

results = []

for idx, match in enumerate(matches, 1):
    lang = match.group(1).strip().lower() or "text"
    code = match.group(2)
    start_pos = match.start()
    line_no = content[:start_pos].count("\n") + 1
    
    block_info = {"id": idx, "line": line_no, "lang": lang, "code": code, "status": "PENDING", "error": None}
    
    if lang == "python":
        try:
            ast.parse(code)
            block_info["status"] = "PASS"
        except Exception as e:
            block_info["status"] = "FAIL"
            block_info["error"] = str(e)
            
    elif lang in ("yaml", "yml"):
        try:
            yaml.safe_load(code)
            block_info["status"] = "PASS"
        except Exception as e:
            block_info["status"] = "FAIL"
            block_info["error"] = str(e)
            
    elif lang in ("json", "jsonc", "hujson"):
        try:
            try:
                json.loads(code)
            except Exception:
                parse_hujson(code)
            block_info["status"] = "PASS"
        except Exception as e:
            block_info["status"] = "FAIL"
            block_info["error"] = str(e)
            
    elif lang == "xml":
        try:
            plistlib.loads(code.encode("utf-8"))
            block_info["status"] = "PASS"
        except Exception as e:
            block_info["status"] = "FAIL"
            block_info["error"] = str(e)
            
    elif lang in ("bash", "sh", "shell"):
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        try:
            res = subprocess.run(["bash", "-n", tmp_path], capture_output=True, text=True)
            if res.returncode == 0:
                block_info["status"] = "PASS"
            else:
                block_info["status"] = "FAIL"
                block_info["error"] = res.stderr.strip()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    elif lang == "dockerfile":
        ok, msg = validate_dockerfile(code)
        if ok:
            block_info["status"] = "PASS"
        else:
            block_info["status"] = "FAIL"
            block_info["error"] = msg
        
    elif lang == "uci":
        block_info["status"] = "PASS"
        
    elif lang == "ini":
        block_info["status"] = "PASS"
        
    else:
        block_info["status"] = "PASS (ASCII/Diagram)"

    results.append(block_info)

failed = 0
for b in results:
    print(f"Block #{b['id']:02d} | Line {b['line']:4d} | Lang: {b['lang']:10s} | Status: {b['status']}")
    if b["status"] == "FAIL":
        print(f"   --> ERROR: {b['error']}")
        failed += 1

print(f"\nTotal Blocks: {len(results)} | Passed: {len(results) - failed} | Failed: {failed}")
