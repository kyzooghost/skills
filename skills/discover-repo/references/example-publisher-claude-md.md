# Example: High-Quality CLAUDE.md

This is a real CLAUDE.md generated for a Rust-based Shared Publisher service. Use it as a quality benchmark for the output you produce. Note the level of detail in component descriptions, the annotated directory tree, and the ASCII data flow diagram.

---

# Ethera Shared Publisher - CLAUDE.md

## 1. Purpose

The Ethera Shared Publisher is the **coordinator** in a Two-Phase Commit (2PC) protocol that enables **synchronous composability across rollups**. It allows cross-chain transactions (xTs) - transactions that span multiple L2 rollup chains - to either commit on all chains or abort on all chains atomically within the same time slot.

The publisher sits at the center of a hub-and-spoke topology: rollup sequencer sidecars connect to it over QUIC. When a cross-chain transaction arrives, the publisher orchestrates the 2PC consensus - broadcasting `StartInstance` to all sidecars, collecting votes, and broadcasting the final `Decided` outcome. It also manages superblock periods, proof collection from rollup provers, and L1 settlement via the `ComposeL2OutputOracle` contract.

This is part of the broader Ethera/Compose protocol. The publisher coordinates; the sequencers (running modified op-geth) execute. See the AGENTS.md file (on development branches) for the full system architecture including sequencer integration details.

**Note:** The `main` branch contains only a Go template skeleton. All actual code lives on feature/development branches. The most recent development is on the branch at commit `ed8de74` (Rust implementation). This document describes that Rust codebase.

---

## 2. Architecture

### 2.1 Directory Tree

```
publisher/
  bin/publisher/src/
    main.rs                          # Binary entrypoint: wires QUIC + HTTP + coordinator + loops
  crates/
    config/src/
      lib.rs                         # YAML + env-var config loading (ServerConfig, ApiConfig, ConsensusConfig, etc.)
    coordinator/src/
      coordinator.rs                 # Core 2PC state machine (CoordinatorState), xT lifecycle, proof collection
      handlers.rs                    # Inbound protobuf message dispatch (Vote, XtRequest, Ping, Handshake, Proof, Mailbox)
      l1_submit.rs                   # L1 settlement: builds SuperblockAggregationOutputs, calls proposeL2Output on L1
      proof_types.rs                 # ProofData, AggregationOutputs, MailboxInfo structs
      lib.rs                         # Module declarations
    transport/src/
      server.rs                      # QUIC server: connection registry, identification handshake, message loop
      framing.rs                     # 4-byte big-endian length-prefixed framing codec
      tls.rs                         # Self-signed ephemeral TLS via rcgen (ALPN: "ethera-quic")
      socket.rs                      # UDP socket with 7MB OS buffer tuning
      error.rs                       # TransportError enum
      lib.rs                         # Module declarations
    server/src/
      router.rs                      # Axum HTTP router: /health, /ready, /stats, /metrics, /v1/proofs/op-succinct
      state.rs                       # AppState (shared Coordinator + Prometheus Registry)
      handlers/
        health.rs                    # GET /health (liveness), /ready (503 until sidecar connects), /stats
        metrics.rs                   # GET /metrics (Prometheus OpenMetrics text)
        proofs.rs                    # POST /v1/proofs/op-succinct (HTTP proof submission from op-succinct provers)
      lib.rs                         # Module declarations
    metrics/src/
      lib.rs                         # PublisherMetrics: connections, messages, xT counters, decision latency histogram
    tracing/src/
      lib.rs                         # tracing-subscriber init (JSON or pretty format)
    spec/src/                        # [VENDORED] Domain types
      primitives.rs                  # ChainId, PeriodId, SequenceNumber, SuperblockNumber, InstanceId, etc.
      instance.rs                    # XtRequest, TransactionRequest, Instance, DecisionState
      lib.rs                         # Re-exports, PERIOD_DURATION (3840s), PROOF_WINDOW (24*7 periods)
    spec-proto/src/                  # [VENDORED] Protobuf wire types
      messages.rs                    # Hand-written prost::Message structs (no .proto file - uses prost derive macros)
      convert.rs                     # Bidirectional From impls between proto and domain types
      lib.rs                         # Re-exports
    spec-sbcp/src/                   # [VENDORED] Superblock Construction Protocol types
      publisher.rs                   # Publisher state machine (trait-based: PublisherProver, PublisherMessenger, L1Publisher)
      sequencer.rs                   # Sequencer state machine (trait-based: SequencerProver, SequencerMessenger)
      block.rs                       # BlockNumber, PendingBlock, BlockHeader, SealedBlockHeader, SettledState
      id.rs                          # generate_instance_id: SHA256(period_id || seq || chain_data...)
      lib.rs                         # Re-exports
  Cargo.toml                         # Workspace root (10 members, workspace dependencies)
  Cargo.lock                         # Locked dependency versions
  Dockerfile                         # Multi-stage: cargo-chef -> build -> debian:bookworm-slim runtime
  justfile                           # Task runner (build, test, lint, fmt, ci, dev, docker, etc.)
  rust-toolchain.toml                # Pinned to Rust 1.91
  deny.toml                          # cargo-deny: license allowlist, ban openssl, ignore RUSTSEC-2024-0436
  clippy.toml                        # MSRV 1.91
  rustfmt.toml                       # Edition 2021, max_width 100, tab_spaces 4
  .pre-commit-config.yaml            # Pre-commit hooks: fmt, clippy, deny, machete
  .github/workflows/
    go.yml                           # Go CI (legacy, for main branch template)
    local-testnet.yml                # Local testnet on PR comment (/test trigger)
```

