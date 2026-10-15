# client.hcl for macOS (L1, L2, L5) and Android AVF (L6, L7)
data_dir  = "/opt/nomad/data"
bind_addr = "0.0.0.0"

client {
  enabled = true
  servers = ["100.101.39.98:4647"]
}

plugin "docker" {
  config {
    allow_privileged = true
  }
}
