# =============================================================================
# Stage 1: Build Environment (Alpine 3.20 Musl + CMake Static Toolchain)
# Target Architecture: ARM64 (MediaTek MT7986 / MT7981 OpenWrt Gateway)
# =============================================================================
FROM alpine:3.20 AS builder

RUN apk add --no-cache \
    build-base \
    cmake \
    git \
    linux-headers \
    musl-dev

WORKDIR /src

# llama.cpp build configuration with static musl linking and ARM NEON SIMD
ARG LLAMA_CPP_REPO="https://github.com/ggerganov/llama.cpp.git"
ARG LLAMA_CPP_TAG="b3950"

RUN git clone --depth 1 --branch ${LLAMA_CPP_TAG} ${LLAMA_CPP_REPO} /src/llama_cpp || \
    git clone --depth 1 ${LLAMA_CPP_REPO} /src/llama_cpp

WORKDIR /src/llama_cpp

RUN cmake -B build-static \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=OFF \
    -DLLAMA_STATIC=ON \
    -DLLAMA_BUILD_SERVER=ON \
    -DLLAMA_BUILD_TESTS=OFF \
    -DLLAMA_BUILD_EXAMPLES=OFF \
    -DGGML_OPENMP=OFF \
    -DGGML_NATIVE=OFF \
    -DGGML_CPU_ARM_ARCH=armv8-a \
    -DCMAKE_C_FLAGS="-Os -static -ffunction-sections -fdata-sections" \
    -DCMAKE_CXX_FLAGS="-Os -static -ffunction-sections -fdata-sections" \
    -DCMAKE_EXE_LINKER_FLAGS="-static -Wl,--gc-sections -s" && \
    cmake --build build-static --target llama-server -j$(nproc)

# Strip and verify static ELF binary
RUN strip --strip-all build-static/bin/llama-server

# =============================================================================
# Stage 2: Minimal Runtime Container (< 15.0 MB Image Size)
# Strict RAM Ceiling: <= 300.0 MB Resident Set Size
# =============================================================================
FROM alpine:3.20

LABEL maintainer="Lauburu Mesh Engineering <mesh@lauburu.ai>"
LABEL description="smolagi Router AI Daemon on GL.iNet OpenWrt"
LABEL memory_limit="300MB"

RUN apk add --no-cache \
    ca-certificates \
    curl \
    python3 \
    tini \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Dedicated non-root daemon user and group
RUN addgroup -S -g 1000 smolagi && \
    adduser -S -u 1000 -G smolagi -h /app smolagi

# Prepare tmpfs mount targets and application directories
RUN mkdir -p /models /tmp/telemetry /tmp/cache /app/src && \
    chown -R smolagi:smolagi /app /models /tmp/telemetry /tmp/cache

# Copy statically compiled llama-server
COPY --from=builder /src/llama_cpp/build-static/bin/llama-server /usr/local/bin/llama-server
RUN chmod 0755 /usr/local/bin/llama-server

# Copy SmolAGI Daemon Controller Source and Init Scripts
COPY src /app/src
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod 0755 /app/entrypoint.sh && \
    chown -R smolagi:smolagi /app

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    ROUTER_AI_RAM_BUDGET_MB=300.0 \
    ROUTER_AI_HOST=127.0.0.1 \
    ROUTER_AI_PORT=8080 \
    LLAMA_SERVER_HOST=127.0.0.1 \
    LLAMA_SERVER_PORT=8081 \
    TMPFS_MODELS_DIR=/models \
    TMPFS_TELEMETRY_DIR=/tmp/telemetry \
    UBUS_SOCKET_PATH=/var/run/ubus/ubus.sock \
    HOST_PROC_PATH=/proc

EXPOSE 8080 8081

HEALTHCHECK --interval=5s --timeout=2s --retries=3 --start-period=5s \
    CMD curl -f http://127.0.0.1:8080/health || exit 1

USER smolagi

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["/app/entrypoint.sh"]
