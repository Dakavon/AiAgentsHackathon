# Status channel: headless node (status-backend) in Docker

Runs a headless [Status](https://status.app) node so the bot can send and receive
**1:1 chat messages** that interoperate with the official Status mobile app. Raw Waku
is **not** enough: the app speaks the Status messaging protocol, which `status-go`
implements.

Pinned to status-go **v10.31.0**, the newest tag that builds without the Nim/libsds
toolchain (added in v10.32.0). See the [Dockerfile](Dockerfile).

## 1. Build and run the node

```bash
cd status
docker compose build      # first build is slow: clones status-go and compiles (cgo)
docker compose up -d
docker compose logs -f    # watch it sync into the Waku network
```

The node serves a control API and a signals websocket on `localhost:12345`.

## 2. Bootstrap the bot account and read its chat key

```bash
pip install -r requirements.txt
python bootstrap.py
```

This connects to the signals socket, creates the bot account, logs in, starts the
messenger, and prints the bot's chat key. Share the `zQ3sh` form (a compressed public
key) so users can add the bot as a contact in the Status app.

The named volume `status-data` persists the keystore, so the bot keeps the **same chat
key** across restarts. `docker compose down -v` wipes it (new identity).

## How it talks to the app (verified on a live node)

- Incoming messages arrive as the signal `messages.new`. Read them with
  `wakuext_chatMessages(chatId, "", limit)`.
- A user cannot cold-DM the bot: Status requires a mutual contact. The contact request
  arrives as `contentType 11`; the bridge auto-accepts it with
  `wakuext_acceptContactRequest({id})`. Without that step nothing reaches the bot, even
  though the node is up.
- The bridge replies with `wakuext_sendChatMessage({chatId, text, contentType: 1})`.

## Next

The bridge (`../bridge/`) listens on the signals socket, auto-accepts contact requests,
maps each sender's chat key to an LLM session, calls Nebius (or Hermes), and replies.
