# Changelog — deprecated-api-scan

## v0.1.1 — 2026-10-12

- Fixed: extension filter now also applies to an explicit single-file `--path`
  (previously a `data.log` file was scanned despite not matching the ext list).
- Fixed: invalid regex in a manifest entry now reports the offending API id in
  the load-time error instead of an opaque compile message.
- Self-review round: test suite grew 45 → 49 cases (added non-numeric
  `removed_in` degradation, case-sensitive literal matching, one-finding-per-
  api-per-line dedupe, deep directory walk, `--min removed` CI-gate path).

## v0.1.0 — 2026-10-11

- Initial cut (session-interrupted build): declarative manifest schema
  (id/match/match_type/severity/removed_in/replacement/message), line-level
  scanner for files and directory trees, `--target` severity escalation,
  `--min` floor filter, `--format json` CI report, text output with migration
  suggestions, bundled Python-3.12 sample manifest + legacy example, 45
  self-test cases.
