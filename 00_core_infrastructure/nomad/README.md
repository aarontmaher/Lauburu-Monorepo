# Nomad Setup and Verification Steps

## 1. Install Nomad
Ensure Nomad is installed on all nodes (e.g., via `brew install nomad` on macOS or downloading the binary for Linux/Android AVF).

## 2. Server Setup (L3 - Linux Mini)
1. Copy `server.hcl` to `/etc/nomad.d/server.hcl`.
2. Start the Nomad server:
   ```bash
   sudo nomad agent -config=/etc/nomad.d/server.hcl
   ```
   *(Or configure as a systemd service on Linux Mini)*

## 3. Client Setup (macOS: L1, L2, L5)
1. Create data and config directories:
   ```bash
   sudo mkdir -p /opt/nomad/data /etc/nomad.d
   ```
2. Copy `client.hcl` to `/etc/nomad.d/client.hcl`.
3. Copy `com.hashicorp.nomad.plist` to `/Library/LaunchDaemons/com.hashicorp.nomad.plist`.
4. Load and start the daemon:
   ```bash
   sudo launchctl load -w /Library/LaunchDaemons/com.hashicorp.nomad.plist
   ```

## 4. Client Setup (Android AVF: L6, L7)
1. Copy `client.hcl` to `/etc/nomad.d/client.hcl`.
2. Start the Nomad client agent:
   ```bash
   sudo nomad agent -config=/etc/nomad.d/client.hcl
   ```

## 5. Verification
1. Verify nodes have joined the cluster:
   ```bash
   nomad node status -address=http://100.101.39.98:4646
   ```
2. Run a test job to ensure scheduling works:
   ```bash
   nomad job init -short
   nomad job run -address=http://100.101.39.98:4646 example.nomad
   nomad job status -address=http://100.101.39.98:4646 example
   ```
