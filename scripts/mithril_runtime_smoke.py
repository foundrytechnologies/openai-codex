#!/usr/bin/env python3
"""Verify an unpacked Mithril runtime using the pinned Python SDK offline."""

import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import tempfile

from openai_codex import Codex, CodexConfig
from openai_codex._runtime_requirements import require_runtime_version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", type=Path)
    runtime = parser.parse_args().runtime.resolve()
    info = json.loads((runtime / "build-info.json").read_text())
    package = json.loads((runtime / "codex-package.json").read_text())
    if (package["version"], package["target"]) != (info["version"], info["target"]):
        raise ValueError("Package metadata does not match build information")
    if version("openai-codex") != info["upstream_version"]:
        raise ValueError("Unexpected SDK version")
    require_runtime_version(info["version"])
    binary = runtime / "bin/codex"
    result = subprocess.check_output([binary, "--version"], text=True).strip()
    if result.split()[-1] != info["version"]:
        raise ValueError(f"Unexpected CLI version: {result}")
    for path in (
        "bin/codex-code-mode-host",
        "codex-path/rg",
        "codex-resources/bwrap",
        "codex-resources/zsh/bin/zsh",
    ):
        if not os.access(runtime / path, os.X_OK):
            raise ValueError(f"Missing or non-executable runtime helper: {path}")
    with tempfile.TemporaryDirectory() as home:
        (Path(home) / ".codex").mkdir()
        env = {
            "HOME": home,
            "CODEX_HOME": str(Path(home) / ".codex"),
            "PATH": f"{runtime / 'codex-path'}{os.pathsep}{os.environ.get('PATH', '')}",
        }
        with Codex(CodexConfig(codex_bin=str(binary), cwd=home, env=env)) as client:
            server = client.metadata.serverInfo
            if server is not None and server.version.split()[0] != info["version"]:
                raise ValueError(f"Unexpected server version: {server.version}")
            print(f"Initialized SDK {version('openai-codex')} with {result}")


if __name__ == "__main__":
    main()