### 2.2 Key System Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| **main.rs** | `bin/publisher/src/main.rs` | Entrypoint. Parses config, initializes QUIC server + HTTP API + Coordinator. Spawns period loop (12s default broadcast) and reaper loop (1s timeout/proof cleanup). Graceful shutdown on CTRL+C. |
| **Coordinator** | `crates/coordinator/src/coordinator.rs` | Core 2PC state machine. Manages `CoordinatorState` behind `Arc<RwLock<...>>`. Handles xT requests (queue if chains overlap, else prepare), votes (collect, decide on unanimous or any-false), period advancement, proof collection, L1 submission, timeout reaping, rollback. |
| **handlers::dispatch** | `crates/coordinator/src/handlers.rs` | Protobuf message router. Decodes `Message` envelope, dispatches by `Payload` variant to coordinator methods. |
| **L1Submitter** | `crates/coordinator/src/l1_submit.rs` | Builds `SuperblockAggregationOutputs`, ABI-encodes, calls `proposeL2Output` on `ComposeL2OutputOracle` via alloy. Retries up to 3 times with exponential backoff. Tracks parent superblock hash. |
| **QuicServer** | `crates/transport/src/server.rs` | QUIC server using quinn. Accepts connections, reads client ID from first bi-stream, registers in `ConnectionRegistry`. Subsequent bi-streams carry length-prefixed protobuf messages. Supports `send_raw` (unicast) and `broadcast_raw`. |
| **HTTP API** | `crates/server/` | Axum-based. `/health` (liveness), `/ready` (503 until sidecar connected), `/stats` (JSON coordinator state), `/metrics` (Prometheus), `/v1/proofs/op-succinct` (POST proof submission). |
| **PublisherMetrics** | `crates/metrics/src/lib.rs` | Prometheus counters/gauges/histogram: connections_active, messages_received, broadcasts_sent, xt_started/committed/aborted/queued, decision_latency_seconds, period_broadcast. |
| **Config** | `crates/config/src/lib.rs` | YAML config file + env-var overrides (`SECTION_FIELD` convention). Sections: server, api, consensus, metrics, log, settlement. |

### 2.3 Data Flow

