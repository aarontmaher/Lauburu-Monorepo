with open("tui/services/blackboard_store.py", "r") as f:
    content = f.read()

content = content.replace('url = f"http://127.0.0.1:{port}/api/sensors/status"', 'url = f"http://127.0.0.1:{port}/api/v1/apps/spec-03/status"')
with open("tui/services/blackboard_store.py", "w") as f:
    f.write(content)
