# Project Plan & Status

**Status-native Ämterservice Agent.** An AI public-administration assistant reachable
over the decentralized Status messenger, powered by Nebius, with decentralized proof
of completed steps on Swarm.

_Last updated: 2026-06-20_

## TL;DR

The core pipeline works end-to-end. A real Status app message reaches the bot, gets
answered by an LLM (Nebius, Llama-3.3-70B) with an Ämterservice persona, and the reply
comes back: multilingual, with auto-accepted contacts and per-user sessions. Remaining
work is the **Hermes agent layer**, **Swarm confirmations**, and the **demo and pitch**.

## Milestones

| # | Milestone | Status |
|---|---|---|
| 1 | Nebius Token Factory: tool-calling verified (`Llama-3.3-70B-Instruct`) | ✅ done |
| 2 | status-go v10.31.0 built, node live on `status.prod`, bot identity and `zQ3sh` code | ✅ done |
| 3 | Real Status-app signal shapes verified (messages.new, chatMessages, accept, send) | ✅ done |
| 4 | Bridge live: Status to Nebius (direct), auto-accept, session mapping, dedupe | ✅ done |
| 5 | Repo cleanup, docs, git | 🔧 in progress |
| 6 | Hermes agent layer (memory, tool-calling) | ⬜ planned |
| 7 | Swarm appointment confirmation | ⬜ planned |
| 8 | Demo flow and pitch (all BGA focus areas, Nebius) | ⬜ planned |

## Workstreams

### 1 to 4. Channel, LLM, Bridge (DONE)
- `status/` Docker image builds (`make status-backend`, Go 1.24 with protobuf toolchain).
- Node runs headless on the production Status network. The bot account persists in a volume.
- `bridge/bridge.py` listens on the signals websocket, auto-accepts contact requests,
  maps each sender's chat key to an LLM session, replies via `wakuext_sendChatMessage`.
- Two modes exist in code: `direct` (Nebius, current) and `hermes` (planned).

### 5. Repo cleanup and git (in progress)
- [x] move dev test to `tools/`, add `README.md`, reframe use case to Ämterservice
- [x] all code comments in English, no refugee-specific content
- [x] `ARCHITECTURE.md` updated (Swarm, `tools/`, verified shapes, direct/Hermes)
- [x] natural punctuation in docs (no em-dash/ellipsis "agent slop")
- [ ] git is on hold by request. No remote (removed). Commit locally when asked;
      `.env` must stay untracked.

### 6. Hermes agent layer (PLANNED)
Put Hermes between the bridge and Nebius (`LLM_MODE=hermes`). It adds:
- **per-user memory** via `X-Hermes-Session-Id`, the sender's Status chat key,
- **tool-calling** for real service lookups (a municipal *Dienstleistungen* catalog)
  and to trigger the Swarm confirmation.

Nebius stays the underlying model. The bridge already speaks the OpenAI-compatible API,
so this is a configuration switch plus running a Hermes instance, not a rewrite.

### 7. Swarm appointment confirmation (PLANNED)
When an appointment is booked (the agent recognizes it via an LLM tool-call), the bridge
writes an **appointment confirmation** to Swarm and returns the content hash. Both the
citizen (over Status) and the office can read the same content-addressed file to verify
the appointment, without it revealing personal details. Communication stays on Status;
Swarm is only the confirmation artifact.
- Run a **Bee node** in dev mode for the demo (free postage stamps). A real funded node
  is a later config switch.
- `swarm.py`: `store_confirmation(dict) -> reference` via `POST /bzz`.
- Trigger: an **LLM tool-call** (`confirm_appointment`). The bridge exposes the tool to
  Nebius and acts on the tool call (works in `direct` mode already).
- File (data-minimal, **Option 1**, no reason/PII): `type`, `office`, `datetime`,
  `reference`, `subject` = `sha256(Status pubkey)`, `issuedBy`, `issuedAt`. The office
  already knows the reason from its own booking, so it is not stored.

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
- **Git on hold, local-only.** Remote removed by request; commit only when asked.
- **Writing style.** Natural punctuation in docs and replies, no em-dash/ellipsis slop.

## Open questions

- When (if ever) to move from Bee dev mode to a real funded node (xBZZ/xDAI on Gnosis).
- Demo script details: which two languages to showcase, exact completed-step example.
