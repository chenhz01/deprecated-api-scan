# Alignment Audit (Rules 85-100 / 16 items) — deprecated-api-scan v0.1.1

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Safety/Ethics section | N/A | Not a security-research repo; no dual-use surface. Fails closed (exit 2) on unreadable/invalid manifests; read-only over sources |
| 2 | Privacy/dezero | PASS | No secrets/tokens/real names; no contact line needed; grep `(sk-\|ghp_\|api[_-]?key\s*=\s*['"][A-Za-z0-9])` → 0 hits |
| 3 | Copyright boundary | PASS | Bundled manifest states Python 3.12 removal facts (imp, distutils, ssl.wrap_socket, unittest aliases, SafeConfigParser) as short factual entries, no >50-char copied text; anchor comparisons structural; MIT LICENSE present, "zhengming contributors" |
| 4 | Fact-check annotation | PASS | Quickstart ~2 s marked [Measured] with repro `python self_test.py`; Python 3.12 removal facts flagged High-confidence in README Confidence; 2000-line scan <5 s [Measured in c06] |
| 5 | Confidence grading | PASS | Tool behavior [High ≥80%]; manifest facts [High]; line-matching sufficiency [Medium]; manifest upkeep [Low]; visible in Confidence section |
| 6 | PLAN B built-in | PASS | "Minimal Fallback (PLAN B)": grep -E one-liner CI gate with explicit statement of what is lost |
| 7 | Timeout preset | PASS | Quickstart states "~2 s" total with per-step ≈0.5 s / ≈1 s markers |
| 8 | Rule-conflict arbitration | PASS | "Design Trade-offs" opens with priority order: zero false obstacles (manifest validation over cleverness) > offline determinism > line-level precision > semantic depth |
| 9 | Version changelog | PASS | CHANGELOG.md v0.1.0 + v0.1.1; v0.1.1 lists ext-filter fix, error-attribution fix, test delta 45→49 |
| 10 | Exemption instruction | N/A | Session-level rule; static repo content not applicable |
| 11 | External-knowledge cutoff | PASS | Python 3.12 removal facts stated "as of 2026-10-12"; no forward-looking vendor claims |
| 12 | Assumption explicitness | PASS | "[Core Assumptions]" section with 4 items (static knowability, dotted-numeric versions, manifest is human-owned truth, advisory-only output) |
| 13 | Logic-check trio | PASS | self_test.py tiers: [A] functional (20), [B] exception/CLI paths (14), [C] extreme edges (15: empty file/5000-char line/unicode source+path/CRLF/2000-line timing/first+last line/8-deep walk/dedupe). Final run: `python self_test.py` → `SUMMARY: PASS 49/49` |
| 14 | Socratic question | PASS | FAQ "When NOT to use this tool?" with 4 concrete anti-use-cases (k8s yaml audit, AST-accurate analysis, in-editor UX, runtime-config-dependent deprecations) |
| 15 | Pareto improvement | PASS | v0.1.1: test count 45→49 (+8.9%) plus 2 correctness fixes (ext filter on file paths, api-id error attribution); documented in CHANGELOG, suite re-run green |
| 16 | Ultimate fallback (≤60-word opener) | PASS | First paragraph = 58 words, contains what/who-needs-it judgment sentence |

Second-order effects (rule 16 bonus): PASS — "Limits & Second-order Effects" lists manifest rot/stale entries, comment/string false positives, dynamic-usage blindness.

Scan evidence: `grep -rEn "(sk-\|ghp_\|api[_-]?key\s*=\s*['\"][A-Za-z0-9])" .` → 0 hits; `python self_test.py` → `SUMMARY: PASS 49/49`.
