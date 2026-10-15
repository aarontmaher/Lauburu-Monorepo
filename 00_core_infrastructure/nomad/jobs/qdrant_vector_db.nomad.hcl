job "qdrant-vector-db" {
  datacenters = ["dc1"]
  type        = "service"

  # Offload vector database compute and RAM to L3 Linux Mini
  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "qdrant" {
    count = 1

    network {
      port "http" {
        static = 6333
      }
      port "grpc" {
        static = 6334
      }
    }

    volume "qdrant_storage" {
      type      = "host"
      read_only = false
      source    = "seaweed_webdav"
    }

    task "qdrant-engine" {
      driver = "docker"

      config {
        image        = "qdrant/qdrant:latest"
        ports        = ["http", "grpc"]
        network_mode = "bridge"
      }

      volume_mount {
        volume      = "qdrant_storage"
        destination = "/qdrant/storage"
        read_only   = false
      }

      resources {
        cpu    = 800
        memory = 1024
      }

      service {
        name = "qdrant-api"
        port = "http"
        check {
          type     = "http"
          path     = "/readyz"
          interval = "10s"
          timeout  = "2s"
        }
      }
    }
  }
}
