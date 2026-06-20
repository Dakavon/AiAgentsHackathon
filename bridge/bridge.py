#!/usr/bin/env python3
"""
Status <-> Nebius/Hermes bridge
===============================

Connects the headless status-backend node to an LLM so a Status-app user can
chat 1:1 with an AI public-services assistant.

All Status RPCs/shapes below are VERIFIED against a live v10.31.0 node + a real
message from the Status desktop app (not guessed):

  incoming trigger : signal {"type": "messages.new", "event": {"chats":[...]}}
  read messages    : wakuext_chatMessages(chatId, "", limit)
                       -> result.messages[] {id, from, text, contentType,
                                             contactRequestState, outgoing}
  contact request  : arrives as contentType 11, contactRequestState 1
  accept it        : wakuext_acceptContactRequest({"id": <messageId>})
  send reply       : wakuext_sendChatMessage({chatId, text, contentType: 1})
  chatId (1:1)     : the peer's public key (0x04...), also used as session id

LLM modes (LLM_MODE in .env):
  "direct" : call Nebius Token Factory directly (persona + per-session history)
  "hermes" : call Hermes' OpenAI API (X-Hermes-Session-Id = peer key)

Run (node must be up):
    pip install -r requirements.txt
    python bridge.py
"""

import hashlib
import json
import os
import secrets
import threading
import time

import requests
import websocket  # websocket-client
from dotenv import load_dotenv
from openai import OpenAI

import swarm  # local module (bridge/swarm.py)

# load repo-root .env (NEBIUS_API_KEY) as well as a local one if present
_here = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_here, "..", ".env"))
load_dotenv()

# --- Status node ----------------------------------------------------------
ADDR = os.environ.get("STATUS_BACKEND_ADDR", "localhost:12345")
HTTP = f"http://{ADDR}"
WS = f"ws://{ADDR}/signals"

# Status ChatMessage content types (verified): 1 = plain text, 11 = contact
# request (carries the first message), 15 = system "sent you a contact request".
CT_TEXT = 1
CT_CONTACT_REQUEST = 11
CONTACT_REQUEST_PENDING = 1

# --- LLM ------------------------------------------------------------------
LLM_MODE = os.environ.get("LLM_MODE", "direct")
NEBIUS_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
NEBIUS_API_KEY = os.environ.get("NEBIUS_API_KEY", "")
NEBIUS_MODEL = os.environ.get("LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
HERMES_BASE_URL = os.environ.get("HERMES_BASE_URL", "http://localhost:8080/v1/")
HERMES_API_KEY = os.environ.get("HERMES_API_KEY", "hermes")

SYSTEM_PROMPT = (
    "You are Amtomat, a multilingual public-administration assistant (a "
    "conversational 'Ämterservice') reachable over the Status messenger. First and "
    "foremost, have a normal, helpful conversation about municipal and government "
    "services: the responsible office, required documents, fees, processing times, "
    "opening hours, and how procedures work, for things like residence registration, "
    "ID and passport, vehicle registration, business registration, certificates and "
    "permits. Answer questions directly. "
    "Only use the reserve_appointment tool when the person actually wants to start a "
    "procedure that needs an in-person visit, or explicitly asks for an appointment. "
    "For general questions, just answer; you may offer to book an appointment instead "
    "of booking one. When you do reserve, do not write the appointment time, the "
    "reference code, or a confirmation link yourself; the system appends those. "
    "Reply in the user's language. Be concrete and helpful."
)

_history: dict[str, list[dict]] = {}
_llm = OpenAI(base_url=NEBIUS_BASE_URL, api_key=NEBIUS_API_KEY) if LLM_MODE == "direct" else None
_hermes = OpenAI(base_url=HERMES_BASE_URL, api_key=HERMES_API_KEY) if LLM_MODE == "hermes" else None

_seen: set[str] = set()          # processed message ids (dedupe)
_bot_key: str | None = None      # our own pubkey, to skip our echoes


# --- Status RPC -----------------------------------------------------------
def rpc(method: str, params: list | None = None) -> dict:
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    r = requests.post(f"{HTTP}/statusgo/CallRPC", json=body, timeout=60)
    try:
        return r.json()
    except ValueError:
        return {"raw": r.text}


def get_bot_key() -> str | None:
    res = rpc("settings_getSettings").get("result") or {}
    return res.get("public-key") if isinstance(res, dict) else None


def prime_seen() -> None:
    """Mark existing messages as seen so a (re)start doesn't replay backlog."""
    chats = rpc("wakuext_chats").get("result") or []
    n = 0
    for c in chats:
        cid = c.get("id") if isinstance(c, dict) else None
        if not cid:
            continue
        for m in chat_messages(cid, limit=50):
            if m.get("id"):
                _seen.add(m["id"])
                n += 1
    print(f"primed {n} existing messages as seen (no backlog replay)")


def chat_messages(chat_id: str, limit: int = 10) -> list[dict]:
    res = rpc("wakuext_chatMessages", [chat_id, "", limit]).get("result") or {}
    return res.get("messages") or []


def accept_contact_request(message_id: str) -> None:
    print(f"[contact] accepting request {message_id[:12]}")
    rpc("wakuext_acceptContactRequest", [{"id": message_id}])


def send_message(chat_id: str, text: str) -> None:
    print(f"[send] -> {chat_id[:14]}: {text[:70]!r}")
    rpc("wakuext_sendChatMessage", [{"chatId": chat_id, "text": text, "contentType": CT_TEXT}])


# --- LLM ------------------------------------------------------------------
# --- agent tools --------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "reserve_appointment",
            "description": (
                "Reserve an in-person appointment at the responsible public office and "
                "store a verifiable, privacy-preserving confirmation on Swarm. Call this "
                "when the user needs to appear in person (for example a lost passport or "
                "ID, or a residence registration). Pick a concrete office and a "
                "near-future slot."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "office": {
                        "type": "string",
                        "description": "Responsible office, e.g. 'Buergeramt Mitte'",
                    },
                    "datetime": {
                        "type": "string",
                        "description": "Date and time, ISO 8601, e.g. 2026-07-01T10:00",
                    },
                },
                "required": ["office", "datetime"],
            },
        },
    }
]

