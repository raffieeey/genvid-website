#!/usr/bin/env python3
"""Grok 4.6 worker dispatch for the GENVID website build.

Usage:
  grok_dispatch.py --smoke
  grok_dispatch.py <task-file.md> <tag> [--max-tokens N]

Reads xAI OAuth token from ~/.hermes/auth.json, auto-refreshes once on 403,
calls api.x.ai/v1/chat/completions with model grok-4.6, saves the raw reply to
build/grok/<tag>.md, then parses `### FILE: <relpath>` blocks and writes each
file under the repo root (~/genvid-website). Path traversal is rejected.
Never prints token values (lengths only).
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

AUTH = Path.home() / ".hermes" / "auth.json"
REPO = Path.home() / "genvid-website"
BUILD = REPO / "build" / "grok"
API = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-4.6"

SYSTEM = (
    "You are Grok, a senior front-end engineer and product designer. "
    "You are building ONE deliverable for a real static marketing website. "
    "Follow the output contract EXACTLY: emit each file as a block starting with a line "
    "'### FILE: <relative path>' followed by the complete file content. "
    "No commentary before the first file block. End with a '## BUILD NOTES' section. "
    "Never invent facts beyond the provided spec, never add emojis, never use lorem ipsum, "
    "never reference files that are not in the manifest."
)


def load_token():
    d = json.loads(AUTH.read_text())
    entry = d["credential_pool"]["xai-oauth"][0]
    return entry.get("access_token"), entry


def refresh_token():
    try:
        from hermes_cli import auth as ha  # available when run under hermes venv
    except Exception as exc:  # pragma: no cover
        print("REFRESH_IMPORT_FAILED:", exc)
        return None
    import inspect

    entry = json.loads(AUTH.read_text())["credential_pool"]["xai-oauth"][0]
    fn = getattr(ha, "refresh_xai_oauth_pure", None)
    if fn is None:
        cands = [n for n in dir(ha) if "refresh" in n.lower() and "xai" in n.lower()]
        print("REFRESH_CANDIDATES:", cands)
        if not cands:
            return None
        fn = getattr(ha, cands[0])
    try:
        print("REFRESH_SIG:", inspect.signature(fn))
    except Exception:
        pass
    out = fn(entry["access_token"], entry["refresh_token"], timeout_seconds=30)
    new_access = new_refresh = new_id = None
    if isinstance(out, dict):
        t = out.get("tokens") if isinstance(out.get("tokens"), dict) else out
        new_access = t.get("access_token")
        new_refresh = t.get("refresh_token")
        new_id = t.get("id_token")
    elif isinstance(out, (tuple, list)):
        new_access = out[0] if len(out) > 0 else None
        new_refresh = out[1] if len(out) > 1 else None
        new_id = out[2] if len(out) > 2 else None
    if not new_access:
        print("REFRESH_NO_ACCESS:", type(out).__name__)
        return None
    bak = AUTH.with_name("auth.json.bak-grok")
    bak.write_text(AUTH.read_text())
    d = json.loads(AUTH.read_text())
    e = d["credential_pool"]["xai-oauth"][0]
    e["access_token"] = new_access
    if new_refresh:
        e["refresh_token"] = new_refresh
    if new_id:
        e["id_token"] = new_id
    e["last_refresh"] = int(time.time())
    e["last_status"] = "ok"
    for k in list(e.keys()):
        if k.startswith("last_error"):
            e.pop(k, None)
    tmp = AUTH.with_name("auth.json.tmp-grok")
    tmp.write_text(json.dumps(d, indent=2))
    os.replace(tmp, AUTH)
    print("REFRESH_OK access_len:", len(new_access))
    return new_access


def call_api(token, user_text, max_tokens, timeout=1800):
    body = {
        "model": MODEL,
        "stream": False,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_text},
        ],
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "Hermes-Agent/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def api_with_refresh(user_text, max_tokens):
    token, _ = load_token()
    for attempt in (1, 2):
        try:
            return call_api(token, user_text, max_tokens)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode()[:300]
            print("HTTP_ERROR", exc.code, detail)
            if exc.code == 403 and attempt == 1:
                token = refresh_token()
                if token:
                    continue
            raise
        except Exception as exc:
            print("TRANSIENT", type(exc).__name__, exc)
            if attempt == 1:
                time.sleep(5)
                continue
            raise
    raise RuntimeError("unreachable")


def smoke():
    resp = api_with_refresh("Reply with exactly: SMOKE_OK", 16)
    content = resp["choices"][0]["message"]["content"].strip()
    print("SMOKE_RESULT:", content)
    print("USAGE:", resp.get("usage"))
    return 0 if "SMOKE_OK" in content else 1


def write_outputs(text, tag):
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / (tag + ".md")).write_text(text)
    body_text = text.split("\n## BUILD NOTES")[0]
    parts = re.split(r"^### FILE:\s*", body_text, flags=re.M)[1:]
    written = []
    for part in parts:
        lines = part.splitlines()
        if not lines:
            continue
        rel = lines[0].strip().strip("`").strip()
        body = "\n".join(lines[1:]).strip("\n")
        if body.startswith("```"):
            body = re.sub(r"^```[A-Za-z0-9_-]*\n", "", body)
            body = re.sub(r"\n```\s*$", "", body)
        if rel.startswith("/") or ".." in Path(rel).parts:
            print("REJECTED_PATH:", rel)
            continue
        target = REPO / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body + "\n")
        written.append((rel, len(body)))
    print("FILES_WRITTEN:", json.dumps(written))


def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        return 2
    if args[0] == "--smoke":
        return smoke()
    task_file = Path(args[0])
    tag = args[1] if len(args) > 1 else "worker"
    max_tokens = 49152
    if "--max-tokens" in args:
        max_tokens = int(args[args.index("--max-tokens") + 1])
    user_text = task_file.read_text()
    print("DISPATCH tag=%s task=%s max_tokens=%d chars=%d" % (tag, task_file, max_tokens, len(user_text)))
    resp = api_with_refresh(user_text, max_tokens)
    choice = resp["choices"][0]
    content = choice["message"]["content"]
    print("FINISH_REASON:", choice.get("finish_reason"))
    print("USAGE:", resp.get("usage"))
    print("OUTPUT_CHARS:", len(content))
    write_outputs(content, tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
