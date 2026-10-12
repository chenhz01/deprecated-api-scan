#!/usr/bin/env python3
"""Self-test for deprecated-api-scan. Run: python self_test.py"""
import contextlib
import io
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deprecated_scan as ds

TESTS = []


def t(fn):
    TESTS.append(fn)
    return fn


TD = None
SAMPLE = os.path.join(HERE, "manifests", "python_stdlib_sample.json")
EXAMPLE = os.path.join(HERE, "examples", "legacy_app.py")


def setup():
    global TD
    TD = tempfile.mkdtemp(prefix="das_test_")


def wp(name):
    return os.path.join(TD, name)


def wj(name, obj):
    p = wp(name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return p


def wt(name, text):
    p = wp(name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    code = None
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = ds.main(argv)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 0
    return code, out.getvalue(), err.getvalue()


APIS = None


def get_apis():
    global APIS
    if APIS is None:
        APIS = ds.load_manifest(SAMPLE)
    return APIS


def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return
    raise AssertionError("expected %s" % exc.__name__)


# ---------------- [A] functional

@t
def a01_literal_match():
    apis = ds.prepare_manifest({"apis": [{"id": "x", "match": "old_fn(",
                                          "match_type": "literal"}]})
    f = ds.scan_text("y = old_fn(1)\n", apis)
    assert len(f) == 1 and f[0]["line"] == 1 and f[0]["api"] == "x"


@t
def a02_regex_match():
    f = ds.scan_text("import imp  # legacy\n", get_apis())
    assert any(x["api"] == "py-imp-module" for x in f)


@t
def a03_line_numbers():
    src = "\n\n\nssl.wrap_socket(s)\n"
    f = ds.scan_text(src, get_apis())
    assert f[0]["line"] == 4


@t
def a04_multiple_apis_same_file():
    src = "import imp\nimport distutils\n"
    f = ds.scan_text(src, get_apis())
    ids_ = {x["api"] for x in f}
    assert {"py-imp-module", "py-distutils"} <= ids_


@t
def a05_escalation_target_reached():
    apis = ds.prepare_manifest({"apis": [{"id": "a", "match": "zz(",
                                          "match_type": "literal",
                                          "severity": "deprecated",
                                          "removed_in": "3.12"}]})
    f = ds.scan_text("zz()\n", apis, target="3.12")
    assert f[0]["severity"] == "removed"


@t
def a06_no_escalation_before_target():
    apis = ds.prepare_manifest({"apis": [{"id": "a", "match": "zz(",
                                          "match_type": "literal",
                                          "severity": "deprecated",
                                          "removed_in": "3.12"}]})
    f = ds.scan_text("zz()\n", apis, target="3.10")
    assert f[0]["severity"] == "deprecated"


@t
def a07_min_severity_filter():
    f = ds.scan_text(open(EXAMPLE, encoding="utf-8").read(), get_apis(),
                     target="3.12")
    rem = [x for x in f if x["severity"] == "removed"]
    assert rem and all(x["severity"] in ("deprecated", "removed") for x in f)


@t
def a08_json_format_parseable():
    code, out, _ = run_cli(["scan", "--manifest", SAMPLE, "--path", EXAMPLE,
                            "--format", "json", "--target", "3.12"])
    data = json.loads(out)
    assert code == 1 and data["count"] >= 5 and data["findings"][0]["file"]


@t
def a09_text_format_lines():
    code, out, _ = run_cli(["scan", "--manifest", SAMPLE, "--path", EXAMPLE])
    assert "findings:" in out and "migrate to: importlib" in out


@t
def a10_dir_walk_recursive():
    sub = wp("deep/nested")
    os.makedirs(sub)
    p = os.path.join(sub, "m.py")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("import imp\n")
    code, out, _ = run_cli(["scan", "--manifest", SAMPLE, "--path", wp("deep")])
    assert code == 1 and p.replace("\\", "/") in out.replace("\\", "/")


@t
def a11_ext_filter():
    p = wt("data.log", "import imp\n")  # not in default exts
    code, _, _ = run_cli(["scan", "--manifest", SAMPLE, "--path", p])
    assert code == 0


@t
def a12_ext_override():
    p = wt("data.log", "import imp\n")
    code, _, _ = run_cli(["scan", "--manifest", SAMPLE, "--path", p,
                          "--ext", ".log"])
    assert code == 1


@t
def a13_evidence_trimmed():
    f = ds.scan_text("    ssl.wrap_socket(s)   # padded\n", get_apis())
    assert f[0]["evidence"] == "ssl.wrap_socket(s)   # padded"


@t
def a14_replacement_present():
    f = ds.scan_text("import imp\n", get_apis())
    assert f[0]["replacement"] == "importlib"


@t
def a15_message_present():
    f = ds.scan_text("import imp\n", get_apis())
    assert "3.12" in f[0]["message"]


@t
def a16_cli_exit0_clean_source():
    p = wt("clean.py", "import json\nprint(json.dumps({}))\n")
    code, out, _ = run_cli(["scan", "--manifest", SAMPLE, "--path", p])
    assert code == 0 and "findings: 0" in out


@t
def a17_cli_exit1_findings():
    code, _, _ = run_cli(["scan", "--manifest", SAMPLE, "--path", EXAMPLE])
    assert code == 1


@t
def a18_sample_manifest_valid():
    with open(SAMPLE, encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["manifest_version"] == 1 and len(data["apis"]) >= 5


@t
def a19_clean_code_no_findings():
    apis = ds.prepare_manifest({"apis": [{"id": "x", "match": "old_fn(",
                                          "match_type": "literal"}]})
    assert ds.scan_text("new_fn()\n", apis) == []


@t
def a20_finding_keys():
    f = ds.scan_text("import imp\n", get_apis())
    for k in ("line", "api", "severity", "evidence", "replacement", "message",
              "removed_in"):
        assert k in f[0], k

# ---------------- [B] exception paths

@t
def b01_missing_manifest_exit2():
    code, _, err = run_cli(["scan", "--manifest", wp("nope.json"),
                            "--path", EXAMPLE])
    assert code == 2 and "error" in err


@t
def b02_malformed_manifest_json():
    p = wt("m.json", "{bad")
    code, _, _ = run_cli(["scan", "--manifest", p, "--path", EXAMPLE])
    assert code == 2


@t
def b03_manifest_not_object():
    raises(ValueError, ds.prepare_manifest, [1, 2])


@t
def b04_apis_not_list():
    raises(ValueError, ds.prepare_manifest, {"apis": "x"})


@t
def b05_entry_missing_fields():
    raises(ValueError, ds.prepare_manifest, {"apis": [{"id": "x"}]})


@t
def b06_invalid_regex():
    raises(ValueError, ds.prepare_manifest,
           {"apis": [{"id": "x", "match": "([bad"}]})


@t
def b07_bad_match_type():
    raises(ValueError, ds.prepare_manifest,
           {"apis": [{"id": "x", "match": "a", "match_type": "fuzzy"}]})


@t
def b08_bad_severity():
    raises(ValueError, ds.prepare_manifest,
           {"apis": [{"id": "x", "match": "a", "severity": "fatal"}]})


@t
def b09_missing_path_exit2():
    code, _, _ = run_cli(["scan", "--manifest", SAMPLE,
                          "--path", wp("gone_dir")])
    assert code == 2


@t
def b10_bad_min_choice_exit2():
    code, _, _ = run_cli(["scan", "--manifest", SAMPLE, "--path", EXAMPLE,
                          "--min", "critical"])
    assert code == 2


@t
def b11_no_subcommand_exit2():
    code, _, _ = run_cli([])
    assert code == 2


@t
def b12_empty_manifest_no_findings():
    p = wj("m.json", {"apis": []})
    code, out, _ = run_cli(["scan", "--manifest", p, "--path", EXAMPLE])
    assert code == 0 and "findings: 0" in out


@t
def b13_optional_fields_tolerated():
    apis = ds.prepare_manifest({"apis": [{"id": "bare", "match": "bare(",
                                          "match_type": "literal"}]})
    f = ds.scan_text("bare()\n", apis)
    assert f[0]["replacement"] == "" and f[0]["removed_in"] == ""


@t
def b14_undecodable_file_tolerated():
    p = wp("bin.py")
    with open(p, "wb") as fh:
        fh.write(b"\xff\xfe import \x00imp\n")
    code, _, _ = run_cli(["scan", "--manifest", SAMPLE, "--path", p])
    assert code in (0, 1)  # replaced bytes, never crashes

# ---------------- [C] extreme edges

@t
def c01_empty_file():
    assert ds.scan_text("", get_apis()) == []


@t
def c02_long_line_evidence_capped():
    src = "ssl.wrap_socket(" + "x" * 5000 + ")\n"
    f = ds.scan_text(src, get_apis())
    assert len(f) == 1 and len(f[0]["evidence"]) <= ds.EVIDENCE_LIMIT


@t
def c03_unicode_source():
    src = "# 中文注释\n值 = ssl.wrap_socket(s)  # เก่า\n"
    f = ds.scan_text(src, get_apis())
    assert f[0]["line"] == 2 and "เก่า" in f[0]["evidence"]


@t
def c04_unicode_path():
    p = wp("旧代码.py")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("import imp\n")
    f = ds.scan_path(p, get_apis())
    assert f[0]["file"].endswith("旧代码.py")


@t
def c05_crlf_line_endings():
    src = "import imp\r\nssl.wrap_socket(s)\r\n"
    f = ds.scan_text(src, get_apis())
    assert [x["line"] for x in f] == [1, 2]


@t
def c06_big_file_timing():
    src = "\n".join("# filler %d" % i for i in range(2000)) + \
        "\nimport imp\n"
    t0 = time.time()
    f = ds.scan_text(src, get_apis())
    assert time.time() - t0 < 5.0 and f[0]["line"] == 2001


@t
def c07_match_first_and_last_line():
    src = "import imp\nmiddle\nssl.wrap_socket(s)\n"
    f = ds.scan_text(src, get_apis())
    assert f[0]["line"] == 1 and f[-1]["line"] == 3


@t
def c08_case_sensitive_literal():
    apis = ds.prepare_manifest({"apis": [{"id": "x", "match": "OldFn(",
                                          "match_type": "literal"}]})
    assert ds.scan_text("oldfn()\n", apis) == []
    assert ds.scan_text("OldFn()\n", apis)


@t
def c09_non_numeric_removed_in_no_escalation():
    apis = ds.prepare_manifest({"apis": [{"id": "x", "match": "zz(",
                                          "match_type": "literal",
                                          "severity": "deprecated",
                                          "removed_in": "next-year"}]})
    f = ds.scan_text("zz()\n", apis, target="9999")
    assert f[0]["severity"] == "deprecated"


@t
def c10_no_removed_in_no_escalation():
    apis = ds.prepare_manifest({"apis": [{"id": "x", "match": "zz(",
                                          "match_type": "literal",
                                          "severity": "deprecated"}]})
    f = ds.scan_text("zz()\n", apis, target="3.12")
    assert f[0]["severity"] == "deprecated"


@t
def c11_one_finding_per_api_per_line():
    src = "imp.load_source('a', 'b')  # imp.load_source again imp.load_source\n"
    f = ds.scan_text(src, get_apis())
    assert len([x for x in f if x["api"] == "py-imp-module"]) == 1


@t
def c12_deep_dir_walk():
    d = wp("l0")
    cur = d
    for i in range(8):
        cur = os.path.join(cur, "l%d" % i)
    os.makedirs(cur)
    with open(os.path.join(cur, "x.py"), "w", encoding="utf-8") as fh:
        fh.write("import imp\n")
    code, _, _ = run_cli(["scan", "--manifest", SAMPLE, "--path", d])
    assert code == 1


@t
def c13_min_removed_strict():
    code, out, _ = run_cli(["scan", "--manifest", SAMPLE, "--path", EXAMPLE,
                            "--min", "removed", "--format", "json",
                            "--target", "3.12"])
    data = json.loads(out)
    assert data["count"] >= 4
    assert all(f["severity"] == "removed" for f in data["findings"])


@t
def c14_report_serializable():
    f = ds.scan_text("import imp\n", get_apis(), target="3.12")
    json.loads(json.dumps(f))


@t
def c15_vkey_shapes():
    assert ds.vkey("3.12") == (3, 12)
    assert ds.vkey("3.9") < ds.vkey("3.12")
    assert ds.vkey("beta") is None and ds.vkey("") is None


def main():
    setup()
    ok = 0
    fails = []
    for fn in TESTS:
        try:
            fn()
            ok += 1
        except Exception as e:  # noqa: BLE001
            fails.append((fn.__name__, repr(e)))
    for name, e in fails:
        print("FAIL %s: %s" % (name, e))
    total = len(TESTS)
    print("SUMMARY: %s %d/%d" % ("PASS" if not fails else "FAIL", ok, total))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
