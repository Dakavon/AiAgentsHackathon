# Build status-backend (headless Status node) from source.
# status-go is cgo-heavy (sqlcipher, secp256k1, ...), so we need a full
# C toolchain in the builder stage.
#
# NOTE: pin STATUS_GO_REF to a known-good commit/tag once it builds, so the
# image is reproducible across the team. `develop` moves fast.
ARG GO_VERSION=1.24
FROM golang:${GO_VERSION}-bookworm AS builder

# Pinned to v10.31.0 ON PURPOSE: it's the newest status-go tag that builds with
# just Go + cgo + the lightweight protobuf toolchain. From v10.32.0 on,
# status-backend links libsds.so (the Nim-based nim-sds library), which drags in
# the full Nimbus/Nim toolchain, a much heavier build we don't need for a
# 1:1-messaging bot.
ARG STATUS_GO_REF=v10.31.0
# libprotobuf-dev provides the well-known-type imports (google/protobuf/*.proto)
# that protoc needs; protobuf-compiler alone (with --no-install-recommends) omits them.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git ca-certificates protobuf-compiler libprotobuf-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git clone --branch "${STATUS_GO_REF}" --depth 1 \
        https://github.com/status-im/status-go.git .

# `make status-backend` runs `make generate`, which invokes protoc. Provide the
# Go protobuf plugin on PATH (matches the version verified to build v10.31.0).
ENV PATH="/go/bin:${PATH}"
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.34.1

# Build only the headless backend command (verified to compile clean at v10.31.0).
RUN make status-backend

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /src/build/bin/status-backend /usr/local/bin/status-backend

# Control API + signals websocket are served on this address.
EXPOSE 12345
# Persist keystore/accounts/db so the bot keeps the SAME chat key across restarts.
VOLUME ["/data"]
WORKDIR /data

ENTRYPOINT ["status-backend"]
CMD ["--address", "0.0.0.0:12345"]
