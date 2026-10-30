#!/usr/bin/env python3
"""Assemble and describe Mithril releases from verified upstream runtimes."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import tomllib
from urllib.parse import quote
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = json.loads((ROOT / "scripts/mithril_upstream_runtime.json").read_text())
TARGETS = set(UPSTREAM["targets"])


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def version():
    with (ROOT / "codex-rs/Cargo.toml").open("rb") as source:
        return tomllib.load(source)["workspace"]["package"]["version"]


def package(args):
    upstream = UPSTREAM["targets"][args.target]
    own_version = version()
    actual_version = subprocess.check_output(
        [args.binary, "--version"], text=True
    ).strip()
    if actual_version.split()[-1] != own_version:
        raise ValueError(
            f"Binary version {actual_version!r} does not match {own_version}"
        )
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        wheel = temp / "runtime.whl"
        with (
            urlopen(upstream["url"], timeout=120) as response,
            wheel.open("wb") as dest,
        ):
            shutil.copyfileobj(response, dest)
        if sha256(wheel) != upstream["sha256"]:
            raise ValueError("Upstream wheel SHA256 mismatch")
        runtime = temp / "runtime"
        runtime.mkdir()
        total = 0
        with zipfile.ZipFile(wheel) as archive:
            for entry in archive.infolist():
                if not entry.filename.startswith("codex_cli_bin/"):
                    continue
                relative = PurePosixPath(entry.filename).relative_to("codex_cli_bin")
                if not relative.parts or relative == PurePosixPath("__init__.py"):
                    continue
                mode = entry.external_attr >> 16
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR))
                ):
                    raise ValueError(f"Unsafe wheel entry: {entry.filename}")
                total += entry.file_size
                if total > 1024 * 1024 * 1024:
                    raise ValueError("Upstream runtime exceeds extraction limit")
                dest = runtime.joinpath(*relative.parts)
                if entry.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, dest.open("xb") as output:
                    shutil.copyfileobj(source, output)
                dest.chmod(mode & 0o777 or 0o644)
        binary = runtime / "bin/codex"
        if not binary.is_file():
            raise ValueError("Upstream runtime is missing bin/codex")
        shutil.copyfile(args.binary, binary)
        binary.chmod(0o755)
        metadata_path = runtime / "codex-package.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())
            metadata["version"] = own_version
            metadata["target"] = args.target
            write_json(metadata_path, metadata)
        info = {
            "version": own_version,
            "source_revision": args.revision,
            "upstream_version": UPSTREAM["version"],
            "target": args.target,
            "upstream_wheel_sha256": upstream["sha256"],
        }
        write_json(runtime / "build-info.json", info)
        for name in ("LICENSE", "NOTICE"):
            shutil.copyfile(ROOT / name, runtime / name)
        name = f"codex-mithril-{args.target}.tar.gz"
        archive_path = args.output / name
        with tarfile.open(archive_path, "w:gz") as archive:
            for path in sorted(runtime.iterdir()):
                archive.add(path, arcname=path.name)
        write_json(
            args.output / f"codex-mithril-{args.target}.json",
            {**info, "archive": name, "sha256": sha256(archive_path)},
        )


def manifest(args):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        raise ValueError("Repository must be OWNER/REPO")
    records = []
    for target in sorted(TARGETS):
        name = f"codex-mithril-{target}.tar.gz"
        metadata = json.loads((args.input / f"codex-mithril-{target}.json").read_text())
        if (
            metadata["target"] != target
            or metadata["archive"] != name
            or metadata["version"] != version()
            or metadata["source_revision"] != args.revision
            or metadata["upstream_version"] != UPSTREAM["version"]
            or metadata["upstream_wheel_sha256"]
            != UPSTREAM["targets"][target]["sha256"]
            or metadata["sha256"] != sha256(args.input / name)
        ):
            raise ValueError(f"Invalid release artifact metadata for {target}")
        url = f"https://github.com/{args.repository}/releases/download/{quote(args.tag, safe='')}/{name}"
        records.append({**metadata, "url": url})
    write_json(
        args.input / "release.json",
        {
            "version": version(),
            "source_revision": args.revision,
            "upstream_version": UPSTREAM["version"],
            "artifacts": records,
        },
    )
    (args.input / "SHA256SUMS").write_text(
        "".join(f"{record['sha256']}  {record['archive']}\n" for record in records)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("package")
    build.add_argument("--binary", type=Path, required=True)
    build.add_argument("--target", choices=sorted(TARGETS), required=True)
    build.add_argument("--revision", required=True)
    build.add_argument("--output", type=Path, required=True)
    build.set_defaults(func=package)
    release = commands.add_parser("manifest")
    release.add_argument("--input", type=Path, required=True)
    release.add_argument("--revision", required=True)
    release.add_argument("--repository", required=True)
    release.add_argument("--tag", required=True)
    release.set_defaults(func=manifest)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("revision must be a full lowercase commit SHA")
    args.func(args)


if __name__ == "__main__":
    main()
