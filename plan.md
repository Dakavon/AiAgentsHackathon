# Amtomat: Project Plan & Status

**Amtomat** (Amt + Automat). An AI public-administration assistant reachable
over the decentralized Status messenger, powered by Nebius, with decentralized proof
of completed steps on Swarm.

_Last updated: 2026-06-20_

## TL;DR

The end-to-end demo works. A real Status app message reaches Amtomat, the agent answers
(Nebius, Llama-3.3-70B), and when an in-person visit is needed it reserves an appointment
and stores a verifiable, PII-free confirmation on Swarm, returning the hash in the reply.
Multilingual, auto-accepted contacts, per-user sessions. Remaining work is the **Hermes
agent layer**, a **real Swarm node**, and **demo polish**.

## Milestones

| # | Milestone | Status |
|---|---|---|
| 1 | Nebius Token Factory: tool-calling verified (`Llama-3.3-70B-Instruct`) | ✅ done |
| 2 | status-go v10.31.0 built, node live on `status.prod`, bot identity and `zQ3sh` code | ✅ done |
| 3 | Real Status-app signal shapes verified (messages.new, chatMessages, accept, send) | ✅ done |
| 4 | Bridge live: Status to Nebius (direct), auto-accept, session mapping, dedupe | ✅ done |
| 5 | Repo cleanup, docs, rebrand to Amtomat, slides, git pushed | ✅ done |
| 6 | Hermes agent layer (memory, tool-calling) | ⬜ planned |
| 7 | Swarm appointment confirmation (`reserve_appointment` tool, Bee dev) | ✅ done |
| 8 | Demo flow and pitch | 🔧 in progress |

## Workstreams

### 1 to 4. Channel, LLM, Bridge (DONE)
- `status/` Docker image builds (`make status-backend`, Go 1.24 with protobuf toolchain).
- Node runs headless on the production Status network. The bot account persists in a volume.
- `bridge/bridge.py` listens on the signals websocket, auto-accepts contact requests,
  maps each sender's chat key to an LLM session, replies via `wakuext_sendChatMessage`.
- Two modes exist in code: `direct` (Nebius, current) and `hermes` (planned).

### 5. Repo cleanup, docs, rebrand (DONE)
- [x] moved dev test to `tools/`, added README, reframed to **Amtomat** (Amt + Automat)
- [x] all code comments in English, natural punctuation (no em-dash/ellipsis slop)
- [x] real Status and Nebius logos in the slides flow
- [x] committed in build order and pushed to the GitHub remote; `.env` stays untracked

### 6. Hermes agent layer (PLANNED)
Put Hermes between the bridge and Nebius (`LLM_MODE=hermes`). It adds:
- **per-user memory** via `X-Hermes-Session-Id`, the sender's Status chat key,
- **tool-calling** for real service lookups (a municipal *Dienstleistungen* catalog)
  and to trigger the Swarm confirmation.

Nebius stays the underlying model. The bridge already speaks the OpenAI-compatible API,
so this is a configuration switch plus running a Hermes instance, not a rewrite.

### 7. Swarm appointment confirmation (DONE)
When the agent reserves an appointment (LLM `reserve_appointment` tool-call), the bridge
writes a confirmation to Swarm and appends the content hash to the reply. Both the citizen
(over Status) and the office read the same content-addressed file to verify it.
- **Bee node in dev mode**, pinned to `ethersphere/bee:1.18.2` (Bee 2.x removed `dev`).
  Free postage stamps, no funding. A real funded node is a config switch.
- `bridge/swarm.py`: `store_confirmation(dict) -> reference` via `POST /bytes`; a stamp is
  bought once on the debug API (`:1635`) and reused; data API is `:1633`.
- Trigger: the `reserve_appointment` tool. The bridge appends office, datetime, reference,
  and `bzz://<hash>` deterministically, so the hash is always present.
- File (Option 1, no reason/PII): `type`, `office`, `datetime`, `reference`,
  `subject` = `sha256(chat key)`, `issuedBy`, `issuedAt`.
- Verify: `GET http://localhost:1633/bytes/<hash>` returns the exact bytes.

### 8. Demo and pitch (PLANNED)
- Show two users chatting concurrently (separate sessions), multilingual replies.
- Show the decentralization angle (Nebius today, decentralized AI as the direction).
- Show a Swarm confirmation hash being created and retrieved.
- Tune the pitch to the judges: Glenn (public infra, government scale) and Tiffany
  (decentralized AI).

## Track coverage (BGA, Nebius)

| Requirement | How |
|---|---|
| Infrastructure / Public Infra | Status channel, censorship-resistant, edge-deployable; Ämterservice scales per municipality |
| Real-World Blockchain Adoption | Swarm decentralized storage for tamper-proof completion confirmations |
| Decentralized AI | pluggable provider (Nebius today, a decentralized one later); Hermes agent layer |
| Nebius track | all inference on Token Factory |

## Decisions log

- **status-go pinned to v10.31.0.** Newest tag that builds without the Nim/libsds
  toolchain (introduced in v10.32.0). Keeps the build to Go, cgo, and protobuf.
- **Model `meta-llama/Llama-3.3-70B-Instruct`.** Verified reliable tool-calling, fast.
  (`Qwen3-235B-Instruct` also passed, kept as a heavier multilingual option.)
- **Bridge `direct` mode now, Hermes later.** Get a working channel first; Hermes is a
  config switch on top.
- **Swarm (not EAS) for the decentralized proof.** Decentralized storage fits the
  decentralized-web stack (Status/Waku with Swarm) and avoids per-chain wallet and gas setup.
- **Swarm via Bee dev mode for the demo.** Free postage stamps, no funding step; a real
  node is a config switch.
- **Confirmation trigger: LLM tool-call.** Fits the agent story and shows Nebius
  tool-calling live.
- **Swarm confirmation = appointment confirmation, Option 1 (data-minimal).** Stores
  office, datetime, reference, and a pubkey hash. No reason/service, no PII. Both citizen
  and office verify via the same Swarm hash without revealing details.
- **Use case Ämterservice (not refugee-specific).** Broader, scales with any
  municipality or government, stronger public-infrastructure story.
- **Bee pinned to 1.18.2.** Bee 2.x removed the `dev` command; 1.18.2 keeps it (free
  stamps). Stamps live on the debug API (`:1635`), data on `:1633`; we use `/bytes`.
- **Deterministic confirmation footer.** The bridge appends the appointment and Swarm hash
  itself instead of relying on the model to include them.
- **Bot renamed to Amtomat** in place via `wakuext_setDisplayName` (chat key unchanged).
- **Git: committed in build order and pushed** to the GitHub remote; `.env` stays untracked.
- **Writing style.** Natural punctuation in docs and replies, no em-dash/ellipsis slop.

## Open questions

- **Read access:** the confirmation is plaintext on Swarm, readable by anyone who has the
  hash (it is PII-free by design). For true confidentiality (only the user and the office)
  we would enable Swarm encryption (`Swarm-Encrypt`) or ACT.
- When to move from Bee dev mode to a real funded node (xBZZ/xDAI on Gnosis).
- Demo script details: which two languages to showcase.
