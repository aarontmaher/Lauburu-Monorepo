#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06_scripts_and_tooling/mesh/wol_manager.py
=========================================
Compatibility shim and alias for canonical_network_resurrection_engine.py.
Preserves backwards compatibility for existing daemons and scripts:
- lauburu_network_cli.py
- nomad_courier_self_healer.py
- bluetooth_serial_self_healing_tui.py
- nomad_roi_cron_governor.py
"""

import sys
from pathlib import Path

NETWORK_DIR = Path(__file__).resolve().parent.parent / "network"
if str(NETWORK_DIR) not in sys.path:
    sys.path.insert(0, str(NETWORK_DIR))

from canonical_network_resurrection_engine import *
from canonical_network_resurrection_engine import (
    WoLEngine,
    CanonicalResurrectionEngine,
    DEVICES,
    construct_magic_packet,
    send_magic_packet,
    wake_bluetooth,
    resurrect_via_bluetooth_l2cap,
    inject_adb_wake_lock,
    ensure_node_connectivity,
    main,
)

if __name__ == "__main__":
    main()
