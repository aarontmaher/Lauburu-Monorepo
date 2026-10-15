# Multi-stage Dockerfile for Lauburu Port 4000 Core Engine (Rust Backend)
FROM rust:1.80-bullseye as builder

WORKDIR /usr/src/lauburu_port4000

# Copy manifests
COPY Cargo.toml ./

# Copy source code
COPY src ./src

# Build release artifacts
RUN cargo build --release --bin port4000_server

# Runtime minimal image
FROM debian:bullseye-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy binary from builder
COPY --from=builder /usr/src/lauburu_port4000/target/release/port4000_server /app/port4000_server

ENV PORT=4000
EXPOSE 4000

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:4000/health || exit 1

CMD ["/app/port4000_server"]
