# Status-native Public-Administration Agent

An AI **public-administration assistant** (a conversational *Ämterservice*) reachable
over the decentralized **Status** messenger, with no phone number, no KYC, and
end-to-end encryption. Instead of browsing a municipality's A-Z list of services,
residents just ask in natural language, in their own language: which office is
responsible, the documents required, fees, processing time, and how to book an
appointment, for procedures like registering a residence, ID/passport, vehicle
registration, business registration, certificates and permits. Inference runs on
**Nebius Token Factory**. The bot stores tamper-proof completion confirmations on
decentralized storage (**Swarm**, planned).

Hackathon tracks: **Infrastructure**, **BGA** (public infra, real-world Web3,
decentralized AI), and **Nebius**.

## How it works

```
Status app ──Waku P2P──► status-go (Docker) ──► Bridge ──► Nebius (Llama-3.3-70B)
   ▲  no SIM, E2E                                  │          tool-calling proven
   └──────────────── AI reply ◄────────────────────┘
```

The bridge listens for incoming messages, auto-accepts contact requests, maps
each sender's chat key to its own LLM session, and replies via the Status node.
See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and verified RPC shapes.

## Components

| Dir | What |
|---|---|
| [status/](status/) | Headless Status node (`status-go` v10.31.0) in Docker, the messaging channel. See [status/README.md](status/README.md). |
| [bridge/](bridge/) | Python bridge: Status signals to LLM (Nebius direct, or Hermes). |
| [tools/](tools/) | Dev utilities, e.g. the Nebius tool-calling smoke test. |

## Quickstart

```bash
# 0. secrets
cp .env.example .env        # then fill in NEBIUS_API_KEY

# 1. verify the LLM (optional but recommended)
pip install -r tools/requirements.txt
python tools/nebius_toolcall_test.py     # -> which models tool-call reliably

# 2. start the Status node
cd status
docker compose up -d
pip install -r requirements.txt
python bootstrap.py          # creates the bot account, prints its chat key (zQ3sh code)

# 3. start the bridge (talks to node + Nebius)
cd ../bridge
pip install -r requirements.txt
python bridge.py             # DM the bot from the Status app

cd ..
```

Then add the bot in the Status app via its `zQ3sh` chat key (printed by
`bootstrap.py`), send a contact request and a message, and the assistant replies.

## Configuration (.env, gitignored)

| Var | Purpose |
|---|---|
| `NEBIUS_API_KEY` | Nebius Token Factory key (required) |
| `LLM_MODEL` | default `meta-llama/Llama-3.3-70B-Instruct` |
| `LLM_BASE_URL` | default Nebius Token Factory; any OpenAI-compatible endpoint works |
| `LLM_MODE` | `direct` (bridge to Nebius) or `hermes` (bridge to Hermes to Nebius) |
| `STATUS_BACKEND_ADDR` | default `localhost:12345` |

## Status

- ✅ Nebius Token Factory: tool-calling verified (`Llama-3.3-70B-Instruct`)
- ✅ status-go v10.31.0 built and running on the production Status network
- ✅ Full round-trip proven: real Status app to AI reply, multilingual, deduped
- ⬜ **Hermes agent layer**: per-user memory and tool-calling (bridge `hermes` mode).
  The bridge is provider-agnostic, so this is a config switch, not a rewrite.
- ⬜ Swarm confirmation storage (decentralized proof of completed steps)
- ⬜ Demo flow and pitch

See **[plan.md](plan.md)** for the live roadmap, milestones and decisions log.

### Planned: Hermes agent layer

Today the bridge calls Nebius directly (`direct` mode). The planned `hermes` mode
puts the **Hermes Agent** between the bridge and Nebius so the assistant gains:

- **per-user memory** keyed by `X-Hermes-Session-Id`, the sender's Status chat key,
- **tool-calling** for real service lookups (e.g. a municipal *Dienstleistungen*
  catalog) and for triggering the Swarm confirmation,

while Nebius stays the underlying LLM. Because the bridge already speaks the
OpenAI-compatible API, switching `LLM_MODE` from `direct` to `hermes` is a
configuration change.

> Pinned to status-go **v10.31.0** on purpose: newest tag that builds without the
> Nim/libsds toolchain (added in v10.32.0). See [status/Dockerfile](status/Dockerfile).

## Reference

- Hackathon: [AI Agents Hackathon 2026](https://luma.com/ai-agents-hackathon-2026)
