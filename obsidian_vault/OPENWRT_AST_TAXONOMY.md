---
title: "OpenWrt C Subsystems & LuCI JavaScript AST Taxonomy"
tags: [openwrt, ast_taxonomy, c_headers, libubox, libubus, uci, netifd, firewall4, luci_js]
date: 2026-08-29
---

# 🧬 OpenWrt C Subsystems & LuCI JavaScript AST Taxonomy

## 1. Core Header Hierarchies
```
include/mock_openwrt/
├── libubox/
│   ├── blobmsg.h      # TLV serialization, typed tables/arrays
│   ├── blobmsg_json.h # JSON <-> blobmsg conversion bridge
│   ├── uloop.h        # epoll/kqueue event loop, timers, process monitors
│   ├── avl.h          # Self-balancing binary search trees (avl_tree, avl_node)
│   ├── list.h         # Intrusive doubly-linked circular lists (list_head)
│   ├── ustream.h      # Buffered non-blocking stream ring-buffers
│   └── utils.h        # ARRAY_SIZE, container_of, byte order macros
├── libubus.h          # ubus_context, ubus_object, ubus_method, RPC APIs
├── uci.h              # uci_context, uci_package, uci_section, uci_ptr
└── netifd.h           # proto_handler, interface, interface_proto_state
```

## 2. Modern LuCI SPA JavaScript View Architecture
- **`form.Map(config, title, description)`**: Root container mapped to `/etc/config/<config>`.
- **`form.TypedSection` / `form.NamedSection` / `form.GridSection`**: Section layout components.
- **Form Options**: `form.Value`, `form.ListValue`, `form.Flag`, `form.DynamicList`, `form.MultiValue`.
- **Validation**: `o.datatype = 'ip4addr' | 'port' | 'host' | 'range(min,max)'`.
- **RPC Wrappers**: `rpc.declare({ object: 'obj', method: 'method' })`.

## 3. Related Knowledge Graph Links
- [[DOM_GLINET_LUCI_DEV_PIPELINE]]
- [[SPEEDIFY_TAILSCALE_REVERSE_ENGINEERING]]
- [[Index]]
