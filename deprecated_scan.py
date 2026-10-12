#!/usr/bin/env python3
"""deprecated-api-scan: declarative deprecation manifests + static source matching.

A manifest lists deprecated/removed APIs as declarative entries (literal or
regex match, severity, removed_in version, replacement, message). The scanner
matches source files line-by-line, escalates severity when a `--target`
version has reached an entry's `removed_in`, and prints findings with
migration suggestions. Pure stdlib, offline.
"""
import argparse
import json
import os
import re
import sys

MANIFEST_VERSION = 1
DEFAULT_EXTS = [".py", ".js", ".ts"]
SEV_ORDER = {"info": 0, "deprecated": 1, "removed": 2}
EVIDENCE_LIMIT = 120


# ---------------------------------------------------------------- manifest

def vkey(version):
    """'3.12' -> (3, 12); non-numeric parts -> None (uncomparable)."""
    if not isinstance(version, str) or not version.strip():
        return None
    parts = []
    for p in version.strip().split("."):
        if not p.isdigit():
            return None
        parts.append(int(p))
    return tuple(parts)


def prepare_manifest(data):
    """Validate a manifest dict -> list of prepared API entries."""
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    apis = data.get("apis")
    if not isinstance(apis, list):
        raise ValueError("manifest must contain an 'apis' list")
    prepared = []
    for i, api in enumerate(apis):
        if not isinstance(api, dict) or "id" not in api or "match" not in api:
            raise ValueError("api entry %d: requires 'id' and 'match'" % i)
        kind = api.get("match_type", "regex")
        if kind == "regex":
            try:
                matcher = re.compile(api["match"])
            except re.error as e:
                raise ValueError("api %r: invalid regex: %s" % (api["id"], e))
        elif kind == "literal":
            matcher = re.compile(re.escape(api["match"]))
        else:
            raise ValueError("api %r: match_type must be 'regex' or 'literal'"
                             % (api["id"],))
        sev = api.get("severity", "deprecated")
        if sev not in SEV_ORDER:
            raise ValueError("api %r: severity must be one of %s"
                             % (api["id"], ", ".join(SEV_ORDER)))
        entry = dict(api)
        entry["_matcher"] = matcher
        prepared.append(entry)
    return prepared


def load_manifest(path):
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError("invalid manifest JSON: %s" % e)
    return prepare_manifest(data)


def effective_severity(api, target):
    """Escalate to 'removed' when target >= removed_in."""
    sev = api.get("severity", "deprecated")
    rin, tv, rv = api.get("removed_in"), vkey(target), vkey(api.get("removed_in"))
    if tv is not None and rv is not None and rv <= tv:
        return "removed"
    return sev


# ---------------------------------------------------------------- scanning

def scan_text(text, apis, target=None):
    """Scan one text blob -> list of findings (one per api per matching line)."""
    findings = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        for api in apis:
            if api["_matcher"].search(raw):
                findings.append({
                    "line": lineno,
                    "api": api["id"],
                    "severity": effective_severity(api, target),
                    "evidence": raw.strip()[:EVIDENCE_LIMIT],
                    "replacement": api.get("replacement", ""),
                    "message": api.get("message", ""),
                    "removed_in": api.get("removed_in", ""),
                })
    return findings


def iter_source_files(path, exts):
    if os.path.isfile(path):
        if os.path.splitext(path)[1].lower() in exts:
            yield path
        return
    if not os.path.isdir(path):
        raise OSError("path not found: %s" % path)
    for root, _dirs, files in os.walk(path):
        for name in sorted(files):
            if os.path.splitext(name)[1].lower() in exts:
                yield os.path.join(root, name)


def scan_path(path, apis, target=None, exts=None):
    exts = set(exts if exts is not None else DEFAULT_EXTS)
    all_findings = []
    for fpath in iter_source_files(path, exts):
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        for f in scan_text(text, apis, target):
            f["file"] = fpath
            all_findings.append(f)
    return all_findings


# ---------------------------------------------------------------- CLI

def _print_text(findings):
    for f in findings:
        loc = "%s:%d" % (f["file"], f["line"])
        print("[%s] %s  %s (%s)" % (f["severity"].upper(), loc, f["api"],
                                    f["removed_in"] or "no removal version"))
        if f["replacement"]:
            print("    migrate to: %s" % f["replacement"])
        if f["message"]:
            print("    note: %s" % f["message"])
        print("    | %s" % f["evidence"])
    print("findings: %d" % len(findings))


def cmd_scan(args):
    apis = load_manifest(args.manifest)
    findings = scan_path(args.path, apis, target=args.target,
                         exts=[e if e.startswith(".") else "." + e
                               for e in args.ext.split(",")] if args.ext else None)
    floor = SEV_ORDER[args.min]
    findings = [f for f in findings if SEV_ORDER[f["severity"]] >= floor]
    if args.format == "json":
        print(json.dumps({"findings": findings,
                          "count": len(findings),
                          "target": args.target}, indent=2))
    else:
        _print_text(findings)
    return 1 if findings else 0


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="deprecated-api-scan",
        description="Scan sources against a declarative deprecation manifest.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="scan a file or directory")
    s.add_argument("--manifest", required=True)
    s.add_argument("--path", required=True)
    s.add_argument("--target", help="version to escalate removed_in against (e.g. 3.12)")
    s.add_argument("--format", choices=["text", "json"], default="text")
    s.add_argument("--min", choices=list(SEV_ORDER), default="info",
                   help="minimum severity to report")
    s.add_argument("--ext", help="comma-separated file extensions (default .py,.js,.ts)")
    s.set_defaults(fn=cmd_scan)
    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except (ValueError, OSError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
