# Architecture — Status-native Public-Administration Agent

A conversational *Ämterservice* (public-administration assistant) reachable over the
**Status** messenger (web3-native, no phone number, end-to-end encrypted). Residents
ask in natural language which office is responsible, the documents required, fees and
how to book an appointment. Inference runs on **Nebius Token Factory**; an optional
**Hermes** layer can add per-user memory and tool-calling. Built for the BGA
(public-infrastructure / real-world Web3 / decentralized AI) and Nebius tracks.

## Stack (decided)

| Layer | Choice |
|---|---|
| Channel | **Status** (web3-native, no mobile number, E2E) |
| Node | **status-go / status-backend**, headless in **Docker** |
| Bridge | **Python** (signals listener + RPC client) |
| LLM | **Nebius Token Factory** (`meta-llama/Llama-3.3-70B-Instruct`) |
| Agent layer | Bridge → Nebius **direct** (current); **Hermes** optional (memory + tools) |
| Use case | **Ämterservice** assistant — municipal/government services, multilingual |
| Runtime | laptop (containerized) |

## System diagram

```
┌────────────────┐
│  Status App     │  User (iOS/Android) — adds bot via chat key / QR,
│  (mobile)       │  sends 1:1 DM. No SIM, E2E-encrypted.
└───────┬─────────┘
        │  Waku P2P (free, outbound only)
        │
╔═══════▼══════════════════════ Laptop (Docker) ══════════════════════════╗
║                                                                          ║
║  ┌──────────────────────┐                                               ║
║  │  status-backend       │   • signals WS:  ws://localhost:12345/signals ║
║  │  (status-go, headless)│        ▲ incoming msgs + contact requests     ║
║  │                       │   • control API: POST /statusgo/CallRPC       ║
║  └──────────┬────────────┘        │ outgoing msgs + accept contact       ║
║             │ ▲                    │                                      ║
║      signals│ │CallRPC             │                                      ║
║             ▼ │                    │                                      ║
║  ┌──────────────────────┐                                               ║
║  │  Bridge (Python)      │   1. contact-request signal → auto-accept     ║
║  │                       │   2. incoming msg → LLM                       ║
║  │                       │   3. chatId(=user pubkey) → session id        ║
║  │                       │   4. answer → wakuext_sendChatMessage         ║
║  └──────────┬────────────┘                                               ║
║             │  OpenAI-compatible                                         ║
║   ┌─────────┴──────── LLM_MODE ────────────┐                            ║
║   ▼ "hermes"                                ▼ "direct"                   ║
║  ┌──────────────────────┐                  (bridge calls Nebius directly,║
║  │  Hermes Agent         │                   persona + memory — fast      ║
║  │  • memory per session │                   demo path)                  ║
║  │  • tool-calling       │                                              ║
║  │  • X-Hermes-Session-Id│                                              ║
║  └──────────┬────────────┘                                              ║
╚═════════════│════════════════════════════════════════════════════════════╝
              │  OpenAI-compatible (HTTPS, outbound)
              ▼
   ┌──────────────────────────┐
   │  Nebius Token Factory      │  Llama-3.3-70B-Instruct
   │  api.tokenfactory.nebius…  │  (inference + tool-calling)
   └──────────────────────────┘
```

## Message round-trip

```
1. User types in Status app  →  Waku  →  status-backend
2. status-backend emits a signal on the signals WS
3. Bridge reads the signal:
     • contact request?  → wakuext_acceptContactRequest  (auto-accept)
     • chat message?     → continue to 4
4. Bridge: chatId (user pubkey) → session id → LLM call
     • hermes:  Hermes API with X-Hermes-Session-Id  (Hermes owns memory+tools)
     • direct:  Nebius directly with persona + in-bridge history
5. LLM → Nebius → answer text
6. Bridge: wakuext_sendChatMessage {chatId, text}  →  status-backend
7. status-backend  →  Waku  →  user's Status app
```

## Two LLM modes

- **`direct`** — bridge → Nebius directly. Fastest path to a working
  Status↔LLM demo before Hermes is wired. Bridge keeps the history.
- **`hermes`** — bridge → Hermes API → Nebius. Full agent: Hermes manages
  per-session memory + tool-calling. `X-Hermes-Session-Id` = user's chat key,
  so each user gets an isolated context.

## Session mapping (multi-user)

```
Status user ABC… (Alice)  →  session "status-ABC…"  →  own memory/context
Status user XYZ… (Bob)    →  session "status-XYZ…"  →  separate memory/context
```

The chat key is authenticated by the E2E protocol → a legitimate identity anchor.

## Track / focus-area coverage

| Requirement | Satisfied by |
|---|---|
| Infrastructure / Public Infra | Status channel, censorship-resistant, edge-deployable |
| Real-World Blockchain Adoption | Swarm decentralized storage → tamper-proof completion confirmation (planned) |
| Decentralized AI | pluggable provider — Nebius ↔ decentralized (FLock.io story) |
| Nebius track | all inference runs on Token Factory |

## Verified against a live node (v10.31.0)

All shapes below were confirmed end-to-end with a real message from the Status app:

1. `CreateAccountAndLogin` required fields: `rootDataDir`, `displayName`,
   `password`, `customizationColor` (+ `wakuV2Fleet: status.prod`).
2. Chat key = `settings_getSettings` → `public-key` (`0x04…`); shareable form via
   `CompressPublicKey` → `zQ3sh…`.
3. Incoming messages → signal `messages.new`; read via
   `wakuext_chatMessages(chatId, "", limit)` → `messages[]{id, from, text,
   contentType, contactRequestState}`.
4. Contact request arrives as `contentType 11` / `contactRequestState 1`; accept via
   `wakuext_acceptContactRequest({id})`. Reply via
   `wakuext_sendChatMessage({chatId, text, contentType: 1})`.

## Repo layout

```
.
├── README.md                # project overview + quickstart
├── ARCHITECTURE.md          # this file
├── .env                     # secrets (gitignored)
├── status/                  # the Status node
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── bootstrap.py         # create bot account, read chat key
│   ├── requirements.txt
│   └── README.md
├── bridge/                  # Status ↔ LLM bridge
│   ├── bridge.py
│   └── requirements.txt
└── tools/                   # dev utilities
    ├── nebius_toolcall_test.py   # ✅ proves tool-calling on Token Factory
    └── requirements.txt
```
