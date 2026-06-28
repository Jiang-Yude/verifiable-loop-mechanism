#!/usr/bin/env python3
"""G-T-W Grader: machine-verifiable completion for loop tasks.

Reads a manifest (JSON) listing checks, runs them against the current
state, and emits a verdict JSON.

Core idea (from Yuta Tu, G-T-W, 2026, preprint / n=1 / not peer-reviewed):
  - A task is "done" only when the Worthy Condition holds.
  - WC = (number of P0 findings == 0). A machine decides, not the AI.
  - score (0-100) is a TREND indicator for anti-stagnation, NOT the
    completion criterion. Do not let an agent "claim done" by raising
    score while P0 remains.

Exit code: 0 if WC holds, 2 if WC fails (so a shell/hook can gate on it),
1 only if the grader itself could not run.
"""
import argparse
import datetime
import json
import pathlib
import re
import sys

SEVERITY_WEIGHT = {"P0": 10, "P1": 5, "P2": 2}


def now_taipei():
    tz = datetime.timezone(datetime.timedelta(hours=8))
    return datetime.datetime.now(tz).isoformat(timespec="seconds")


def finding(severity, code, message, path, evidence):
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "path": path,
        "evidence": evidence,
    }


# ---- check functions: each takes (root, params) and returns a list of findings ----

def check_file_exists(root, params):
    path = root / params["path"]
    if not path.exists():
        return [finding("P0", "FILE_MISSING", f'{params["path"]} not found', params["path"], "missing")]
    return []


def check_literal_count(root, params):
    """Literal substring must appear exactly `expect` times.
    Real use: dialogues.html must contain 'initFixedStars' exactly once."""
    path = root / params["path"]
    if not path.exists():
        return [finding("P0", "FILE_MISSING", f'{params["path"]} not found', params["path"], "missing")]
    needle = params.get("needle", "")
    if not needle:
        return [finding("P0", "BAD_PARAM", "literal_count needs a non-empty needle", params["path"], "empty needle")]
    text = path.read_text(encoding="utf-8", errors="replace")
    count = len(re.findall(re.escape(needle), text))
    expect = params.get("expect", 1)
    if count != expect:
        sev = params.get("severity", "P0")
        return [finding(sev, "LITERAL_COUNT",
                        f'"{params["needle"]}" expected {expect}, found {count}',
                        params["path"], f"count={count}")]
    return []


def check_min_lines(root, params):
    """Completeness proxy: file must not be empty/truncated below min_lines.
    Real use: a kanban board must have at least N rows (not silently truncated)."""
    path = root / params["path"]
    if not path.exists():
        return [finding("P0", "FILE_MISSING", f'{params["path"]} not found', params["path"], "missing")]
    n = sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
    mn = params.get("min_lines", 1)
    if n < mn:
        return [finding(params.get("severity", "P1"), "MIN_LINES",
                        f'{params["path"]} has {n} lines, expected >= {mn}',
                        params["path"], f"lines={n}")]
    return []


def check_forbid(root, params):
    """A regex pattern must NOT appear. Real use: forbid em-dash / 'truncated'."""
    path = root / params["path"]
    if not path.exists():
        return [finding("P0", "FILE_MISSING", f'{params["path"]} not found', params["path"], "missing")]
    text = path.read_text(encoding="utf-8", errors="replace")
    hits = len(re.findall(params["pattern"], text))
    if hits:
        return [finding(params.get("severity", "P1"), "FORBIDDEN_PATTERN",
                        f'forbidden /{params["pattern"]}/ found {hits}x',
                        params["path"], f"hits={hits}")]
    return []


CHECKS = {
    "file_exists": check_file_exists,
    "literal_count": check_literal_count,
    "min_lines": check_min_lines,
    "forbid": check_forbid,
}


def run(root, manifest):
    findings = []
    checks = manifest.get("checks", [])
    if not checks:
        # An empty manifest must never read as "done". Fail closed.
        findings.append(finding("P0", "EMPTY_MANIFEST", "manifest has no checks", "-", "0 checks"))
    for chk in checks:
        fn = CHECKS.get(chk.get("type"))
        if not fn:
            # A typo'd check type must fail closed, not silently pass.
            findings.append(finding("P0", "UNKNOWN_CHECK",
                                    f'unknown check type {chk.get("type")}', "-", str(chk.get("type"))))
            continue
        try:
            findings.extend(fn(root, chk))
        except Exception as exc:  # a crashed check must fail closed, not pass
            findings.append(finding("P0", "CHECK_ERROR",
                                    f'{chk.get("type")} crashed: {exc}', chk.get("path", "-"), str(exc)))
    p0 = [f for f in findings if f["severity"] == "P0"]
    p1 = [f for f in findings if f["severity"] == "P1"]
    p2 = [f for f in findings if f["severity"] == "P2"]
    score = max(0, 100
                - SEVERITY_WEIGHT["P0"] * len(p0)
                - SEVERITY_WEIGHT["P1"] * len(p1)
                - SEVERITY_WEIGHT["P2"] * len(p2))
    return {
        "schema_version": "gtw.grader.v1",
        "task_id": manifest.get("task_id", "unnamed"),
        "score": score,
        "wc": len(p0) == 0,
        "p0": p0,
        "p1": p1,
        "p2": p2,
        "checked_at": now_taipei(),
    }


def main():
    ap = argparse.ArgumentParser(description="G-T-W machine-verifiable completion grader")
    ap.add_argument("--root", required=True, help="base directory checks resolve against")
    ap.add_argument("--manifest", required=True, help="path to the manifest JSON")
    args = ap.parse_args()
    try:
        manifest = json.loads(pathlib.Path(args.manifest).read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"error": f"cannot read manifest: {exc}"}, ensure_ascii=False))
        sys.exit(1)
    verdict = run(pathlib.Path(args.root), manifest)
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    sys.exit(0 if verdict["wc"] else 2)


if __name__ == "__main__":
    main()
