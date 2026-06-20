#!/usr/bin/env python3
"""
Swarm storage for appointment confirmations.

Stores a small, PII-free confirmation as raw bytes on a Bee node and returns the
content address (Swarm reference). Both the citizen and the office can later read
the same bytes by that hash, and the hash IS the checksum, so it is tamper-proof.

Bee dev mode exposes two APIs:
  - data API  (:1633): /bytes upload and download
  - debug API (:1635): /stamps postage-stamp management

A postage stamp is bought once and reused for all confirmations.
"""

import json
import os
import time

import requests

BEE_API = os.environ.get("BEE_API", "http://localhost:1633")
BEE_DEBUG_API = os.environ.get("BEE_DEBUG_API", "http://localhost:1635")
STAMP_AMOUNT = os.environ.get("BEE_STAMP_AMOUNT", "100000000")
STAMP_DEPTH = os.environ.get("BEE_STAMP_DEPTH", "20")

_batch_id: str | None = None


def _get_stamp() -> str:
    """Return a usable postage batch id, reusing one if available."""
    global _batch_id
    if _batch_id:
        return _batch_id

    # reuse an existing usable stamp if the node already has one
    try:
        stamps = requests.get(f"{BEE_DEBUG_API}/stamps", timeout=10).json().get("stamps", [])
        for s in stamps:
            if s.get("usable"):
                _batch_id = s["batchID"]
                return _batch_id
    except requests.RequestException:
        pass

    # otherwise buy one (free in dev mode)
    r = requests.post(f"{BEE_DEBUG_API}/stamps/{STAMP_AMOUNT}/{STAMP_DEPTH}", timeout=30)
    r.raise_for_status()
    _batch_id = r.json()["batchID"]
    for _ in range(30):  # wait until the batch is usable
        st = requests.get(f"{BEE_DEBUG_API}/stamps/{_batch_id}", timeout=10).json()
        if st.get("usable"):
            break
        time.sleep(1)
    return _batch_id


def store_confirmation(data: dict) -> str:
    """Upload the confirmation JSON to Swarm; return the content reference (hash)."""
    batch = _get_stamp()
    r = requests.post(
        f"{BEE_API}/bytes",
        data=json.dumps(data).encode(),
        headers={"Swarm-Postage-Batch-Id": batch, "Content-Type": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["reference"]


def read_confirmation(reference: str) -> dict:
    """Read a confirmation back from Swarm by its reference (for verification)."""
    r = requests.get(f"{BEE_API}/bytes/{reference}", timeout=30)
    r.raise_for_status()
    return r.json()
