#!/usr/bin/env python3
"""
Build .mrpack files for each modpack branch.

For each remote branch (excluding _build), archives the branch content
into a .mrpack file (ZIP format) suitable for Modrinth-compatible launchers.
"""

import os
import re
import subprocess
import sys
import zipfile


def get_remote_branches(exclude: list[str] | None = None) -> list[str]:
    """Return a list of remote branch refs, excluding specified ones."""
    if exclude is None:
        exclude = ["_build"]

    result = subprocess.run(
        ["git", "branch", "-r"],
        capture_output=True,
        text=True,
        check=True,
    )

    branches: list[str] = []
    for line in result.stdout.strip().splitlines():
        ref = line.strip()
        if "->" in ref:
            continue
        branch_name = re.sub(r"^[^/]+/", "", ref)
        if branch_name not in exclude:
            branches.append(ref)

    return branches


def build_mrpack(ref: str, output_dir: str) -> str | None:
    """Build a .mrpack (ZIP) from the contents of a git branch."""
    branch_name = re.sub(r"^[^/]+/", "", ref)
    mrpack_path = os.path.join(output_dir, f"{branch_name}.mrpack")

    # List all files in the branch
    try:
        result = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", ref],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"  ⚠ Cannot list files for {ref}: {exc}", file=sys.stderr)
        return None

    files = result.stdout.strip().splitlines()
    if not files:
        print(f"  ⚠ No files in {ref}", file=sys.stderr)
        return None

    with zipfile.ZipFile(mrpack_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for filepath in files:
            try:
                blob = subprocess.run(
                    ["git", "show", f"{ref}:{filepath}"],
                    capture_output=True,
                    check=True,
                )
                zf.writestr(filepath, blob.stdout)
            except subprocess.CalledProcessError:
                print(f"  ⚠ Cannot read {filepath} from {ref}", file=sys.stderr)
                continue

    return mrpack_path


def main() -> None:
    output_dir = "."
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    os.makedirs(output_dir, exist_ok=True)

    print("🔍 Fetching remote branches…")
    branches = get_remote_branches()

    if not branches:
        print("ℹ No modpack branches found.", file=sys.stderr)
        return

    print(f"📦 Building .mrpack for {len(branches)} branch(es)")

    for ref in branches:
        branch_name = re.sub(r"^[^/]+/", "", ref)
        print(f"  → Building {branch_name}.mrpack…")
        path = build_mrpack(ref, output_dir)
        if path:
            size_kb = os.path.getsize(path) / 1024
            print(f"    ✅ {path} ({size_kb:.1f} KB)")

    print("✅ Done!")


if __name__ == "__main__":
    main()
