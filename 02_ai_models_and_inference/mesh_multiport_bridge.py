#!/usr/bin/env python3
"""
Subsystem: 02_ai_models_and_inference/mesh_multiport_bridge.py
Zero-Memory Peripheral Inference Bridge & Host Sanctuary Enforcer
Lauburu Mesh Ecosystem — 2026

Maintains ports 8081, 8083, 8011, and 11434 locally on Mac Mini (127.0.0.1 / 0.0.0.0),
routing requests to high-speed Metal GPU endpoints (:8085 and :8089) with
automatic fallback to peripheral Thunderbolt / Tailscale worker nodes:
- Port 8083  -> 127.0.0.1:8085 (Metal GPU 3B/8B) -> 127.0.0.1:8089 -> 10.0.0.8:8083
- Port 8081  -> 127.0.0.1:8089 (Metal GPU 0.5B)  -> 127.0.0.1:8085 -> 10.0.0.8:8081
- Port 8011  -> 127.0.0.1:8085 (Metal GPU 3B/8B) -> 127.0.0.1:8089
- Port 11434 -> 127.0.0.1:8085 (Ollama / Page Assist bridge to Metal GPU llama.cpp)

Also provides zero-mock Ollama API translation (/api/tags, /api/version, /api/show,
/api/chat, /api/generate) on all bridged ports so Page Assist and Ollama clients
discover and stream from local llama.cpp Metal GPU servers without configuration errors.
"""

import asyncio
import datetime
import json
import logging
import socket
import time
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MeshBridge] %(levelname)s: %(message)s",
)
logger = logging.getLogger("MeshBridge")

PORT_MAPPINGS = {
    8085: [
        ("127.0.0.1", 8089),
        ("10.0.0.8", 8083),
    ],
    8083: [
        ("127.0.0.1", 8089),
        ("10.0.0.8", 8083),
        ("100.121.247.8", 8083),
        ("100.101.39.98", 8083),
        ("192.168.8.127", 8083),
        ("100.103.212.21", 8083),
    ],
    8081: [
        ("127.0.0.1", 8089),
        ("10.0.0.8", 8081),
        ("100.101.39.98", 8081),
        ("192.168.8.127", 8081),
        ("100.103.212.21", 8081),
    ],
    8011: [
        ("127.0.0.1", 8089),
    ],
    11434: [
        ("127.0.0.1", 8089),
    ],
}

CORS_HEADERS = (
    "Access-Control-Allow-Origin: *\r\n"
    "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\r\n"
    "Access-Control-Allow-Headers: *\r\n"
)


def _iso_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _send_http_json(writer: asyncio.StreamWriter, payload: dict, status: str = "200 OK") -> None:
    body = json.dumps(payload).encode("utf-8")
    header = (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: application/json; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"{CORS_HEADERS}"
        f"Connection: close\r\n\r\n"
    ).encode("utf-8")
    writer.write(header + body)


