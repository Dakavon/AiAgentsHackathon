---
marp: true
theme: gaia
paginate: true
title: Amtomat
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: ⚡ Powered by Nebius Token Factory -->

# 🏛️🤖 Amtomat

### Your private agent for public administration

Reach your own AI assistant over decentralized, encrypted **Status** messaging.
**It deals with the Amt for you.**

🗓️ AI Agents Hackathon 2026

---

## 📱 One assistant, reachable anywhere?

The private channels to your own agent are broken:

| | | |
|---|---|---|
| 📞 | **Signal** | needs its own phone number |
| 🔓 | **Telegram** | unencrypted and centralized |

➡️ Your agent ends up either **not private** or **not reachable**.

---

## 🛰️ Our move: reach your agent over Status

✅ Decentralized&nbsp;&nbsp; ✅ End-to-end encrypted
✅ No phone number&nbsp;&nbsp; ✅ No account

We built the **Status bridge** to our **Hermes** agent.

> 🟢 **Live:** a real Status message reaches the agent and gets a reply back.

---

## 🤖 It does not just answer. It acts.

You: *"I moved. Sort out my address registration."*

Amtomat, on your behalf:

1. 🔎 finds the responsible office
2. 📅 requests an appointment at the Amt
3. 🧾 brings back a verifiable confirmation

You stay in your messenger. **The agent runs the errand.** 🏃

---

## 💬 Live today

```
👤 User (Status):  "Ich bin umgezogen und brauche einen Termin."
🤖 Amtomat:        "Zustaendig ist das Buergeramt. Bring Ausweis,
                    Wohnungsgeberbestaetigung und Formular mit. Termin: ..."
```

🌍 multilingual &nbsp;|&nbsp; 🔒 private &nbsp;|&nbsp; 🤝 auto-accepts contacts, one session per user

<!-- Tip: replace with a screenshot of the live Status chat. -->

---

## 🛠️ How it works

![h:72](assets/status.png) &nbsp; ➡️ &nbsp; 🟢 status-go &nbsp; ➡️ &nbsp; 🌉 Bridge &nbsp; ➡️ &nbsp; 🧠 Hermes &nbsp; ➡️ &nbsp; ![h:72](assets/nebius.png)

- 📡 **Status** delivers the message over Waku: no SIM, end-to-end encrypted
- 🌉 the **Bridge** maps each chat key to its own 🧠 **Hermes** session
- ⚡ **Nebius** runs the model; when the agent books a slot ➡️ 🐝 **Swarm** stores a verifiable confirmation

RPC shapes verified against a live Status node.

---

## 🔒 Private and verifiable by design

- 🌐 **Channel:** Status / Waku. No phone number, E2E, no central server.
- 🐝 **Action proof:** appointment confirmation on **Swarm**. Content-addressed,
  tamper-proof, **no PII** (office, time, reference, a pubkey hash).
- 🧠 **Brain:** Hermes agent on **Nebius**, provider pluggable.

Citizen and office verify the **same Swarm hash** without revealing details.

---

## ⚡ Powered by Nebius Token Factory

- 🦙 `meta-llama/Llama-3.3-70B-Instruct`, OpenAI-compatible API
- 🛠️ **Tool-calling verified**, which is what lets the agent act
- 🔀 one config switch to scale the model or swap the provider

---

## 🎯 The two tracks we apply for

🏗️ **Infrastructure**
- a private, encrypted, no-phone-number channel to any AI agent

⛓️ **BGA (Blockchain for Good)**
- an agent that reaches the Amt for you
- 🐝 verifiable, private confirmations on Swarm

---

## 🛣️ Roadmap

- 🧠 **Hermes agent layer:** per-user memory and richer tool-calling
- 🤖 **Autonomous errands:** book real appointments, return Swarm confirmations
- 🏙️ **More offices:** municipal *Dienstleistungen* per city
- 🔌 **More channels:** the bridge is channel-agnostic

---

<!-- _class: lead -->
<!-- _paginate: false -->

# 🏛️🤖 Amtomat

### Your private agent for public administration

📡 Status &nbsp;+&nbsp; 🧠 Hermes &nbsp;+&nbsp; ⚡ Nebius &nbsp;+&nbsp; 🐝 Swarm

Built at AI Agents Hackathon 2026.
