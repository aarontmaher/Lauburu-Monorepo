# server.hcl for Linux Mini (L3)
data_dir  = "/opt/nomad/data"
bind_addr = "0.0.0.0"

server {
  enabled          = true
  bootstrap_expect = 1
}

plugin "docker" {
  config {
    allow_privileged = true
  }
}
