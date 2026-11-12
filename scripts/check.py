"""Check that every link in a workspace's logical chain resolves.

Takes:    the path of a workspace.
Writes:   check-report.md in that workspace.
Returns:  exit code 0 when every link resolves, 1 otherwise.

A link resolves when its file exists and, if it names an anchor, the file holds
that anchor. A link with only an anchor, such as #step-3, points into the chain
itself. Links to other sites are not checked, and neither is anything inside code.

Usage:  uv run python scripts/check.py <workspace>
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

CHAIN = "logical-chain.md"
REPORT = "check-report.md"

# [text](target) or [text](<target with spaces> "title"); images are links too.
LINK = re.compile(r"\[(?:[^\[\]]|\[[^\[\]]*\])*\]\(\s*(<[^>]*>|[^\s)]+)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
ANCHOR = re.compile(r"""\b(?:id|name)\s*=\s*["']([^"']+)["']""")
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")
OTHER_SITE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


@dataclass(frozen=True)
class Finding:
    line: int
    target: str
    reason: str


def _lines_outside_code(text: str):
    """Yield (line number, line) with fenced blocks skipped and inline code blanked."""
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield number, INLINE_CODE.sub("", line)


def _anchors(path: Path, cache: dict[Path, set[str]]) -> set[str]:
    if path not in cache:
        text = path.read_text(encoding="utf-8", errors="replace")
        cache[path] = set(ANCHOR.findall(text))
    return cache[path]


def check_workspace(workspace: Path) -> list[Finding]:
    """Return one finding for each link of the chain that does not resolve."""
    workspace = Path(workspace)
    chain = workspace / CHAIN
    if not chain.is_file():
        return [Finding(0, CHAIN, f"`{CHAIN}` not found in the workspace")]

    cache: dict[Path, set[str]] = {}
    found: list[Finding] = []
    for number, line in _lines_outside_code(chain.read_text(encoding="utf-8")):
        for match in LINK.finditer(line):
            target = match.group(1)
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            if OTHER_SITE.match(target):
                continue
            path_part, _, fragment = target.partition("#")
            file = chain if not path_part else (chain.parent / unquote(path_part))
            shown = path_part or CHAIN
            if not file.exists():
                found.append(Finding(number, target, "file not found"))
            elif fragment and file.is_file() and unquote(fragment) not in _anchors(file, cache):
                found.append(Finding(number, target, f"no anchor `{unquote(fragment)}` in `{shown}`"))
    return found


def write_report(workspace: Path, found: list[Finding]) -> None:
    lines = ["# Check report", "", f"Result: {'fail' if found else 'pass'}", "", "## Links that do not resolve"]
    if found:
        for f in found:
            where = f"line {f.line}: " if f.line else ""
            lines.append(f"- {where}`{f.target}` — {f.reason}")
    else:
        lines.append("None.")
    (Path(workspace) / REPORT).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv in (['-h'], ['--help']):
        print(__doc__)
        return 0
    if len(argv) != 1:
        print(__doc__)
        return 2
    workspace = Path(argv[0])
    if not workspace.is_dir():
        print(f"not a folder: {workspace}")
        return 2
    found = check_workspace(workspace)
    write_report(workspace, found)
    print(f"{'fail' if found else 'pass'}: {len(found)} link(s) do not resolve; report in {workspace / REPORT}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