# The booking tool is only offered when the user shows booking intent, so normal
# questions stay a normal conversation instead of always booking an appointment.
BOOKING_KEYWORDS = (
    "termin", "appointment", "buchen", "book", "reservier", "reserve",
    "schedule", "vereinbar",
)


def reserve_appointment(session_id: str, office: str, when: str) -> dict:
    """Build a data-minimal confirmation, store it on Swarm, return the result."""
    subject = hashlib.sha256(session_id.encode()).hexdigest()
    reference = "APT-" + secrets.token_hex(3).upper()
    confirmation = {
        "type": "appointment-confirmation",
        "office": office or "Buergeramt",
        "datetime": when,
        "reference": reference,
        "subject": f"sha256:{subject}",  # anonymous anchor, no PII
        "issuedBy": "Amtomat",
        "issuedAt": int(time.time()),
    }
    try:
        ref = swarm.store_confirmation(confirmation)
    except Exception as e:  # noqa: BLE001
        print(f"[swarm] store failed: {e}")
        return {"status": "error", "error": str(e)}
    print(f"[swarm] confirmation {reference} stored -> {ref}")
    return {
        "status": "reserved",
        "office": confirmation["office"],
        "datetime": when,
        "reference": reference,
        "swarm_reference": ref,
        "swarm_url": f"bzz://{ref}",
    }


def _run_tool(session_id: str, tc) -> dict:
    name = tc.function.name
    try:
        args = json.loads(tc.function.arguments or "{}")
    except json.JSONDecodeError:
        args = {}
    if name == "reserve_appointment":
        return reserve_appointment(session_id, args.get("office", ""), args.get("datetime", ""))
    return {"error": f"unknown tool {name}"}


