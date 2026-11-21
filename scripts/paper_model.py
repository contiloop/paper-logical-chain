"""The paper as a reader hands it to the convert script.

A reader (`latex_reader` for LaTeX source, `markdown_reader` for Markdown) reads a
paper and returns a Paper. The convert script names the paragraphs, writes the files
and makes the checks from the Paper alone, so a reader can be replaced without changing
the script. A PDF has no reader: an agent transcribes it, and `transcription` reads
what the agent wrote.

Text is the paper's text as the reader gives it; from LaTeX source it is the LaTeX as
written, and from Markdown the Markdown as written. The reader names every item's
anchors. The script never computes a number.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Every other kind of item is a statement, named as the paper names it in lower case:
# "theorem", "lemma", "proposition", "assumption", "definition", "remark" and so on.
NOT_STATEMENTS = ("equation", "figure", "table", "algorithm", "reference")


class ConversionError(Exception):
    """The paper could not be converted at all."""


def anchor_name(label: str) -> str:
    """A label of the source as a link anchor: characters a link cannot hold become hyphens."""
    return re.sub(r"[^A-Za-z0-9:._-]+", "-", label.strip())


@dataclass
class Heading:
    """The heading of a section or of a part of one."""
    role: str            # "abstract", "main", "appendix", "references", or "other" for a section without a number
    level: int           # 1 for a top-level section, 2 and more for the parts inside it
    number: str | None   # "3", "C.1": its place among the sections; None when it has none
    title: str
    labels: list[str] = field(default_factory=list)   # anchors that lead here


@dataclass
class RunIn:
    """A heading that starts a paragraph's line, such as **Convergence guarantee.**"""
    title: str
    labels: list[str] = field(default_factory=list)   # anchors that lead here


@dataclass
class Raw:
    """Text that is neither a paragraph nor an item, such as layout commands. Written as it is."""
    text: str
    labels: list[str] = field(default_factory=list)


@dataclass
class Item:
    """A statement, an equation, a figure, a table, an algorithm or a reference-list entry."""
    kind: str                    # one of NOT_STATEMENTS, or the kind of a statement
    anchors: list[str]           # its labels in the source, or one name made from its kind and place
    body: list[str | Item] = field(default_factory=list)   # its text, and the items inside it, in order
    words: str = ""              # what its row of the index shows: a caption, or the start of its text
    images: list[Path] = field(default_factory=list)       # a figure's image files in the paper's source


@dataclass
class Paragraph:
    """A paragraph: its text, and the items that stand inside it, in order."""
    parts: list[str | Item] = field(default_factory=list)
    words: str = ""              # the start of its text, for its row of the index
    labels: list[str] = field(default_factory=list)   # anchors that lead here


@dataclass
class Reference:
    """A cross-reference or a citation in the paper's text."""
    anchor: str          # the anchor it must lead to
    written: str         # as the paper wrote it, such as \\ref{thm:main}


@dataclass
class Paper:
    title: str = ""
    # What stands before the text: from LaTeX, the macro definitions; from Markdown, the front matter.
    preamble: str = ""
    preamble_language: str = "latex"   # the language paper.md names on the preamble's code fence
    blocks: list[Heading | RunIn | Raw | Paragraph | Item] = field(default_factory=list)   # in the paper's order
    references: list[Reference] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)   # included files and figure files that were not found
    # What the reader could not do for an item, in its own words, by the item's anchor, such as an image
    # that could not be downloaded. It is reported in place of the script's own check of that item.
    problems: dict[str, str] = field(default_factory=dict)
