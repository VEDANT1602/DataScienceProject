# SPDX-License-Identifier: MIT
"""Verify archived source bytes against the migration manifest without running notebooks."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent


def verify(git_objects: bool = False) -> dict:
    manifest = json.loads((HERE / "migration-manifest.json").read_text(encoding="utf-8"))
    checked = 0
    checked_bytes = 0
    failures = []
    for repo in manifest["repositories"]:
        for entry in repo["files"]:
            relative = Path(repo["snapshot_directory"]) / entry["path"]
            source = HERE / relative
            assert source.resolve().is_relative_to(HERE.resolve())
            sha256 = hashlib.sha256()
            blob = hashlib.sha1(b"blob " + str(entry["bytes"]).encode() + b"\0")
            size = 0
            process = None
            try:
                if git_objects:
                    ref = "HEAD:legacy/" + relative.as_posix()
                    process = subprocess.Popen(["git", "-C", str(HERE.parent), "cat-file", "blob", ref],
                                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    handle = process.stdout
                else:
                    handle = source.open("rb")
                with handle:
                    while chunk := handle.read(1024 * 1024):
                        size += len(chunk)
                        sha256.update(chunk)
                        blob.update(chunk)
                if process is not None and process.wait() != 0:
                    raise FileNotFoundError("Tracked Git blob was not found")
                matches = (size == entry["bytes"] and sha256.hexdigest() == entry["sha256"]
                           and blob.hexdigest() == entry["git_blob_sha"])
                if not matches:
                    failures.append({"path": relative.as_posix(), "issue": "byte_hash_mismatch"})
            except OSError as error:
                failures.append({"path": relative.as_posix(), "issue": type(error).__name__})
            checked += 1
            checked_bytes += size
    return {"repositories": len(manifest["repositories"]), "files_checked": checked,
            "bytes_checked": checked_bytes, "mode": "Git objects" if git_objects else "filesystem",
            "all_match": not failures, "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git-objects", action="store_true",
                        help="Verify committed blobs, independent of platform checkout line endings")
    arguments = parser.parse_args()
    result = verify(arguments.git_objects)
    print(json.dumps(result, indent=2))
    return 0 if result["all_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