def ask_llm(session_id: str, user_text: str) -> str:
    if LLM_MODE == "hermes":
        resp = _hermes.chat.completions.create(
            model="hermes",
            messages=[{"role": "user", "content": user_text}],
            extra_headers={"X-Hermes-Session-Id": f"status-{session_id}"},
        )
        return resp.choices[0].message.content or ""

    history = _history.setdefault(session_id, [{"role": "system", "content": SYSTEM_PROMPT}])
    # work on a copy so tool-call/result pairs do not pollute the rolling history
    msgs = list(history) + [{"role": "user", "content": user_text}]
    # offer the booking tool only on booking intent; otherwise it is a plain chat
    wants_booking = any(k in user_text.lower() for k in BOOKING_KEYWORDS)
    final = ""
    reserved = None
    for _ in range(4):  # allow a couple of tool rounds
        kwargs = {"model": NEBIUS_MODEL, "messages": msgs}
        if wants_booking:
            kwargs["tools"] = TOOLS
            kwargs["tool_choice"] = "auto"
        resp = _llm.chat.completions.create(**kwargs)
        m = resp.choices[0].message
        if not m.tool_calls:
            final = m.content or ""
            break
        msgs.append(m.model_dump())
        for tc in m.tool_calls:
            result = _run_tool(session_id, tc)
            if isinstance(result, dict) and result.get("status") == "reserved":
                reserved = result
            msgs.append(
                {"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)}
            )

    # Deterministically append the appointment confirmation so the verifiable Swarm
    # reference is always present, regardless of what the model chose to write.
    if reserved:
        final = (
            final.rstrip()
            + "\n\n"
            + f"📅 {reserved['office']}, {reserved['datetime']}\n"
            + f"🔖 {reserved['reference']}\n"
            + f"🐝 Confirmation on Swarm: {reserved['swarm_url']}"
        )

    # persist only a clean user+assistant turn
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": final})
    if len(history) > 21:
        _history[session_id] = [history[0]] + history[-20:]
    return final


# --- core: process one chat's recent messages -----------------------------
def process_chat(chat_id: str) -> None:
    for m in chat_messages(chat_id):
        mid = m.get("id")
        if not mid or mid in _seen:
            continue
        # skip our own / outgoing messages
        if m.get("outgoing") or (m.get("from") and m.get("from") == _bot_key):
            _seen.add(mid)
            continue

        ctype = m.get("contentType")
        sender = m.get("from")
        text = (m.get("text") or "").strip()

        # auto-accept incoming contact requests (Status needs mutual contact)
        if ctype == CT_CONTACT_REQUEST and m.get("contactRequestState") == CONTACT_REQUEST_PENDING:
            accept_contact_request(mid)

        # treat plain text AND the message carried with a contact request as queries
        if ctype in (CT_TEXT, CT_CONTACT_REQUEST) and text:
            _seen.add(mid)
            print(f"[recv] <- {sender[:14]}: {text[:70]!r}")
            try:
                reply = ask_llm(sender, text)
            except Exception as e:  # noqa: BLE001
                reply = f"(assistant error: {e})"
            send_message(sender, reply)
        else:
            _seen.add(mid)  # system / other content types: ignore


# --- signal handling ------------------------------------------------------
def handle_signal(sig: dict) -> None:
    if sig.get("type") != "messages.new":
        return
    event = sig.get("event") or {}
    chat_ids = {c.get("id") for c in (event.get("chats") or []) if c.get("id")}
    for m in (event.get("messages") or []):
        if m.get("localChatId"):
            chat_ids.add(m["localChatId"])
    for cid in chat_ids:
        try:
            process_chat(cid)
        except Exception as e:  # noqa: BLE001
            print(f"!! process_chat({cid[:12]}) error: {e}")


def on_message(_ws, message: str) -> None:
    try:
        sig = json.loads(message)
    except json.JSONDecodeError:
        return
    try:
        handle_signal(sig)
    except Exception as e:  # noqa: BLE001
        print(f"!! handler error: {e}")


def main() -> None:
    global _bot_key
    if LLM_MODE == "direct" and not NEBIUS_API_KEY:
        raise SystemExit("NEBIUS_API_KEY missing (.env) for direct mode")

    _bot_key = get_bot_key()
    print(f"LLM_MODE={LLM_MODE}  model={NEBIUS_MODEL if LLM_MODE=='direct' else 'hermes'}")
    print(f"bot key: {(_bot_key or '?')[:18]}  status={WS}")
    prime_seen()
    print("Bridge live. DM the bot from the Status app.\n")

    while True:
        try:
            websocket.WebSocketApp(WS, on_message=on_message).run_forever()
        except Exception as e:  # noqa: BLE001
            print(f"!! ws disconnected: {e}. Reconnecting in 3s")
        time.sleep(3)


if __name__ == "__main__":
    main()
