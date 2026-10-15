FROM python:3.11-slim

# Install Tailscale
RUN apt-get update && apt-get install -y curl iptables \
    && curl -fsSL https://tailscale.com/install.sh | sh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
COPY start.sh .
RUN chmod +x start.sh

# Run Tailscale in userspace networking mode, then start Uvicorn
CMD ["./start.sh"]