```
                    QUIC (protobuf, length-prefixed)
                    +--------------------------------------------+
                    |                                            |
+---------------+   |    +-----------------------------+         |   +---------------+
| Rollup A      |---+    |      Shared Publisher       |         +---| Rollup B      |
| Sidecar       |   |    |                             |         |   | Sidecar       |
| (op-geth)     |<--+    |  QuicServer                 |         +-->| (op-geth)     |
+---------------+   |    |    |                         |         |   +---------------+
                    |    |    v                         |         |
                    |    |  handlers::dispatch          |         |
                    |    |    |                         |         |
                    |    |    v                         |         |
                    |    |  Coordinator (2PC state)     |         |
                    |    |    |                         |         |
                    |    |    +- Period loop (12s)      |         |
                    |    |    +- Reaper loop (1s)       |         |
                    |    |    +- L1Submitter            |         |
                    |    |                              |         |
                    |    |  HTTP API (Axum)             |         |
                    |    |    /health /ready /stats     |         |
                    |    |    /metrics                  |         |
                    |    |    /v1/proofs/op-succinct    |         |
                    |    +-----------------------------+         |
                    +--------------------------------------------+
                                      |
                                      | proposeL2Output (alloy)
                                      v
                              +---------------+
                              |  L1 Contract  |
                              | ComposeL2     |
                              | OutputOracle  |
                              +---------------+
```

### 2.4 Cross-Chain Transaction (xT) Lifecycle

1. **XtRequest arrives** - A sidecar sends `Payload::XtRequest` containing per-chain transaction bundles. `handlers::dispatch` routes to `Coordinator::handle_xt_request`.

2. **Chain overlap check** - The coordinator checks if any target chain is already locked by an active xT. If overlap exists, the request is queued (up to 100 entries in `pending_queue`). If no overlap, the request proceeds immediately.

3. **Prepare** - `CoordinatorState::prepare_xt` assigns the next `SequenceNumber`, computes a deterministic `InstanceId` via `generate_instance_id(period_id, seq, xt_request)` (SHA-256 hash), reserves chains in `active_chains`, and constructs a `StartInstance` protobuf message.

4. **Broadcast StartInstance** - The publisher broadcasts to all connected sidecars. Each sidecar simulates its local transactions, exchanges mailbox (CIRC) messages with peers, and votes.

5. **Vote collection** - Each sidecar sends `Payload::Vote(instance_id, chain_id, bool)`. The coordinator records votes in `ActiveXt::votes`. A single `false` vote triggers immediate `Decided(false)`. Once all chains have voted `true`, the outcome is `Decided(true)`.

6. **Decision broadcast** - The `Decided` message is broadcast to all sidecars. Chains are released from `active_chains`. The queue is drained (`drain_queue`) to start any waiting xTs whose chains are now free.

7. **Timeout** - If no decision is reached within `scp_timeout` (default 60s), the reaper loop produces `Decided(false)` and drains the queue.

---

## 3. Noteworthy Implementation Choices

### Single RwLock for all coordinator state
All mutable state lives in `CoordinatorState` behind a single `Arc<RwLock<...>>`. The lock is dropped before any `.await` (broadcasting) to avoid holding it across async suspension points. This is a deliberate simplicity-over-concurrency trade-off.

### Deterministic Instance IDs
`generate_instance_id` hashes `SHA256(period_id || sequence_number || chain_id || tx_count || tx_length || tx_data ...)` to produce a 32-byte `InstanceId`. This ensures every participant independently computes the same ID for the same xT, enabling distributed consensus without a naming authority.

### Vendored spec crates
The three `spec-*` crates are temporary local copies. Protobuf types use prost derive macros directly in Rust code (no `.proto` files or codegen).

### Self-signed ephemeral TLS
`crates/transport/src/tls.rs` generates a fresh self-signed certificate at every startup using rcgen. No mTLS or client authentication beyond QUIC's transport encryption. Custom ALPN: `ethera-quic`.

### Chain reservation prevents concurrent xTs on same chain
`active_chains: HashMap<ChainId, String>` maps each locked chain to the xT ID that holds it. New xT requests touching any locked chain are queued.

