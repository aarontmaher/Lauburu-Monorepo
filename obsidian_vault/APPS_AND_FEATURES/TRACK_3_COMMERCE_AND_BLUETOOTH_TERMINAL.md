---
title: "Track 3: Commerce Sales Readiness & Bluetooth Serial Terminal"
conversation_id: "d161e75c-1d12-4715-8ca2-2eb3cab65eed"
tags: [commerce, shopify, bluetooth_terminal, rfcomm, mesh_terminal_sheet, local_ai]
---

# 🛒 Track 3: Commerce Sales Readiness & Bluetooth Serial Terminal

> **Parent Source Conversation:** [Conversation d161e75c-1d12-4715-8ca2-2eb3cab65eed](conversation://d161e75c-1d12-4715-8ca2-2eb3cab65eed)  
> **Workspace Root:** `/Volumes/Lauburu-Monorepo/01_apps/screen_lens/lauburu_life_companion`  
> **Commerce Screen:** `lib/screens/ecommerce_hub_screen.dart`  
> **Auth & Session Services:** `lib/services/shopify_auth_service.dart`, `lib/services/session_storage.dart`  
> **Bluetooth Daemon:** `06_scripts_and_tooling/bluetooth_serial_terminal_daemon.py` (TCP Port 4005)  
> **Local AI Router:** `http://127.0.0.1:8082` (Qwen 3.8 Max, 1734 ELO)  

---

## 🏛️ 1. Exact Line-by-Line Chat History & Direction Extract

From [Source Conversation d161e75c-1d12-4715-8ca2-2eb3cab65eed](conversation://d161e75c-1d12-4715-8ca2-2eb3cab65eed):

- **User Directives:**
  - **Turn 151:** *"/goal /ai-debate /screen-lens-sovereign utilise the e commerce training protocol to develop the life companion app to sales readiness and prove functionality across all the devices"*
  - **Turn 158:** *"i thin life companion app will be significantly stronger with the new bluetooth terminal features - Understanding Omni Inbox - analyse this chat and suggest how to integrate it"*
  - **Turn 160:** *"the bluetooth terminal should be integrated with the app commerce app we built - or should each individual app contain the bluetooth terminal for ai integration?"*

---

## ⚡ 2. The Architectural Consensus: Shared Daemon + In-App Terminal Sheet

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 COMMERCE & BLUETOOTH TERMINAL INTEGRATION                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. 🛡️ PHYSICAL HARDWARE MUTEX (Rule 0 & Rule 1)                             │
│    • A physical Bluetooth RFCOMM/SPP port (/dev/rfcomm0) is exclusive.      │
│    • Single host daemon owns the serial link:                               │
│      bluetooth_serial_terminal_daemon.py on TCP port 4005.                  │
│    • Eliminates kernel EBUSY collisions across multiple apps.               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. 🛒 COMMERCE APP INTEGRATION (ecommerce_hub_screen.dart)                  │
│    • Slide-Out "Mesh Terminal Sheet" (bottom sheet or developer drawer).    │
│    • Headless inventory queries, offline checkout sync, mesh audits.        │
│    • Real-time sales transactions stream to Qwen 3.8 Max for training.      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. 🌐 REUSABLE FLUTTER WIDGET FOR ECOSYSTEM                                 │
│    • lib/widgets/mesh_terminal_sheet.dart connects over local TCP 4005.     │
│    • Plug-and-play drawer imported by Zone 2, Movesense Hub, Showrunner.    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 3. Top 5 Immediate Tasks for the Commerce & Bluetooth Terminal Chat

1. [ ] Build `lib/widgets/mesh_terminal_sheet.dart` connecting to `127.0.0.1:4005` via native Dart TCP socket.
2. [ ] Add floating terminal action button to `lib/screens/ecommerce_hub_screen.dart`.
3. [ ] Implement offline inventory query macro (`stock <product_id>`) routing over Bluetooth UART.
4. [ ] Validate Shopify Cart checkout mutations (`cartCreate`, `cartLinesAdd`) with customer auth token.
5. [ ] Ensure zero port collisions when opening the terminal while movesense or other daemons run.