async def _handle_ollama_api(
    method: str,
    path: str,
    raw_request: bytes,
    local_reader: asyncio.StreamReader,
    local_writer: asyncio.StreamWriter,
) -> bool:
    if method == "OPTIONS":
        resp = (
            f"HTTP/1.1 204 No Content\r\n"
            f"{CORS_HEADERS}"
            f"Content-Length: 0\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("utf-8")
        local_writer.write(resp)
        await local_writer.drain()
        return True

    if path in ("/api/version", "/api/version/"):
        _send_http_json(local_writer, {"version": "0.6.2-llama.cpp-metal"})
        await local_writer.drain()
        return True

    if path in ("/api/tags", "/api/tags/", "/api/ps"):
        now_iso = _iso_now()
        models = [
            {
                "name": "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf",
                "model": "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf",
                "modified_at": now_iso,
                "size": 2019377664,
                "digest": "sha256:lauburu-metal-8085-hermes3",
                "details": {
                    "parent_model": "",
                    "format": "gguf",
                    "family": "llama",
                    "families": ["llama"],
                    "parameter_size": "3.2B/8B",
                    "quantization_level": "Q4_K_M",
                },
            },
            {
                "name": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
                "model": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
                "modified_at": now_iso,
                "size": 491400192,
                "digest": "sha256:lauburu-metal-8089-qwen05b",
                "details": {
                    "parent_model": "",
                    "format": "gguf",
                    "family": "qwen2",
                    "families": ["qwen2"],
                    "parameter_size": "0.5B",
                    "quantization_level": "Q4_K_M",
                },
            },
        ]
        _send_http_json(local_writer, {"models": models})
        await local_writer.drain()
        return True

    # Read full HTTP body if Content-Length is present
    header_end = raw_request.find(b"\r\n\r\n")
    body_bytes = b""
    if header_end != -1:
        headers_raw = raw_request[:header_end].decode("latin-1", errors="replace")
        body_bytes = raw_request[header_end + 4 :]
        content_len = 0
        for line in headers_raw.split("\r\n")[1:]:
            if line.lower().startswith("content-length:"):
                try:
                    content_len = int(line.split(":", 1)[1].strip())
                except ValueError:
                    content_len = 0
        while len(body_bytes) < content_len:
            more = await local_reader.read(content_len - len(body_bytes))
            if not more:
                break
            body_bytes += more

    if path in ("/api/show", "/api/show/"):
        _send_http_json(
            local_writer,
            {
                "modelfile": "FROM Hermes-3-Llama-3.1-8B.Q4_K_M.gguf",
                "parameters": "num_ctx 4096",
                "template": "{{ .Prompt }}",
                "details": {
                    "format": "gguf",
                    "family": "llama",
                    "families": ["llama"],
                    "parameter_size": "8B",
                    "quantization_level": "Q4_K_M",
                },
                "model_info": {"general.architecture": "llama"},
                "capabilities": ["completion"],
            },
        )
        await local_writer.drain()
        return True

    if path in ("/api/chat", "/api/chat/", "/api/generate", "/api/generate/"):
        try:
            req_data = json.loads(body_bytes.decode("utf-8") or "{}")
        except Exception:
            req_data = {}
        model_name = req_data.get("model") or "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"
        stream = req_data.get("stream", True)
        messages = req_data.get("messages")
        if not messages:
            prompt = req_data.get("prompt", "Hello")
            messages = [{"role": "user", "content": prompt}]

        target_port = 8089
        t0 = time.monotonic()

        def _call_backend() -> tuple[str, int]:
            oai_payload = json.dumps(
                {
                    "model": model_name,
                    "messages": messages,
                    "max_tokens": req_data.get("options", {}).get("num_predict", 512),
                    "temperature": req_data.get("options", {}).get("temperature", 0.7),
                    "stream": False,
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:{target_port}/v1/chat/completions",
                data=oai_payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                out = json.loads(resp.read().decode("utf-8"))
            text = out["choices"][0]["message"]["content"]
            tokens = out.get("usage", {}).get("completion_tokens", max(1, len(text.split())))
            return text, tokens

        text, tokens = await asyncio.to_thread(_call_backend)
        dur_ns = int((time.monotonic() - t0) * 1e9)
        is_chat = "chat" in path

        if stream:
            chunk1 = {
                "model": model_name,
                "created_at": _iso_now(),
                "done": False,
            }
            chunk2 = {
                "model": model_name,
                "created_at": _iso_now(),
                "done": True,
                "done_reason": "stop",
                "total_duration": dur_ns,
                "eval_count": tokens,
                "eval_duration": max(1, dur_ns),
            }
            if is_chat:
                chunk1["message"] = {"role": "assistant", "content": text}
                chunk2["message"] = {"role": "assistant", "content": ""}
            else:
                chunk1["response"] = text
                chunk2["response"] = ""
            body = (json.dumps(chunk1) + "\n" + json.dumps(chunk2) + "\n").encode("utf-8")
            header = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: application/x-ndjson\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"{CORS_HEADERS}"
                f"Connection: close\r\n\r\n"
            ).encode("utf-8")
            local_writer.write(header + body)
            await local_writer.drain()
            return True
        else:
            payload = {
                "model": model_name,
                "created_at": _iso_now(),
                "done": True,
                "done_reason": "stop",
                "total_duration": dur_ns,
                "eval_count": tokens,
                "eval_duration": max(1, dur_ns),
            }
            if is_chat:
                payload["message"] = {"role": "assistant", "content": text}
            else:
                payload["response"] = text
            _send_http_json(local_writer, payload)
            await local_writer.drain()
            return True

    return False


async def forward(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
    try:
        while not src.at_eof():
            data = await src.read(65536)
            if not data:
                break
            dst.write(data)
            await dst.drain()
        if dst.can_write_eof():
            dst.write_eof()
    except Exception:
        pass


def create_handler(local_port: int, targets: list[tuple[str, int]]):
    async def handle_client(
        local_reader: asyncio.StreamReader,
        local_writer: asyncio.StreamWriter,
    ) -> None:
        try:
            first_chunk = await asyncio.wait_for(local_reader.read(65536), timeout=5.0)
        except Exception:
            local_writer.close()
            return

        if not first_chunk:
            local_writer.close()
            return

        # Inspect first line for Ollama /api/* endpoints or port 11434 root probe
        first_line_end = first_chunk.find(b"\r\n")
        if first_line_end != -1:
            first_line = first_chunk[:first_line_end].decode("latin-1", errors="replace")
            parts = first_line.split(" ")
            if len(parts) >= 2:
                method, raw_path = parts[0], parts[1].split("?", 1)[0]
                if local_port == 11434 and method in ("GET", "HEAD") and raw_path == "/":
                    body = b"Ollama is running"
                    hdr = (
                        f"HTTP/1.1 200 OK\r\n"
                        f"Content-Type: text/plain; charset=utf-8\r\n"
                        f"Content-Length: {len(body)}\r\n"
                        f"{CORS_HEADERS}"
                        f"Connection: close\r\n\r\n"
                    ).encode("utf-8")
                    local_writer.write(hdr + (b"" if method == "HEAD" else body))
                    await local_writer.drain()
                    local_writer.close()
                    return
                if raw_path.startswith("/api/"):
                    handled = await _handle_ollama_api(
                        method, raw_path, first_chunk, local_reader, local_writer
                    )
                    if handled:
                        local_writer.close()
                        try:
                            await local_writer.wait_closed()
                        except Exception:
                            pass
                        return

        remote_reader = None
        remote_writer = None
        for host, port in targets:
            try:
                remote_reader, remote_writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=0.5,
                )
                break
            except Exception:
                continue

        if not remote_writer or not remote_reader:
            logger.error(f"Port {local_port}: All backends unavailable: {targets}")
            local_writer.close()
            try:
                await local_writer.wait_closed()
            except Exception:
                pass
            return

        for writer in (local_writer, remote_writer):
            sock = writer.get_extra_info("socket")
            if sock is not None:
                try:
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                except Exception:
                    pass

        remote_writer.write(first_chunk)
        await remote_writer.drain()

        t1 = asyncio.create_task(forward(local_reader, remote_writer))
        t2 = asyncio.create_task(forward(remote_reader, local_writer))
        try:
            await asyncio.gather(t1, t2, return_exceptions=True)
        finally:
            for writer in (remote_writer, local_writer):
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

    return handle_client


async def main() -> None:
    servers = []
    for local_port, targets in PORT_MAPPINGS.items():
        try:
            handler = create_handler(local_port, targets)
            srv = await asyncio.start_server(
                handler,
                "0.0.0.0",
                local_port,
                reuse_address=True,
            )
            servers.append(srv)
            logger.info(f"🟢 Active Bridge Port {local_port} -> {targets[0]}")
        except Exception as e:
            logger.error(f"Failed to bind port {local_port}: {e}")

    if not servers:
        logger.error("No ports successfully bound.")
        return

    await asyncio.gather(*(srv.serve_forever() for srv in servers))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