### Readiness depends on sidecar connections
`GET /ready` returns 503 until at least one sidecar is connected. Prevents premature load balancer traffic.

---

## 4. Key Data Types and Interfaces

### Domain Types (crates/spec)

| Type | Description |
|------|-------------|
| `ChainId(u64)` | Rollup chain identifier |
| `PeriodId(u64)` | Superblock period counter |
| `SequenceNumber(u64)` | Monotonically increasing xT sequence within a period |
| `InstanceId([u8; 32])` | Deterministic SHA-256 hash identifying an SCP instance |
| `XtRequest { transactions: Vec<TransactionRequest> }` | Cross-chain transaction: per-chain bundles of RLP-encoded txs |
| `DecisionState { Pending, Accepted, Rejected }` | Outcome states |

### Wire Protocol (crates/spec-proto)

Messages use 4-byte big-endian length prefix + protobuf body.

| Tag | Payload | Direction | Purpose |
|-----|---------|-----------|---------|
| 6 | `XtRequest` | Sidecar -> Publisher | Cross-chain transaction request |
| 7 | `StartInstance` | Publisher -> All | Begin 2PC for an xT |
| 8 | `Vote` | Sidecar -> Publisher | Chain's commit/abort vote |
| 9 | `Decided` | Publisher -> All | Final 2PC decision |
| 11 | `StartPeriod` | Publisher -> All | New superblock period |
| 12 | `Rollback` | Publisher -> All | Revert to last finalized state |
| 13 | `Proof` | Sidecar -> Publisher | ZK proof submission (QUIC path) |

---

## 5. Test Infrastructure

### Test counts by file

| File | Tests |
|------|-------|
| `crates/spec-sbcp/src/publisher.rs` | 18 |
| `crates/spec-sbcp/src/sequencer.rs` | 13 |
| `crates/config/src/lib.rs` | 7 |
| `crates/spec/src/primitives.rs` | 3 |
| `crates/spec/src/instance.rs` | 3 |
| `crates/spec-proto/src/convert.rs` | 2 |
| `crates/transport/src/framing.rs` | 2 |
| **Total** | **51** |

### Testing approach

- All tests are unit tests using `#[cfg(test)] mod tests` inline in source files
- The `spec-sbcp` crate uses fake trait implementations (`FakeMessenger`, `FakeProver`, `FakeL1`) for isolated state machine testing
- No integration or E2E tests in this repo - those live in deployment infrastructure

---

## 6. Build/Dev Workflow

### Prerequisites

- Rust 1.91 (auto-installed via `rust-toolchain.toml`)
- `cargo-deny` and `cargo-machete` for CI-full: `just install-tools`

### Core commands (via justfile)

```bash
just build          # cargo build --workspace
just test           # cargo test --workspace
just lint           # cargo clippy --workspace --all-targets -- -D warnings
just fmt            # cargo fmt --all
just ci             # fmt-check + lint + test
just dev            # Run with debug logging
just docker         # docker build -t publisher:latest .
```

### Configuration

| Env Variable | Default | Description |
|-------------|---------|-------------|
| `SERVER_LISTEN_ADDR` | `0.0.0.0:8080` | QUIC server bind address |
| `API_LISTEN_ADDR` | `0.0.0.0:8081` | HTTP API bind address |
| `CONSENSUS_TIMEOUT` | `60s` | 2PC vote timeout |
| `CONSENSUS_PERIOD_DURATION` | `3840s` | Superblock period duration |
| `SETTLEMENT_L1_RPC_URL` | (empty) | L1 JSON-RPC endpoint |

---

## 7. Dependency Highlights

| Dependency | Version | Purpose |
|-----------|---------|---------|
| `quinn` | 0.11 | QUIC transport |
| `prost` | 0.13 | Protobuf encoding/decoding |
| `axum` | 0.7 | HTTP API |
| `alloy` | 1.x | Ethereum L1 interaction |
| `tokio` | 1.43 | Async runtime |

OpenSSL is explicitly banned in `deny.toml`.
