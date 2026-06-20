#!/usr/bin/env python3
"""
status-backend bootstrap
========================

Creates the bot's Status account, logs in, starts the messenger, and prints the
bot's chat key (the public key users add as a contact).

Schemas below are taken from the v10.31.0 source (not guessed):
  - InitializeApplication      <- requests.InitializeApplication {dataDir, ...}
  - CreateAccountAndLogin      <- requests.CreateAccount (required: displayName,
                                  password, customizationColor, rootDataDir)
  - chat key                   <- CallRPC settings_getSettings -> "public-key"

Run (node must be up: `docker compose up -d`):
    pip install -r requirements.txt
    python bootstrap.py
"""

import json
import os
import threading
import time

import requests
import websocket  # websocket-client

ADDR = os.environ.get("STATUS_BACKEND_ADDR", "localhost:12345")
HTTP = f"http://{ADDR}"
WS = f"ws://{ADDR}/signals"

# Account config. RootDataDir is a path INSIDE the container (the mounted volume).
ROOT_DATA_DIR = os.environ.get("STATUS_ROOT_DATA_DIR", "/data")
PASSWORD = os.environ.get("STATUS_ACCOUNT_PASSWORD", "hackathon-demo-pw")
DISPLAY_NAME = os.environ.get("STATUS_DISPLAY_NAME", "Amtomat")
CUSTOMIZATION_COLOR = os.environ.get("STATUS_COLOR", "blue")
# Must match the fleet the real Status app uses, or 1:1 messages won't reach it.
WAKU_FLEET = os.environ.get("STATUS_FLEET", "status.prod")
KDF_ITERATIONS = int(os.environ.get("STATUS_KDF_ITERATIONS", "256000"))

_signals: list[dict] = []


def _on_signal(_ws, message: str) -> None:
    try:
        sig = json.loads(message)
    except json.JSONDecodeError:
        print("  <non-json signal>", message[:200])
        return
    _signals.append(sig)
    print(f"  [signal] {sig.get('type')}: {json.dumps(sig.get('event'))[:240]}")


def start_signal_listener() -> None:
    threading.Thread(
        target=lambda: websocket.WebSocketApp(WS, on_message=_on_signal).run_forever(),
        daemon=True,
    ).start()
    time.sleep(1.0)  # connect BEFORE we trigger anything


def call(endpoint: str, payload: dict) -> dict:
    resp = requests.post(f"{HTTP}/statusgo/{endpoint}", json=payload, timeout=60)
    print(f"-> {endpoint}  [{resp.status_code}]")
    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text}
    print(f"   {json.dumps(data)[:280]}")
    return data


def rpc(method: str, params: list | None = None) -> dict:
    return call("CallRPC", {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []})


def wait_for_signal(sig_type: str, timeout: float = 90.0) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for s in _signals:
            if s.get("type") == sig_type:
                return s
        time.sleep(0.5)
    return None


def main() -> None:
    print(f"Connecting signals: {WS}")
    start_signal_listener()

    call("InitializeApplication", {"dataDir": ROOT_DATA_DIR})

    call(
        "CreateAccountAndLogin",
        {
            "rootDataDir": ROOT_DATA_DIR,
            "displayName": DISPLAY_NAME,
            "password": PASSWORD,
            "customizationColor": CUSTOMIZATION_COLOR,
            "kdfIterations": KDF_ITERATIONS,
            "wakuV2Fleet": WAKU_FLEET,
            "logEnabled": True,
            "logLevel": "INFO",
        },
    )

    login = wait_for_signal("node.login")
    if not login:
        print("\n!! no node.login signal. Check the signals/errors above.")
        return
    if login.get("event", {}).get("error"):
        print("\n!! login error:", login["event"]["error"])
        return
    print("\n== logged in ==")

    rpc("wakuext_startMessenger")

    # Chat key = settings "public-key" (the 0x... compressed pubkey users add).
    settings = rpc("settings_getSettings")
    pub = (settings.get("result") or {}).get("public-key") if isinstance(settings.get("result"), dict) else None
    print("\n" + "=" * 60)
    if pub:
        print(f"BOT CHAT KEY (share this / make a QR):\n  {pub}")
    else:
        print("Couldn't auto-extract 'public-key'. Inspect settings_getSettings output above;")
        print("the chat key is the 0x-prefixed compressed public key.")
    print("=" * 60)
    print("\nKeep this process running to watch live signals (DM the bot from the app).")
    print("Ctrl+C to stop.")
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
