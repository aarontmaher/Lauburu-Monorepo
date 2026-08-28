import re
with open("backend/agents/crons/daemon_supervisor.py", "r") as f:
    content = f.read()

replacement = """    DAEMON_COMMANDS = {
        "docker": {"check": ["docker", "info"], "start": ["open", "-a", "Docker"]},
        "tailscale": {"check": ["tailscale", "status"], "start": ["sudo", "tailscaled"]},
        "cloudflared": {"check": ["pgrep", "-f", "cloudflared"], "start": ["cloudflared", "tunnel", "run"]},
        "openclaw": {"check": ["pgrep", "-f", "openclaw"], "start": ["uv", "run", "openclaw"]},
        "llama.cpp": {"check": ["pgrep", "-f", "llama-server"], "start": ["./llama-server", "--port", "50052"]},
        "exo": {"check": ["pgrep", "-f", "exo"], "start": ["exo", "run"]},
        "petals": {"check": ["pgrep", "-f", "petals"], "start": ["python", "-m", "petals.cli.run_server"]},
        "accelerate": {"check": ["pgrep", "-f", "accelerate"], "start": ["accelerate", "launch"]},
        "seaweedfs": {"check": ["pgrep", "-f", "weed"], "start": ["weed", "server"]},
        "movesense": {"check": ["pgrep", "-f", "movesense_api_daemon"], "start": ["uv", "run", "python", "../03_biometrics_and_telemetry/movesense_api_daemon.py"]},
    }"""

content = re.sub(
    r"\s+DAEMON_COMMANDS = \{.*?\n    \}",
    replacement,
    content,
    flags=re.DOTALL
)

with open("backend/agents/crons/daemon_supervisor.py", "w") as f:
    f.write(content)
