"""Tests for the instruction files under prompts/, written before the author's instructions.

A run-time agent reads only prompts/, the skill of its agent tool and its workspace. These
tests hold those files to that: every path they name exists, and none of them names a folder an
agent must not open, a format that no longer exists, or a paper the agents are tested on. The
plugin files, which every person who installs the plugin is shown, are held to the same words,
and each tool's plugin file must lead that tool to its own skill.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_SKILL = ROOT / "skills/paper-chain/SKILL.md"
CODEX_SKILL = ROOT / ".agents/skills/paper-chain/SKILL.md"
SKILLS = [CLAUDE_SKILL, CODEX_SKILL]
PROMPTS = sorted((ROOT / "prompts").rglob("*.md")) + SKILLS

CLAUDE_PLUGIN = ROOT / ".claude-plugin/plugin.json"
CODEX_PLUGIN = ROOT / ".codex-plugin/plugin.json"
MARKETPLACE = ROOT / ".claude-plugin/marketplace.json"
PLUGIN_FILES = [CLAUDE_PLUGIN, CODEX_PLUGIN, MARKETPLACE]

# Words that name a paper of the person's own, one regular expression a line. The file is not
# committed, so that the public repository does not name such a paper either.
PRIVATE_WORDS = ROOT / "local/private-words.txt"

# A path into the project folder, as the instruction files write one.
PROJECT_PATH = re.compile(r"prompts/[A-Za-z0-9_./-]*[A-Za-z0-9_/-]")

FORBIDDEN = {
    "a folder a run-time agent must not open": r"\b(examples|docs|tests)/",
    "a format of the earlier design": r"\b(section|figure-or-table|theorem|manifest)\.md\b|\bmanifest\b",
    "a paper the agents are tested on": r"rlhf|yun\s*2025|yun et al|2506\.01523|arxiv",
}
if PRIVATE_WORDS.is_file():
    words = [w.strip() for w in PRIVATE_WORDS.read_text(encoding="utf-8").splitlines() if w.strip()]
    if words:
        FORBIDDEN["a paper of the person's own"] = "|".join(words)

DELETED = [
    "prompts/formats/section.md",
    "prompts/formats/figure-or-table.md",
    "prompts/formats/theorem.md",
    "prompts/formats/manifest.md",
]

EXPECTED = [
    "prompts/rules.md",
    "prompts/work-graph.md",
    "prompts/formats/source.md",
    "prompts/formats/logical-chain.md",
    "prompts/formats/review.md",
    "prompts/formats/review-log.md",
    "prompts/roles/author.md",
    "prompts/roles/reviewer.md",
    "prompts/roles/transcriber.md",
]


def name(path: Path) -> str:
    return str(path.relative_to(ROOT))


def test_the_instruction_files_of_this_design_exist():
    assert [p for p in EXPECTED if not (ROOT / p).is_file()] == []


def test_each_agent_tool_has_its_skill():
    assert [name(p) for p in SKILLS if not p.is_file()] == []


def test_the_formats_of_the_earlier_design_are_gone():
    assert [p for p in DELETED if (ROOT / p).exists()] == []


@pytest.mark.parametrize("path", PROMPTS, ids=name)
def test_every_project_path_a_file_names_exists(path):
    text = path.read_text(encoding="utf-8")
    missing = sorted({p for p in PROJECT_PATH.findall(text) if not (ROOT / p).exists()})
    assert missing == []


@pytest.mark.parametrize("path", PROMPTS + PLUGIN_FILES, ids=name)
@pytest.mark.parametrize("what", FORBIDDEN)
def test_no_file_names_what_an_agent_must_not_see(path, what):
    found = [
        f"line {number}: {line.strip()[:80]}"
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if re.search(FORBIDDEN[what], line, re.IGNORECASE)
    ]
    assert found == [], what


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def skill_files(plugin_root: Path, skill_dirs: list[str]) -> list[Path]:
    return sorted(p for d in skill_dirs for p in (plugin_root / d).glob("*/SKILL.md"))


def test_the_marketplace_lists_this_folder_as_the_plugin():
    marketplace = read_json(MARKETPLACE)
    [entry] = marketplace["plugins"]
    assert entry["source"] == "./"
    assert entry["name"] == read_json(CLAUDE_PLUGIN)["name"] == read_json(CODEX_PLUGIN)["name"]


def test_claude_code_finds_only_its_own_skill():
    """Claude Code scans skills/ and any folder the manifest adds."""
    manifest = read_json(CLAUDE_PLUGIN)
    added = manifest.get("skills", [])
    found = skill_files(ROOT, ["skills"] + ([added] if isinstance(added, str) else added))
    assert found == [CLAUDE_SKILL]


def test_codex_finds_only_its_own_skill():
    """Codex 0.162.1 took .codex-plugin/plugin.json over .claude-plugin/plugin.json and loaded only the skills it names."""
    found = skill_files(ROOT, [read_json(CODEX_PLUGIN)["skills"]])
    assert found == [CODEX_SKILL]


# The lines the starter ends the chain stage with once review-log.md reads `Chain: accepted`,
# so that a skill that asked for the chain can go on from them.
HAND_BACK = [
    "Chain accepted.",
    "Workspace: <workspace>",
    "Chain: <workspace>/logical-chain.md",
    "Source: <workspace>/source/<input>/",
]

# The four decisions the starter answers only with the person's own words, in bold in each skill.
PERSONS_DECISIONS = ["disagreement", "feedback", "acceptance", "reviewer's list of question kinds"]


def starter_section(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text.split("## The starter", 1)[1].split("\n## ", 1)[0]


@pytest.mark.parametrize("path", SKILLS, ids=name)
def test_each_skill_holds_the_hand_back_lines_in_order(path):
    lines = [line.strip() for line in starter_section(path).splitlines()]
    assert any(lines[i : i + len(HAND_BACK)] == HAND_BACK for i in range(len(lines)))


@pytest.mark.parametrize("path", SKILLS, ids=name)
@pytest.mark.parametrize("term", PERSONS_DECISIONS)
def test_each_skill_names_the_persons_decisions_to_the_starter(path, term):
    assert f"**{term}**" in starter_section(path).lower()


def test_no_tracked_file_holds_the_old_package_name():
    """The package took the name of the repository, the plugin and the marketplace."""
    import subprocess

    old_name = "paper-chain-" + "harness"
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8").split("\0")
    holding = [
        name for name in tracked
        if name and (ROOT / name).is_file()
        and old_name in (ROOT / name).read_text(encoding="utf-8", errors="ignore")
    ]
    assert holding == []


# One review per spine line. A review of a line is numbered in the order the author asks for it,
# so that a change to the spine never renames a review file.
REVIEW_FORMAT = ROOT / "prompts/formats/review.md"
INSTRUCTIONS = sorted((ROOT / "prompts").rglob("*.md")) + SKILLS
SECTION_AS_UNIT = r"section-(<NN>|\d\d)|\bsection(?:'s)? reviews?\b|\b(?:write|review) a section\b"


def test_a_line_review_and_its_second_look_are_numbered_parts():
    text = REVIEW_FORMAT.read_text(encoding="utf-8")
    assert "`reviews/part-<NN>.md`" in text
    assert "`reviews/part-<NN>.second-look.md`" in text


@pytest.mark.parametrize("path", INSTRUCTIONS, ids=name)
def test_no_instruction_takes_a_section_of_the_paper_as_the_unit_of_review(path):
    found = [
        f"line {number}: {line.strip()[:80]}"
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if re.search(SECTION_AS_UNIT, line, re.IGNORECASE)
    ]
    assert found == []


@pytest.mark.parametrize("path", INSTRUCTIONS, ids=name)
def test_no_instruction_has_a_no_steps_state(path):
    """Every spine line has steps; a line no step carries is an error the final review finds."""
    assert re.search(r"`no steps`|\b(?:or|for) no steps\b", path.read_text(encoding="utf-8")) is None


@pytest.mark.parametrize("path", SKILLS, ids=name)
def test_each_skill_names_the_kinds_of_review(path):
    kinds = "a spine review, a review of a spine line, a second look, or the final review"
    assert f"Kind of review: <{kinds}>" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", SKILLS, ids=name)
def test_each_skill_description_names_markdown(path):
    """A person or an orchestrator that has a Markdown file must find the skill by its description."""
    description = path.read_text(encoding="utf-8").split("description:", 1)[1].split("\n", 1)[0]
    assert "Markdown" in description


def test_the_codex_skill_takes_markdown_as_well_as_latex():
    assert "LaTeX source only" not in CODEX_SKILL.read_text(encoding="utf-8")
