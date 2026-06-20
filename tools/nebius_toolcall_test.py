#!/usr/bin/env python3
"""
Nebius Token Factory: Tool-Calling Smoke Test
==============================================

Hermes is an *agentic* runtime: it lives or dies by reliable function/tool
calling. Before wiring Hermes to Nebius, we need to know WHICH open model on
Token Factory tool-calls reliably. This script tries several candidate models
against the same forced-tool prompt and reports which ones are agent-ready.

Run:
    export NEBIUS_API_KEY=...        # from https://tokenfactory.nebius.com
    pip install openai
    python nebius_toolcall_test.py

A model PASSES if it:
  1. returns a tool_call (not prose) for a prompt that requires the tool,
  2. emits valid JSON arguments matching the schema,
  3. accepts the tool result and produces a sensible final answer.
"""

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

# read secrets/config from the repo-root .env (gitignored)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
load_dotenv()

# Provider-agnostic: defaults target Nebius Token Factory, but LLM_BASE_URL /
# LLM_MODELS in .env let you point at any OpenAI-compatible endpoint.
BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")

# Candidate instruct models with a reputation for solid tool-calling.
# Reasoning-first models (e.g. DeepSeek-R1) are intentionally NOT first,
# they can be flaky at structured tool calls. Adjust IDs to the live catalog.
_DEFAULT_MODELS = [
    "meta-llama/Llama-3.3-70B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct",
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "deepseek-ai/DeepSeek-V3",
]
CANDIDATE_MODELS = [
    m.strip()
    for m in os.environ.get("LLM_MODELS", ",".join(_DEFAULT_MODELS)).split(",")
    if m.strip()
]

# A tiny "public-services" flavored tool so the test mirrors our real use case.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_public_service",
            "description": (
                "Look up the responsible public office and required documents "
                "for an administrative procedure in a given city."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "procedure": {
                        "type": "string",
                        "description": "e.g. 'register residence', 'vehicle registration'",
                    },
                },
                "required": ["city", "procedure"],
            },
        },
    }
]

USER_PROMPT = (
    "I just moved and need to register my new address. "
    "Which office handles this and what documents do I need?"
)


def fake_tool_result(city: str, procedure: str) -> dict:
    """Stand-in for the real lookup the agent would do."""
    return {
        "city": city,
        "procedure": procedure,
        "office": "Buergeramt (residents' registration office)",
        "documents": ["ID or passport", "landlord confirmation", "registration form"],
    }


def test_model(client: OpenAI, model: str) -> tuple[bool, str]:
    messages = [
        {
            "role": "system",
            "content": "You are a multilingual public-services assistant. "
            "Use tools to look up factual procedure info before answering.",
        },
        {"role": "user", "content": USER_PROMPT},
    ]

    # --- Round 1: model must CHOOSE the tool -------------------------------
    try:
        r1 = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0,
        )
    except Exception as e:  # noqa: BLE001 (surface any API/model error)
        return False, f"API error on round 1: {e}"

    msg = r1.choices[0].message
    if not msg.tool_calls:
        return False, "no tool_call returned (answered with prose instead)"

    call = msg.tool_calls[0]
    if call.function.name != "lookup_public_service":
        return False, f"called wrong tool: {call.function.name!r}"

    try:
        args = json.loads(call.function.arguments)
    except json.JSONDecodeError:
        return False, f"invalid JSON arguments: {call.function.arguments!r}"

    if "city" not in args or "procedure" not in args:
        return False, f"missing required args: {args}"

    # --- Round 2: feed tool result back, expect a grounded final answer ---
    messages.append(msg)
    messages.append(
        {
            "role": "tool",
            "tool_call_id": call.id,
            "content": json.dumps(fake_tool_result(args["city"], args["procedure"])),
        }
    )
    try:
        r2 = client.chat.completions.create(
            model=model, messages=messages, tools=TOOLS, temperature=0
        )
    except Exception as e:  # noqa: BLE001
        return False, f"API error on round 2: {e}"

    final = (r2.choices[0].message.content or "").strip()
    if "ergeramt" not in final and "registration office" not in final.lower():
        return False, f"final answer didn't use tool result: {final[:120]!r}"

    return True, f"args={args} | final={final[:100]!r}"


def main() -> int:
    api_key = os.environ.get("NEBIUS_API_KEY")
    if not api_key:
        print("ERROR: set NEBIUS_API_KEY (get one at https://tokenfactory.nebius.com)")
        return 2

    client = OpenAI(base_url=BASE_URL, api_key=api_key)

    print(f"Testing tool-calling against {BASE_URL}\n")
    passed = []
    for model in CANDIDATE_MODELS:
        ok, detail = test_model(client, model)
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {model}\n        {detail}\n")
        if ok:
            passed.append(model)

    print("=" * 60)
    if passed:
        print("Agent-ready models (use the first in `hermes model`):")
        for m in passed:
            print(f"  - {m}")
        return 0
    print("No candidate passed. Check model IDs against the live Token Factory")
    print("catalog (https://docs.tokenfactory.nebius.com/llms.txt) and retry.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
