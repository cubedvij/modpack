#!/usr/bin/env python3
"""
Aggregate modpack metadata from modrinth.index.json across all git branches.

Iterates over all remote-tracking branches (excluding HEAD and _build),
reads modrinth.index.json from each via `git show`, and writes:
  - modpacks.json  — compact metadata index
  - index.html     — human-friendly download page
"""

import json
import os
import subprocess
import sys
import re
import hashlib
from datetime import datetime, timezone

REQUIRED_FIELDS = ["formatVersion", "game", "name", "versionId", "files", "dependencies"]


def get_remote_branches(exclude: list[str] | None = None) -> list[str]:
    """Return a list of remote branch names, excluding specified ones."""
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


def read_index_from_branch(ref: str) -> dict | None:
    """Read and parse modrinth.index.json from a given git ref."""
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:modrinth.index.json"],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"  ⚠ Skipping {ref}: {exc}", file=sys.stderr)
        return None


def validate_index(ref: str, index: dict) -> list[str]:
    """Validate modrinth.index.json and return a list of problems."""
    problems: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in index:
            problems.append(f"missing required field '{field}'")
    if index.get("game") != "minecraft":
        problems.append(f"unexpected game: '{index.get('game')}'")
    if index.get("formatVersion") != 1:
        problems.append(f"unexpected formatVersion: {index.get('formatVersion')}")
    if problems:
        print(f"  ⚠ Validation issues in {ref}: {'; '.join(problems)}", file=sys.stderr)
    return problems


def count_overrides_files(ref: str) -> int:
    """Count files inside the overrides/ directory for a given git ref."""
    try:
        result = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", ref, "overrides/"],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.strip()
        return len(lines.splitlines()) if lines else 0
    except subprocess.CalledProcessError:
        return 0


def get_last_commit_info(ref: str) -> tuple[str, str]:
    """Return (ISO timestamp, commit message) for the last commit on a ref."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI%n%s", ref],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.strip().splitlines()
        timestamp = lines[0] if lines else ""
        message = lines[1] if len(lines) > 1 else ""
        return timestamp, message
    except subprocess.CalledProcessError:
        return "", ""


def get_repo_slug() -> str:
    """Get the GitHub repository slug (owner/repo) from env or git remote."""
    slug = os.environ.get("GITHUB_REPOSITORY", "")
    if slug:
        return slug
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        # Handle both HTTPS and SSH URLs
        match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
        if match:
            return match.group(1)
    except subprocess.CalledProcessError:
        pass
    return ""


def build_download_url(repo_slug: str, branch_name: str) -> str:
    """Build the GitHub Release download URL for a .mrpack file."""
    if not repo_slug:
        return ""
    return f"https://github.com/{repo_slug}/releases/download/meta/{branch_name}.mrpack"


def extract_info(ref: str, index: dict, repo_slug: str) -> dict:
    """Extract key metadata from a modrinth.index.json dict."""
    branch_name = re.sub(r"^[^/]+/", "", ref)
    updated_at, changelog = get_last_commit_info(ref)

    info = {
        "branch": branch_name,
        "name": index.get("name", ""),
        "version": index.get("versionId", ""),
        "summary": index.get("summary", ""),
        "dependencies": index.get("dependencies", {}),
        "fileCount": len(index.get("files", [])) + count_overrides_files(ref),
        "updatedAt": updated_at,
        "changelog": changelog,
        # hash the modpack.mrpack 
        
    }

    dl_url = build_download_url(repo_slug, branch_name)
    if dl_url:
        info["downloadUrl"] = dl_url
        info["sha256"] = hashlib.sha256(open(f"{branch_name}.mrpack", "rb").read()).hexdigest()

    return info


def generate_html(modpacks: list[dict], repo_slug: str) -> str:
    """Generate a simple HTML page listing all modpacks."""
    rows = ""
    for m in modpacks:
        deps = ", ".join(f"{k} {v}" for k, v in m.get("dependencies", {}).items())
        dl_link = ""
        hash_short = ""
        if m.get("downloadUrl"):
            hash_short = m.get("sha256", "")[:8]
            dl_link = f'<a href="{m["downloadUrl"]}">⬇ .mrpack</a>'

        updated = m.get("updatedAt", "")[:10]  # just the date part

        rows += f"""      <tr>
        <td><strong>{m["name"]}</strong></td>
        <td><code>{m["branch"]}</code></td>
        <td>{m["version"]}</td>
        <td>{deps}</td>
        <td>{m["fileCount"]}</td>
        <td>{updated}</td>
        <td>{m.get("changelog", "")}</td>
        <td><code>{hash_short}</code></td>
        <td>{dl_link}</td>
      </tr>
