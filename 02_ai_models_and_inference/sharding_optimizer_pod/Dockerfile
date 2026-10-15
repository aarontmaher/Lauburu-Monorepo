FROM python:3.12-slim

# Install system utilities for network telemetry
RUN apt-get update && apt-get install -y \
    iproute2 \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies (llama-cpp-python for MicroLM binding)
# Note: In production on L8, this should be built with cuBLAS or OpenBLAS for CPU/GPU accel.
RUN pip install --no-cache-dir llama-cpp-python asyncio

COPY . /app

# The GGUF models are stored on the host, so we will volume mount them.
CMD ["python", "pod_orchestrator.py"]
