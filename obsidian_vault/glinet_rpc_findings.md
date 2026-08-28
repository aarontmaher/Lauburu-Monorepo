# GL.iNet RPC Interface & Rust Daemon Architecture

## 1. Executive Summary
This architectural brief investigates the underlying JSON-RPC mechanisms used by GL.iNet routers (firmware 4.x+) and outlines strategies for programmatic interaction that bypass the resource-heavy Nginx/LuCI web interfaces. We explored the `tomtana/python-glinet` implementation and community documentation from `docs.shel.sh` to determine whether we should extract exact payloads or construct a custom local API using Rust.

**Verdict:** Relying purely on the `python-glinet` JSON-RPC approach inevitably wakes the HTTP daemon (uhttpd/Nginx). To maintain strict RAM governance on the `GL.iNet` node, we recommend implementing a direct `ubus` client in our Rust daemon that communicates via the `/var/run/ubus/ubus.sock` IPC socket, thereby completely disabling the HTTP UI layers.

---

## 2. Mechanics of `tomtana/python-glinet`
The `python-glinet` repository is an object-oriented Python 3 library designed to wrap the GL.iNet 4.x JSON-RPC interface.

**Key Findings:**
1. **Endpoint Target:** All requests are standard HTTP `POST` calls directed at the router's `/rpc` endpoint.
2. **Payload Structure:** It maps directly to OpenWRT's standard RPC schema:
   ```json
   {
       "jsonrpc": "2.0",
       "id": 1,
       "method": "call",
       "params": ["<SESSION_TOKEN>", "ubus_object", "ubus_method", {"arg": "value"}]
   }
   ```
3. **Authentication:** The library performs a challenge-response login flow to fetch a `sid` (session token) which is then injected into the `params` array for subsequent RPC calls.
4. **Drawback for the Mesh:** Because `python-glinet` is an HTTP client relying on `/rpc`, using its exact methodology inherently triggers the Nginx/uhttpd web server running the LuCI CGI scripts. 

---

## 3. Findings from `docs.shel.sh` (sHEL Wikispace)
The `docs.shel.sh` Wikispace details advanced OpenWRT configurations and LuCI architecture:
1. **LuCI Architecture:** LuCI is built on an MVC pattern using Lua and the CBI (Configuration Binding Interface) framework.
2. **JSON-RPC Plugin:** The `/rpc` endpoint is essentially a Lua/C CGI wrapper exposing OpenWRT's internal `ubusd` (Micro Bus Daemon) to the network.
3. **Overhead:** Leaving Nginx/LuCI active for programmatic control wastes valuable RAM. The web UI and Lua states consume disproportionate memory compared to raw system daemons.

---

## 4. Architectural Recommendation: Custom API via Rust
To achieve our low-RAM, headless execution goal for the GL.iNet gateway node, we must bypass the web tier entirely.

### Option A: Extract JSON-RPC Payloads (Not Recommended)
While we know the exact JSON-RPC formats (as documented above), sending these requires a listening HTTP server (`uhttpd` or `nginx`). This violates our requirement to disable the heavy web interfaces.

### Option B: Native Rust Daemon (Recommended)
Instead of simulating external HTTP requests, we should deploy a lightweight Rust daemon locally on the router (cross-compiled for the GL.iNet's OpenWRT target) that natively bridges our Mesh network to the router's `ubus`.

**Implementation Strategy:**
1. **Direct UBUS IPC:** Use the prototype Rust `ubus` crate or standard C FFI bindings to interact directly with `/var/run/ubus/ubus.sock`.
2. **Shell Fallback:** If pure-Rust `ubus` bindings prove unstable in our target architecture, the Rust daemon can trivially shell out to the native `ubus` command-line binary (e.g., `ubus call network.interface.lan status`).
3. **Mesh Integration:** The Rust daemon can expose a minimal, zero-allocation TCP socket or WebSockets endpoint specifically for the Tri-Orchestrator to issue commands without Lua or Nginx overhead.

## Conclusion
We have successfully mapped the JSON-RPC payloads utilized by `python-glinet`. However, because they mandate an HTTP server, they are unsuitable for a heavily constrained node. The Tri-Orchestrator should pursue an architecture where the heavy LuCI UI is stopped (`/etc/init.d/nginx stop`), and a custom Rust micro-daemon is used to broker direct `ubus` socket connections.