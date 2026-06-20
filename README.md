# Amtomat

*The self-service public office in your messenger.*

**Amtomat** (Amt + Automat) is a private AI agent for public administration, reachable
over the decentralized **Status** messenger, with no phone number, no KYC, and
end-to-end encryption. You message your own agent like any contact, and it does not just
answer: it acts. Ask *"I lost my passport, how do I get a new one?"* and Amtomat names
the office and the documents, **reserves an appointment for you**, and stores a
tamper-proof, privacy-preserving confirmation on **Swarm**. Inference runs on
**Nebius Token Factory**.

Why Status? To reach your own agent privately, the usual channels fall short: Signal
needs its own phone number, Telegram is unencrypted and centralized. The Status bridge
is a decentralized, encrypted, no-phone-number channel to the agent.

Hackathon tracks: **Infrastructure** (the Status bridge) and **BGA** (public-administration
agent, Swarm confirmations, decentralized AI). Powered by **Nebius**.

## How it works

```
Status app ──Waku P2P──► status-go ──► Bridge ──► Nebius (Llama-3.3-70B)
   ▲  no SIM, E2E         (Docker)        │         inference + tool-calling
   └──────── reply ◄───────────────────────┘
                                          │  tool: reserve_appointment
                                          └──► Bee node ──► Swarm (confirmation hash)
```

The bridge listens for incoming messages, auto-accepts contact requests, maps each
sender's chat key to its own LLM session, and replies via the Status node. When the
agent reserves an appointment, it stores a data-minimal confirmation on Swarm and
appends the verifiable hash to the reply. See [ARCHITECTURE.md](ARCHITECTURE.md) for the
full design and verified RPC shapes.

## Components

| Dir | What |
|---|---|
| [status/](status/) | Headless Status node (`status-go` v10.31.0) in Docker, the messaging channel. |
| [bridge/](bridge/) | Python bridge: Status signals to Nebius (or Hermes), the `reserve_appointment` tool, and `swarm.py`. |
| [swarm/](swarm/) | Bee node (dev mode) that stores appointment confirmations on Swarm. |
| [tools/](tools/) | Dev utilities, e.g. the Nebius tool-calling smoke test. |
| [slides/](slides/) | Marp pitch deck. |

## Quickstart

```bash
# 0. secrets
cp .env.example .env        # then fill in NEBIUS_API_KEY

# 1. verify the LLM (optional)
pip install -r tools/requirements.txt
python tools/nebius_toolcall_test.py

# 2. start the Status node
cd status && docker compose up -d
pip install -r requirements.txt
python bootstrap.py          # creates the bot account, prints its chat key (zQ3sh code)
cd ..

# 3. start the Swarm (Bee) node
docker compose -f swarm/docker-compose.yml up -d

# 4. start the bridge
cd bridge && pip install -r requirements.txt
python bridge.py             # DM the bot from the Status app
cd ..
```

Add the bot in the Status app via its `zQ3sh` chat key (printed by `bootstrap.py`), send
a contact request and a message, and the agent replies. Verify a stored confirmation
with `curl http://localhost:1633/bytes/<hash>`.

## Configuration (.env, gitignored)

| Var | Purpose |
|---|---|
| `NEBIUS_API_KEY` | Nebius Token Factory key (required) |
| `LLM_MODEL` | default `meta-llama/Llama-3.3-70B-Instruct` |
| `LLM_BASE_URL` | default Nebius Token Factory; any OpenAI-compatible endpoint works |
| `LLM_MODE` | `direct` (bridge to Nebius) or `hermes` (bridge to Hermes to Nebius) |
| `STATUS_BACKEND_ADDR` | default `localhost:12345` |
| `BEE_API` / `BEE_DEBUG_API` | default `localhost:1633` / `localhost:1635` |

## Status

- ✅ Nebius Token Factory: tool-calling verified (`Llama-3.3-70B-Instruct`)
- ✅ status-go v10.31.0 built and running on the production Status network
- ✅ Full round-trip proven: real Status app to AI reply, multilingual, deduped
- ✅ Swarm appointment confirmation: the agent reserves a slot and stores a verifiable,
  PII-free confirmation, with the hash returned in the reply (Bee dev node)
- ⬜ **Hermes agent layer**: per-user memory and richer tool-calling (bridge `hermes` mode)
- ⬜ Real funded Bee node (public Swarm), more offices, demo polish

See **[plan.md](plan.md)** for the live roadmap, milestones and decisions log.

### Planned: Hermes agent layer

Today the bridge calls Nebius directly (`direct` mode). The planned `hermes` mode puts
the **Hermes Agent** between the bridge and Nebius so the agent gains per-user memory
(keyed by `X-Hermes-Session-Id`, the sender's Status chat key) and richer tool-calling.
Nebius stays the underlying LLM, and because the bridge already speaks the
OpenAI-compatible API, switching `LLM_MODE` from `direct` to `hermes` is a configuration
change.

> Pinned to status-go **v10.31.0** on purpose: newest tag that builds without the
> Nim/libsds toolchain (added in v10.32.0). See [status/Dockerfile](status/Dockerfile).

## Reference

- Hackathon: [AI Agents Hackathon 2026](https://luma.com/ai-agents-hackathon-2026)
