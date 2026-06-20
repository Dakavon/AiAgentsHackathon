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

import json
import os
import threading
import time

import requests
import websocket  # websocket-client
from dotenv import load_dotenv
from openai import OpenAI

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
    "conversational 'Ämterservice') reachable over the Status messenger. You help "
    "residents navigate "
    "municipal and government services such as registering a residence, ID and "
    "passport, vehicle registration, business registration, certificates and "
    "permits. For a request, name the responsible office, the documents needed, "
    "any fees and processing time, and how to book an appointment. Reply in the "
    "user's language. Be concrete and step-by-step. Ask only for the information "
    "needed to point the person to the right service. Keep replies short and "
    "actionable."
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
def ask_llm(session_id: str, user_text: str) -> str:
    if LLM_MODE == "hermes":
        resp = _hermes.chat.completions.create(
            model="hermes",
            messages=[{"role": "user", "content": user_text}],
            extra_headers={"X-Hermes-Session-Id": f"status-{session_id}"},
        )
        return resp.choices[0].message.content or ""

    msgs = _history.setdefault(session_id, [{"role": "system", "content": SYSTEM_PROMPT}])
    msgs.append({"role": "user", "content": user_text})
    resp = _llm.chat.completions.create(model=NEBIUS_MODEL, messages=msgs)
    answer = resp.choices[0].message.content or ""
    msgs.append({"role": "assistant", "content": answer})
    if len(msgs) > 21:  # cap rolling history
        _history[session_id] = [msgs[0]] + msgs[-20:]
    return answer


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
