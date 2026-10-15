#!/usr/bin/env python3
"""
Lauburu JupyterLab Native Dark Window
=====================================
100% native Cocoa/WebKit macOS desktop window with forced dark background,
zero Chrome badges, zero browser tabs, and instant dashboard loading.
"""

import sys
import os
import time
import subprocess
import webview

WORKSPACE = "/Volumes/Lauburu-Monorepo"
PORT = 8890
DASHBOARD_URL = f"http://localhost:{PORT}/lab/tree/01_apps/notebooks/00_lauburu_global_master_project.ipynb"

# Ensure JupyterLab backend daemon is active
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
r = s.connect_ex(('127.0.0.1', PORT))
s.close()

if r != 0:
    subprocess.Popen([
        os.path.expanduser("~/.local/bin/jupyter-lab"),
        f"--notebook-dir={WORKSPACE}",
        "--ServerApp.token=",
        "--ServerApp.password=",
        "--ServerApp.allow_origin=*",
        "--ServerApp.disable_check_xsrf=True",
        "--no-browser",
        f"--port={PORT}",
        "--ip=127.0.0.1"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)

# Launch native Cocoa window with dark background
window = webview.create_window(
    title="Lauburu JupyterLab — Master AI Workspace",
    url=DASHBOARD_URL,
    width=1480,
    height=940,
    background_color="#0F111A",
    text_select=True,
    zoomable=True
)

webview.start()