"""

    repo_url = f"https://github.com/{repo_slug}" if repo_slug else "#"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CubeDvij Modpacks</title>
  
  <!-- Open Graph / Facebook -->
  <meta property="og:type" content="website">
  <meta property="og:url" content="{repo_url}">
  <meta property="og:title" content="CubeDvij Modpacks">
  <meta property="og:description" content="A collection of {len(modpacks)} modpack(s) for Minecraft. Updated {now}">
  <meta property="og:image" content="{repo_url}/raw/_build/icon.png">
  
  <!-- Twitter -->
  <meta property="twitter:card" content="summary_large_image">
  <meta property="twitter:url" content="{repo_url}">
  <meta property="twitter:title" content="CubeDvij Modpacks">
  <meta property="twitter:description" content="A collection of {len(modpacks)} modpack(s) for Minecraft. Updated {now}">
  <meta property="twitter:image" content="{repo_url}/raw/_build/icon.png">
  
  <style>
    :root {{
      --bg: #0d1117;
      --surface: #161b22;
      --border: #30363d;
      --text: #e6edf3;
      --muted: #8b949e;
      --accent: #58a6ff;
      --green: #3fb950;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      padding: 2rem;
    }}
    h1 {{
      font-size: 1.8rem;
      margin-bottom: 0.5rem;
    }}
    .meta {{
      color: var(--muted);
      font-size: 0.85rem;
      margin-bottom: 1.5rem;
    }}
    .meta a {{ color: var(--accent); text-decoration: none; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--surface);
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{
      padding: 0.75rem 1rem;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }}
    th {{
      background: var(--border);
      font-weight: 600;
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
    }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover {{ background: rgba(88, 166, 255, 0.05); }}
    code {{
      background: var(--border);
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
      font-size: 0.85rem;
    }}
    a {{
      color: var(--green);
      text-decoration: none;
      font-weight: 500;
    }}
    a:hover {{ text-decoration: underline; }}
    @media (max-width: 768px) {{
      body {{ padding: 1rem; }}
      table {{ font-size: 0.85rem; }}
      th, td {{ padding: 0.5rem; }}
    }}
  </style>
</head>
<body>
  <h1>📦 CubeDvij Modpacks</h1>
  <p class="meta">
    Auto-generated from <a href="{repo_url}">{repo_slug or "repository"}</a> ·
    Updated {now} · {len(modpacks)} modpack(s)
  </p>
  <table>
    <thead>
      <tr>
        <th>Name</th>
        <th>Branch</th>
        <th>Version</th>
        <th>Platform</th>
        <th>Files</th>
        <th>Updated</th>
        <th>Changelog</th>
        <th>SHA256</th>
        <th>Download</th>
      </tr>
    </thead>
    <tbody>
{rows}    </tbody>
  </table>
</body>
</html>
"""


def main() -> None:
    output_path = "modpacks.json"
    html_path = "index.html"

    if len(sys.argv) > 1:
        output_path = sys.argv[1]
    if len(sys.argv) > 2:
        html_path = sys.argv[2]

    repo_slug = get_repo_slug()
    if repo_slug:
        print(f"🔗 Repository: {repo_slug}")

    print("🔍 Fetching remote branches…")
    branches = get_remote_branches()

    if not branches:
        print("ℹ No modpack branches found.", file=sys.stderr)
        with open(output_path, "w", encoding="utf-8") as fp:
            json.dump([], fp)
        return

    print(f"📦 Found {len(branches)} branch(es): {', '.join(branches)}")

    modpacks: list[dict] = []
    has_errors = False

    for ref in branches:
        print(f"  → Reading {ref}…")
        index = read_index_from_branch(ref)
        if index is None:
            continue

        problems = validate_index(ref, index)
        if problems:
            has_errors = True

        modpacks.append(extract_info(ref, index, repo_slug))

    modpacks.sort(key=lambda m: m["branch"])

    with open(output_path, "w", encoding="utf-8") as fp:
        json.dump(modpacks, fp, indent=2, ensure_ascii=False)
    print(f"✅ Wrote {len(modpacks)} modpack(s) to {output_path}")

    html = generate_html(modpacks, repo_slug)
    with open(html_path, "w", encoding="utf-8") as fp:
        fp.write(html)
    print(f"✅ Wrote {html_path}")

    if has_errors:
        print("⚠ Some modpacks had validation issues (see warnings above)", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
