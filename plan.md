# Project Plan & Status

**Status-native Ämterservice Agent** — an AI public-administration assistant reachable
over the decentralized Status messenger, powered by Nebius, with decentralized proof
of completed steps on Swarm.

_Last updated: 2026-06-20_

## TL;DR

The core pipeline works end-to-end: a real Status app message reaches the bot, gets
answered by an LLM (Nebius / Llama-3.3-70B) with an Ämterservice persona, and the reply
comes back — multilingual, with auto-accepted contacts and per-user sessions. Remaining
work is the **Hermes agent layer**, **Swarm confirmations**, and the **demo + pitch**.

## Milestones

| # | Milestone | Status |
|---|---|---|
| 1 | Nebius Token Factory — tool-calling verified (`Llama-3.3-70B-Instruct`) | ✅ done |
| 2 | status-go v10.31.0 built, node live on `status.prod`, bot identity + `zQ3sh…` code | ✅ done |
| 3 | Real Status-app signal shapes verified (messages.new, chatMessages, accept, send) | ✅ done |
| 4 | Bridge live: Status ↔ Nebius (direct), auto-accept, session mapping, dedupe | ✅ done |
| 5 | Repo cleanup + docs + `git init` | 🔧 in progress |
| 6 | Hermes agent layer (memory + tool-calling) | ⬜ planned |
| 7 | Swarm confirmation storage | ⬜ planned |
| 8 | Demo flow + pitch (all BGA focus areas + Nebius) | ⬜ planned |

## Workstreams

### 1–4. Channel + LLM + Bridge — DONE
- `status/` Docker image builds (`make status-backend`, Go 1.24 + protobuf toolchain).
- Node runs headless on the production Status network; bot account persists in a volume.
- `bridge/bridge.py` listens on the signals websocket, auto-accepts contact requests,
  maps each sender's chat key to an LLM session, replies via `wakuext_sendChatMessage`.
- Two modes exist in code: `direct` (Nebius, current) and `hermes` (planned).

### 5. Repo cleanup + git — IN PROGRESS
- [x] move dev test to `tools/`, add `README.md`, reframe use case to Ämterservice
- [x] all code comments in English; no refugee-specific content
- [x] `ARCHITECTURE.md` updated (Swarm, `tools/`, verified shapes, direct/Hermes)
- [ ] `git init` + first commit + add remote (`git@github.com:Dakavon/AiAgentsHackathon.git`)
      — **waiting for user go-ahead; `.env` must stay untracked**

### 6. Hermes agent layer — PLANNED
Put Hermes between the bridge and Nebius (`LLM_MODE=hermes`). Adds:
- **per-user memory** via `X-Hermes-Session-Id` = sender's Status chat key,
- **tool-calling** for real service lookups (municipal *Dienstleistungen* catalog) and
  to trigger the Swarm confirmation.
Nebius stays the underlying model. The bridge already speaks the OpenAI-compatible API,
so this is a configuration switch + running a Hermes instance, not a rewrite.

### 7. Swarm confirmation storage — PLANNED
After a completed step, the bridge stores a small, PII-free confirmation JSON on Swarm
and returns the content hash to the user (verifiable by any office/NGO later).
- Run a **Bee node** (dev mode for the demo → free postage stamps; real node = config switch).
- `swarm.py`: `store_confirmation(dict) -> reference` via `POST /bzz`.
- Trigger: Hermes tool-call (preferred) or an explicit user command.
- Stored: procedure, step, timestamp, **hash** of the Status pubkey, issuer. No PII.

### 8. Demo + pitch — PLANNED
- Show 2 users chatting concurrently (separate sessions), multilingual replies.
- Show the provider/decentralization angle (Nebius now ↔ decentralized AI story).
- Show a Swarm confirmation hash being created and retrieved.
- Pitch tuned to the judges: Glenn (public infra / government scale), Tiffany (decentralized AI).

## Track coverage (BGA + Nebius)

| Requirement | How |
|---|---|
| Infrastructure / Public Infra | Status channel, censorship-resistant, edge-deployable; Ämterservice scales per municipality |
| Real-World Blockchain Adoption | Swarm decentralized storage → tamper-proof completion confirmation |
| Decentralized AI | pluggable provider (Nebius ↔ decentralized); Hermes agent layer |
| Nebius track | all inference on Token Factory |

## Decisions log

- **status-go pinned to v10.31.0** — newest tag that builds without the Nim/libsds
  toolchain (introduced in v10.32.0). Keeps the build to Go + cgo + protobuf.
- **Model: `meta-llama/Llama-3.3-70B-Instruct`** — verified reliable tool-calling, fast.
  (`Qwen3-235B-Instruct` also passed; kept as a heavier multilingual option.)
- **Bridge `direct` mode now, Hermes later** — get a working channel first; Hermes is a
  config switch on top.
- **Swarm (not EAS) for the "decentralized proof"** — decentralized storage fits the
  decentralized-web stack (Status/Waku + Swarm) and avoids per-chain wallet/gas setup.
- **Use case: Ämterservice (not refugee-specific)** — broader, scales with any
  municipality/government; stronger public-infrastructure story.

## Open questions

- Swarm: Bee **dev mode** for the demo vs a **real funded node** (xBZZ/xDAI on Gnosis)?
- Confirmation **trigger**: Hermes tool-call vs explicit user command?
- Normalize Unicode punctuation (`—`, `…`) in docs to plain ASCII?
- When to **push** to the GitHub remote.
