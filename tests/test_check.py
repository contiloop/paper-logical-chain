"""Tests for scripts/check.py, written before the script.

The workspaces here are made up on purpose: the test is of the script's own logic.
"""
import subprocess
import sys
from pathlib import Path

import pytest

import check

ROOT = Path(__file__).resolve().parent.parent

PAPER = """## 1 Introduction

<a id="s1-p1"></a>
First paragraph.

<a id="theorem-4"></a>
**Theorem 4.** A statement.

<a id="figure-1"></a>
![Figure 1](figures/figure-1.png)
"""

GOOD_CHAIN = """# Logical chain

1. <a id="step-1"></a>**First.** It rests on [§1 ¶1](source/kim2030/paper.md#s1-p1) and
   [Theorem 4](<source/kim2030/paper.md#theorem-4> "the statement").

2. <a id="step-2"></a>**Second.** A consequence of [step 1](#step-1), drawn in
   [Figure 1](source/kim2030/figures/figure-1.png). See also <https://example.org> and
   [a site](https://example.org/page#part).
"""


def make_workspace(tmp_path: Path, chain: str | None) -> Path:
    ws = tmp_path / "workspace"
    src = ws / "source" / "kim2030"
    (src / "figures").mkdir(parents=True)
    (src / "paper.md").write_text(PAPER, encoding="utf-8")
    (src / "figures" / "figure-1.png").write_bytes(b"\x89PNG")
    if chain is not None:
        (ws / "logical-chain.md").write_text(chain, encoding="utf-8")
    return ws


def findings(tmp_path: Path, chain: str):
    return check.check_workspace(make_workspace(tmp_path, chain))


def test_a_chain_whose_links_all_resolve_passes(tmp_path):
    ws = make_workspace(tmp_path, GOOD_CHAIN)
    assert check.check_workspace(ws) == []
    assert check.main([str(ws)]) == 0
    report = (ws / "check-report.md").read_text(encoding="utf-8")
    assert "Result: pass" in report
    assert "None." in report


def test_a_link_to_a_missing_file_is_reported(tmp_path):
    found = findings(tmp_path, "1. <a id=\"step-1\"></a>See [x](source/kim2030/other.md#s1-p1).\n")
    assert len(found) == 1
    assert found[0].target == "source/kim2030/other.md#s1-p1"
    assert "file not found" in found[0].reason


def test_a_link_to_a_missing_anchor_is_reported(tmp_path):
    found = findings(tmp_path, "1. <a id=\"step-1\"></a>See [x](source/kim2030/paper.md#s9-p4).\n")
    assert len(found) == 1
    assert "no anchor `s9-p4`" in found[0].reason


def test_a_link_to_a_missing_image_is_reported(tmp_path):
    found = findings(tmp_path, "1. <a id=\"step-1\"></a>See [fig](source/kim2030/figures/figure-2.png).\n")
    assert len(found) == 1
    assert "file not found" in found[0].reason


def test_a_link_to_a_missing_step_is_reported(tmp_path):
    found = findings(tmp_path, "1. <a id=\"step-1\"></a>As [step 7](#step-7) says.\n")
    assert len(found) == 1
    assert "no anchor `step-7`" in found[0].reason


def test_the_line_of_each_finding_is_given(tmp_path):
    chain = "# Chain\n\n1. <a id=\"step-1\"></a>Fine.\n\n2. <a id=\"step-2\"></a>See [x](missing.md).\n"
    found = findings(tmp_path, chain)
    assert [f.line for f in found] == [5]


def test_links_in_code_are_ignored(tmp_path):
    chain = (
        "1. <a id=\"step-1\"></a>A sample: `[x](missing.md)`.\n\n"
        "```md\n[y](also-missing.md#nowhere)\n```\n"
    )
    assert findings(tmp_path, chain) == []


def test_links_to_other_sites_are_ignored(tmp_path):
    chain = "1. <a id=\"step-1\"></a>[a](https://example.org/x#y) [b](http://example.org) [c](mailto:a@b.org)\n"
    assert findings(tmp_path, chain) == []


def test_an_encoded_path_and_a_link_title_resolve(tmp_path):
    ws = make_workspace(tmp_path, None)
    (ws / "source" / "kim2030" / "part two.md").write_text('<a id="s2-p1"></a>\nText.\n', encoding="utf-8")
    (ws / "logical-chain.md").write_text(
        '1. <a id="step-1"></a>[x](source/kim2030/part%20two.md#s2-p1 "title") '
        "and [y](<source/kim2030/part two.md#s2-p1>).\n",
        encoding="utf-8",
    )
    assert check.check_workspace(ws) == []


def test_a_missing_chain_fails(tmp_path):
    ws = make_workspace(tmp_path, None)
    assert check.main([str(ws)]) == 1
    report = (ws / "check-report.md").read_text(encoding="utf-8")
    assert "Result: fail" in report
    assert "logical-chain.md" in report


def test_the_report_lists_each_finding_and_the_command_exits_1(tmp_path):
    chain = (
        "1. <a id=\"step-1\"></a>[x](source/kim2030/paper.md#s9-p4)\n"
        "2. <a id=\"step-2\"></a>[fig](source/kim2030/figures/figure-2.png)\n"
    )
    ws = make_workspace(tmp_path, chain)
    done = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check.py"), str(ws)],
        capture_output=True, text=True,
    )
    assert done.returncode == 1
    report = (ws / "check-report.md").read_text(encoding="utf-8")
    assert "Result: fail" in report
    assert "- line 1: `source/kim2030/paper.md#s9-p4`" in report
    assert "- line 2: `source/kim2030/figures/figure-2.png`" in report


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_asking_for_help_prints_the_usage_and_is_not_an_error(flag, capsys):
    assert check.main([flag]) == 0
    assert "Usage:" in capsys.readouterr().out
