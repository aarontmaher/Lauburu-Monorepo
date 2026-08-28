# RPC Socket Encryption & HMAC Verification Specification

## Overview
All inter-node RPC communications across the Lauburu 7-layer mesh network (llama.cpp RPC, WoL REST API Port 18802, WebSocket Telemetry feeds) are governed by TLS 1.3 socket encryption and Cloudflare HMAC authentication.

## Core Directives
1. Zero unauthenticated port exposure across public interfaces.
2. Direct WireGuard / Tailscale mesh peering (Port 51820) with pre-shared keys.
3. Strict subnet isolation on GL.iNet hardware router (`192.168.8.0/24`).
4. Automated verification via binary integrity audits and red/blue isolation tests.
