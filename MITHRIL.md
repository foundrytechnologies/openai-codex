# Mithril Codex releases

This GitHub fork tracks [openai/codex](https://github.com/openai/codex).
Upstream licenses and notices remain in place.

| Reference | Contents |
| --- | --- |
| `main` | One flat-MCP patch on upstream `rust-v0.160.1` |
| `kris/mithril-0.160.1` | Mithril versioning and release packaging |
| `mithril-v0.160.1+mithril.1` | First Mithril runtime release |

The runtime reports `0.160.1+mithril.1`. Build metadata distinguishes the fork
while remaining compatible with the pinned Python SDK's version parser.

## Downloads

Each GitHub Release contains these complete runtime archives:

- `codex-mithril-x86_64-unknown-linux-gnu.tar.gz`
- `codex-mithril-aarch64-unknown-linux-gnu.tar.gz`
- `SHA256SUMS` and `release.json` with archive hashes, source revision, and URLs.

> [!IMPORTANT]
> Consumers should pin a release tag and archive SHA256. Do not resolve the
> latest release during image builds. Verify the archive before extracting it.

Archives contain `bin/codex`, upstream runtime helpers, licenses, and
`build-info.json`. Helpers come from checksum-pinned upstream 0.160.1 wheels;
the CLI is built from this fork with Rust 1.95 on Debian 12.
The runtime targets Debian 12 / glibc 2.36 or newer.

Keep the Python SDK pinned to `openai-codex==0.160.1`, extract the matching
archive into the worker image, and select its executable explicitly:

```python
CodexConfig(codex_bin="/opt/codex-mithril/bin/codex")
```

## Release process

The `mithril-release` workflow builds native amd64 and arm64 runtimes and
initializes the pinned SDK against each packaged runtime in Python 3.12 on
Debian 12. Only successful tag builds publish a GitHub prerelease.

Update the workspace version and lockfile on the release branch, then push a
tag named `mithril-v` followed by that exact version. `main` stays focused on the
harness patch; packaging remains separate for a possible upstream proposal.

The MCP setting remains opt-in:

```toml
[model_providers.compatible]
experimental_flat_mcp_tools = true
```

This experimental mode exposes top-level MCP functions while retaining canonical
permission checks and dispatch. It supports direct tools and local provider
configuration. Code Mode is rejected, deferred MCP search is disabled, and
namespace descriptions are omitted from flat declarations.
