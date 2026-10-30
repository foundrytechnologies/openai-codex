# Foundry Codex fork

This repository is a GitHub fork of [openai/codex](https://github.com/openai/codex).
Upstream licenses and notices remain in place.

| Reference | Purpose |
| --- | --- |
| `main` | Upstream default branch |
| `kris/upstream-0.160.1` | Unmodified `rust-v0.160.1` baseline for the MCP proposal |
| `d27764b82f7118f674371e6d6e76271d9d606edb` | Pinned upstream commit |

## Flat MCP tools

Some Responses-compatible providers intermittently fail while streaming
namespaced tool calls. Add this setting to an existing provider configuration
to expose MCP tools as top-level functions:

```toml
[model_providers.compatible]
experimental_flat_mcp_tools = true
```

Names such as `mcp__example__lookup` retain their canonical MCP identities for
permission checks, dispatch, approvals, and hooks. The setting defaults to false.

> [!IMPORTANT]
> This is an experimental direct-tool mode. Code Mode is rejected, deferred MCP
> search is disabled, and remote service provider configuration cannot carry the
> setting. Namespace descriptions are not included in flat tool declarations.

## Build and verification

Use the pinned Rust toolchain and the upstream build commands:

```sh
cd codex-rs
cargo build --locked -p codex-cli --bin codex
just test -p codex-model-provider-info -p codex-model-provider --lib
just test -p codex-core --lib -E 'test(flat)'
cargo build -p codex-rmcp-client --bin test_stdio_server
just test -p codex-core --test all -E 'test(flat_mcp_tool_is_advertised_and_dispatched)'
```

All 135 provider unit tests, four focused core tests, and the MCP dispatch
integration test passed. The integration test verifies the flat declaration,
MCP dispatch, and the returned tool result in the next model request.
The complete upstream test suite has not been run.

Cargo regenerated the release lockfile's local workspace package versions from
`0.0.0` to `0.160.1`. External dependency versions are unchanged.

> [!NOTE]
> Actions are disabled during initial setup. Binary releases require a separate
> change. Keep credentials and private experiment logs outside source control.
