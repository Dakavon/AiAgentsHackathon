# Amtomat: Architecture

A private AI agent for public administration, reachable over the **Status** messenger
(web3-native, no phone number, end-to-end encrypted). Residents ask in natural language;
the agent names the responsible office and documents and, when an in-person visit is
needed, **reserves an appointment** and stores a tamper-proof, PII-free confirmation on
**Swarm**. Inference runs on **Nebius Token Factory**, and an optional **Hermes** layer
can add per-user memory and richer tool-calling. Built for the **Infrastructure** (the
Status bridge) and **BGA** tracks, powered by Nebius.

## Stack (decided)

| Layer | Choice |
|---|---|
| Channel | **Status** (web3-native, no mobile number, E2E) |
| Node | **status-go / status-backend**, headless in **Docker** |
| Bridge | **Python** (signals listener plus RPC client) |
| LLM | **Nebius Token Factory** (`meta-llama/Llama-3.3-70B-Instruct`) |
| Storage | **Swarm** via a **Bee** node (dev mode), for appointment confirmations |
| Agent tool | `reserve_appointment` stores a confirmation on Swarm (LLM tool-call) |
| Agent layer | Bridge to Nebius **direct** (current); **Hermes** optional (memory, tools) |
| Use case | **Ämterservice** assistant: municipal and government services, multilingual |
| Runtime | laptop (containerized) |

## System flow

```
Status app (mobile)                no SIM, end-to-end encrypted
   |  Waku P2P (free, outbound only)
   v
status-backend  (status-go, headless, Docker)
   |   signals WS   ws://localhost:12345/signals   (incoming msgs, contact requests)
   ^   control API  POST /statusgo/CallRPC          (outgoing msgs, accept contact)
   |
Bridge (Python)
   1. contact-request signal  ->  auto-accept
   2. incoming message        ->  LLM
   3. chatId (= user pubkey)   ->  session id
   4. answer                  ->  wakuext_sendChatMessage
   |  OpenAI-compatible, selected by LLM_MODE:
   |    direct: bridge calls Nebius directly (persona plus in-bridge history)
   |    hermes: bridge calls Hermes (per-user memory, tool-calling); Hermes calls Nebius
   v
Nebius Token Factory   Llama-3.3-70B-Instruct   (inference, tool-calling)

When the model calls reserve_appointment:
   Bridge  ->  Bee node  ->  Swarm (confirmation hash)  ->  hash appended to the reply
```

## Message round-trip

```
1. User types in Status app  ->  Waku  ->  status-backend
2. status-backend emits a signal on the signals WS
3. Bridge reads the signal:
     contact request?  ->  wakuext_acceptContactRequest  (auto-accept)
     chat message?     ->  continue to 4
4. Bridge: chatId (user pubkey)  ->  session id  ->  LLM call
     hermes:  Hermes API with X-Hermes-Session-Id  (Hermes owns memory, tools)
     direct:  Nebius directly with persona plus in-bridge history
5. LLM  ->  Nebius  ->  answer text
6. Bridge: wakuext_sendChatMessage {chatId, text}  ->  status-backend
7. status-backend  ->  Waku  ->  user's Status app
```

## Two LLM modes

- **`direct`**: the bridge calls Nebius directly. Fastest path to a working
  Status-to-LLM demo before Hermes is wired. The bridge keeps the history.
- **`hermes`**: the bridge calls the Hermes API, which calls Nebius. Full agent:
  Hermes manages per-session memory and tool-calling. `X-Hermes-Session-Id` is the
  user's chat key, so each user gets an isolated context.

## Appointment confirmation on Swarm

When a request needs an in-person visit, the model calls the `reserve_appointment` tool.
The bridge then:

1. builds a data-minimal confirmation (Option 1, no reason/PII): `type`, `office`,
   `datetime`, `reference`, `subject = sha256(chat key)`, `issuedBy`, `issuedAt`,
2. stores it on Swarm via a **Bee** node and gets a content address (hash),
3. appends the office, time, reference, and `bzz://<hash>` to the reply (deterministically,
   so the verifiable hash is always present).

Bee dev mode exposes two APIs: the data API (`:1633`, `/bytes` upload and download) and the
debug API (`:1635`, `/stamps`). A postage stamp is bought once and reused.

Verify a confirmation by its hash: `GET http://localhost:1633/bytes/<hash>` returns the exact
bytes. Because the address is the content hash, the file cannot be altered under the same
hash. The citizen and the office read the same hash and get the identical, PII-free proof.
Dev mode is local; a funded node would make the hash retrievable from any public Swarm gateway.

## Session mapping (multi-user)

```
Status user 0xABC (Alice)  ->  session "status-0xABC"  ->  own memory/context
Status user 0xXYZ (Bob)    ->  session "status-0xXYZ"  ->  separate memory/context
```

The chat key is authenticated by the E2E protocol, which makes it a legitimate
identity anchor.

## Track / focus-area coverage

| Requirement | Satisfied by |
|---|---|
| Infrastructure / Public Infra | Status channel, censorship-resistant, edge-deployable |
| Real-World Blockchain Adoption | Swarm storage for tamper-proof, PII-free appointment confirmations |
| Decentralized AI | pluggable provider: Nebius today, a decentralized one later (FLock.io story) |
| Nebius track | all inference runs on Token Factory |

## Verified against a live node (v10.31.0)

All shapes below were confirmed end-to-end with a real message from the Status app:

1. `CreateAccountAndLogin` required fields: `rootDataDir`, `displayName`,
   `password`, `customizationColor`, plus `wakuV2Fleet: status.prod`.
2. Chat key: `settings_getSettings` returns `public-key` (starts with `0x04`). The
   shareable form comes from `CompressPublicKey` (a `zQ3sh` code).
3. Incoming messages produce the signal `messages.new`. Read them with
   `wakuext_chatMessages(chatId, "", limit)`, which returns
   `messages[]{id, from, text, contentType, contactRequestState}`.
4. A contact request arrives as `contentType 11` with `contactRequestState 1`. Accept
   it with `wakuext_acceptContactRequest({id})`. Reply with
   `wakuext_sendChatMessage({chatId, text, contentType: 1})`.

## Repo layout

```
.
├── README.md                # project overview, quickstart
├── ARCHITECTURE.md          # this file
├── .env                     # secrets (gitignored)
├── status/                  # the Status node
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── bootstrap.py         # create bot account, read chat key
│   ├── requirements.txt
│   └── README.md
├── bridge/                  # Status-to-LLM bridge
│   ├── bridge.py            # signals listener, reserve_appointment tool
│   ├── swarm.py             # store/read confirmations on Swarm
│   └── requirements.txt
├── swarm/                   # Bee node (dev mode) for Swarm storage
│   └── docker-compose.yml
├── tools/                   # dev utilities
│   ├── nebius_toolcall_test.py
│   └── requirements.txt
└── slides/                  # Marp pitch deck
    ├── deck.md
    └── assets/              # Status, Nebius logos
```
