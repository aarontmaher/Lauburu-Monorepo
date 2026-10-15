job "network-cable-analyzer" {
  datacenters = ["dc1"]
  type        = "service"

  # Target L3 Linux Mini node to protect Mac Mini host RAM (Rule 3 & Rule 10)
  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "analyzer-stack" {
    count = 1

    network {
      port "ui" {
        static = 4007
      }
      port "backend" {
        to = 8000
      }
    }

    # SeaweedFS distributed mount for persistent reports
    volume "seaweed_data" {
      type      = "host"
      read_only = false
      source    = "seaweed_webdav"
    }

    task "analyzer-frontend" {
      driver = "docker"

      config {
        image        = "network_cable_analyzer-analyzer_frontend:latest"
        ports        = ["ui"]
        network_mode = "bridge"
      }

      resources {
        cpu    = 300
        memory = 256
      }
    }

    task "ai-analyst-backend" {
      driver = "docker"

      config {
        image        = "network_cable_analyzer-ai_analyst_daemon:latest"
        ports        = ["backend"]
        network_mode = "bridge"
      }

      volume_mount {
        volume      = "seaweed_data"
        destination = "/mnt/seaweed_webdav"
        read_only   = false
      }

      resources {
        cpu    = 500
        memory = 512
      }

      service {
        name = "cable-ai-analyst"
        port = "backend"
        check {
          type     = "http"
          path     = "/health"
          interval = "15s"
          timeout  = "3s"
        }
      }
    }
  }
}
