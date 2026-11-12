"""Read the `paper.md` a transcriber wrote from a PDF, and check it.

`prompts/formats/source.md` defines what the transcriber writes: a marker at the start
of every page, an anchor on every paragraph and on every numbered item, the headings as
Markdown headings, and which kinds the paper numbers in one sequence. This module reads
those, lists the paragraphs and items for the index, and finds every disagreement: an
anchor that is not well formed, not in order or used twice; a page without a marker; a
place marked as unreadable; a figure or a table without its image; a number missing
from the sequence of a numbered kind; and a mention of a numbered item that leads to
no extracted item.

It reads the text of `paper.md` and nothing else, and it changes nothing.
"""
from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field
from urllib.parse import unquote

ANCHOR_LINE = re.compile(r'<a id="([^"]*)"></a>')
ANCHOR_TAG = re.compile(r"<a\s[^>]*\b(?:id|name)\s*=", re.IGNORECASE)
PAGE_MARKER = re.compile(r"page-([1-9]\d*)")
PARAGRAPH = re.compile(r"p([1-9]\d*)-([1-9]\d*)")
# The kind in lower case, then the number as the paper prints it: theorem-2, lemma-C.1, table-A1, table-II.
ITEM = re.compile(r"([a-z]+(?:-[a-z]+)*)-([A-Z0-9][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)*)")
HEADING = re.compile(r"(#{1,6})\s+(.*\S)")
RUN_IN = re.compile(r"\*\*(.+)\*\*")
FENCE = re.compile(r"\s*(```|~~~)")
IMAGE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)>\s]+)>?[^)]*\)")
# The number in front of a heading's title: 3, 3.2, IV, B, B.2, II-A, each with or without a point after it.
HEADING_NUMBER = re.compile(r"(?:((?i:Appendix))\s+)?((?:\d+|[IVX]+|[A-Z])(?:[.-](?:\d+|[A-Z]))*)([.:]?)\s+(?=\S)")
NOT_SECTIONS = {"abstract": "abstract", "references": "references", "bibliography": "references"}
SEQUENCE_LINE = re.compile(r"<!--\s*one sequence:\s*([a-z]+(?:-[a-z]+)*(?:\s*,\s*[a-z]+(?:-[a-z]+)*)+)\s*-->")
UNREADABLE = "[unreadable]"
ROMAN = re.compile(r"(?=[IVX])(X{0,3})(IX|IV|V?I{0,3})")
ROMAN_DIGITS = {"I": 1, "V": 5, "X": 10}

IMAGE_FOLDER = {"figure": "figures", "table": "tables"}

# The words a paper mentions a kind by, in any case. A kind of the transcription that is
# not here is mentioned by its own name. Reference-list entries are cited by number
# alone, which is no mention by kind and number.
KIND_WORDS = {
    "figure": ("Figure", "Fig"),
    "table": ("Table", "Tab"),
    "algorithm": ("Algorithm", "Alg"),
    "equation": ("Equation", "Eqn", "Eq"),
    "theorem": ("Theorem", "Thm"),
    "lemma": ("Lemma", "Lem"),
    "proposition": ("Proposition", "Prop"),
    "corollary": ("Corollary", "Cor"),
    "assumption": ("Assumption",),
    "definition": ("Definition", "Def"),
    "remark": ("Remark",),
}
NOT_MENTIONED = ("reference",)

ARABIC = r"(?:[A-Z]\.?)?\d+(?:\.\d+)*(?:[a-z](?![A-Za-z]))?"
ROMAN_NUMBER = r"[IVX]+(?![A-Za-z0-9])"
GAP = r"(?:[ \t~\u00a0]*\n?[ \t~\u00a0]*)"


@dataclass
class Row:
    """A heading, a paragraph or an item of the transcription, in the paper's order."""
    kind: str                # "heading", "paragraph", or the kind of an item
    line: int                # its line in paper.md
    anchor: str = ""
    page: int = 0            # 0 before the first page marker
    number: str = ""         # of an item, as the paper prints it
    depth: int = 0           # 1 for an item inside a paragraph or another item
    level: int = 0           # of a heading: 1 for the paper's title, 2 for a top-level section
    title: str = ""          # of a heading
    role: str = ""           # of a top-level section: "abstract", "main", "appendix" or "references"
    location: str = ""       # of a paragraph, such as "p.3, Delay bound ¶2"
    images: list[str] = field(default_factory=list)   # the image files a figure or a table links
    text: list[str] = field(default_factory=list)     # the lines of its first block of text; none for an equation
    done: bool = False                                # that block has ended


@dataclass
class Transcription:
    rows: list[Row] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)       # paper.md, with every anchor line emptied
    last_page: int = 0                                   # the number of the last page marker
    sequences: list[list[str]] = field(default_factory=list)   # the kinds the paper numbers in one sequence
    slips: list[str] = field(default_factory=list)       # what a line shows by itself: an anchor or a line of
                                                         # one sequence in the wrong form, a place marked unreadable

    @property
    def items(self) -> list[Row]:
        return [row for row in self.rows if row.kind not in ("heading", "paragraph")]


# ---------------------------------------------------------------- reading

@dataclass
class _Sections:
    """What the headings read so far show of how the paper numbers its sections."""
    numbered: bool = False   # a numbered section of the main text was read
    appendix: str = ""       # the letter of the last appendix read


def _heading(title: str, level: int, seen: _Sections) -> tuple[str, str]:
    """The role of the section a heading starts, and the heading's title without its number."""
    if level == 2 and title.lower() in NOT_SECTIONS:
        return NOT_SECTIONS[title.lower()], title
    number = HEADING_NUMBER.match(title)
    if number and number.group(2, 3) == ("A", "") and not number.group(1) and not (level == 2 and seen.numbered):
        number = None   # "A" is the first word of the title, not the letter of an appendix
    if not number:
        return ("appendix" if title.lower().startswith("appendix") else "main"), title
    first = re.split("[.-]", number.group(2))[0]
    next_appendix = chr(ord(seen.appendix or "@") + 1)
    appendix = bool(number.group(1)) or first.isalpha() and (not ROMAN.fullmatch(first) or first == next_appendix)
    if level == 2 and appendix:
        seen.appendix = first if first.isalpha() else seen.appendix
    elif level == 2:
        seen.numbered = True
    return ("appendix" if appendix else "main"), title[number.end():]


def read(text: str) -> Transcription:
    """List the headings, paragraphs and items of `text`, and every slip in its anchors."""
    result = Transcription()
    lines = text.splitlines()
    page = paragraphs = 0
    section = run_in = ""
    seen = _Sections()
    in_sequence: set[str] = set()
    owner: Row | None = None      # the row whose block the current line belongs to
    block_has_text = False
    group: list[Row] = []         # the rows that take the text and the images that follow
    in_fence = False

    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        anchor = ANCHOR_LINE.fullmatch(line)
        result.lines.append("" if anchor else raw)
        if anchor:
            name = anchor.group(1)
            if marker := PAGE_MARKER.fullmatch(name):
                written = int(marker.group(1))
                if written != page + 1:
                    result.slips.append(f'Line {number} of paper.md: the page marker is "{name}" where "page-{page + 1}" is next.')
                page, paragraphs = written, 0
                result.last_page = written
                owner, group = None, []
                continue
            nested = owner is not None and block_has_text
            if paragraph := PARAGRAPH.fullmatch(name):
                on_page, written = int(paragraph.group(1)), int(paragraph.group(2))
                if not page:
                    result.slips.append(f'Line {number} of paper.md: the paragraph anchor "{name}" stands before the first page marker.')
                elif (on_page, written) != (page, paragraphs + 1):
                    result.slips.append(
                        f'Line {number} of paper.md: the paragraph anchor is "{name}" where "p{page}-{paragraphs + 1}" is next.'
                    )
                paragraphs = written if on_page == page else paragraphs + 1
                label = run_in or section
                row = Row("paragraph", number, name, on_page,
                          location=f"p.{on_page}, {label} ¶{written}" if label else f"p.{on_page} ¶{written}")
            elif item := ITEM.fullmatch(name):
                row = Row(item.group(1), number, name, page, number=item.group(2))
            else:
                result.slips.append(
                    f'Line {number} of paper.md: the anchor "{name}" is not a page marker, a paragraph anchor or the anchor of an item.'
                )
                continue
            if nested:
                row.depth = owner.depth + 1
            elif owner is None or block_has_text:
                owner, block_has_text, group = row, False, []
            else:
                row.depth = owner.depth     # a second anchor on the same block
            group.append(row)
            result.rows.append(row)
            continue
        if not line:
            owner = None
            for row in group:
                row.done = row.done or bool(row.text)
            continue
        if line.startswith("<!--") and "sequence" in line:
            result.lines[-1] = ""
            sequence = SEQUENCE_LINE.fullmatch(line)
            kinds = re.split(r"\s*,\s*", sequence.group(1)) if sequence else []
            if not sequence:
                result.slips.append(
                    f"Line {number} of paper.md: the kinds of one sequence are not written as "
                    "<!-- one sequence: theorem, lemma -->."
                )
            result.slips += [f'Line {number} of paper.md: "{kind}" is in two sequences.' for kind in kinds if kind in in_sequence]
            if kinds and not in_sequence.intersection(kinds):
                result.sequences.append(kinds)
            in_sequence.update(kinds)
            continue
        if UNREADABLE in line:
            times = line.count(UNREADABLE)
            result.slips.append(
                f"Line {number} of paper.md, page {page}: {UNREADABLE} marks {times} place{'s' if times > 1 else ''} "
                "that the transcriber could not read."
            )
        if ANCHOR_TAG.search(line):
            result.slips.append(
                f'Line {number} of paper.md: an anchor is not written as <a id="…"></a> alone on its line.'
            )
        heading = None if in_fence else HEADING.fullmatch(line)
        if heading:
            level, title = len(heading.group(1)), heading.group(2)
            role, label = _heading(title, level, seen)
            result.rows.append(Row("heading", number, level=level, title=title, role=role if level == 2 else ""))
            section, run_in = ("" if level == 1 else label), ""
            owner, group = None, []
            continue
        if FENCE.match(raw):
            in_fence, block_has_text = not in_fence, True
            continue
        alone = (number == 1 or not lines[number - 2].strip()) and (number == len(lines) or not lines[number].strip())
        bold = RUN_IN.fullmatch(line)
        if bold and alone and owner is None and not in_fence and "**" not in bold.group(1):
            run_in = bold.group(1).rstrip(".: ")
            group = []
            continue
        block_has_text = True
        for row in group:
            row.images += [posixpath.normpath(unquote(target)) for target in IMAGE.findall(line)]
            shown = IMAGE.sub("", line).strip()
            if shown and not row.done and row.kind != "equation":
                row.text.append(shown)
    return result


# ---------------------------------------------------------------- numbers and their sequences

def _sequence_place(number: str) -> tuple[str, str, int] | None:
    """Where a number stands in its sequence: (what comes before the count, "roman" or "arabic", the count)."""
    if ROMAN.fullmatch(number):
        value, previous = 0, 0
        for digit in reversed(number):
            current = ROMAN_DIGITS[digit]
            value += current if current >= previous else -current
            previous = max(previous, current)
        return "", "roman", value
    arabic = re.fullmatch(r"(.*?)(\d+)[a-z]?", number)
    return (arabic.group(1), "arabic", int(arabic.group(2))) if arabic else None


def _written(prefix: str, style: str, count: int) -> str:
    if style == "arabic":
        return f"{prefix}{count}"
    tens, ones = divmod(count, 10)
    return "X" * tens + ("", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX")[ones]


def gaps(items: list[Row], sequences: list[list[str]]) -> list[str]:
    """Every number missing between 1 and the last number of a kind.

    The kinds of one of `sequences` are checked together, as in Assumption 1, Theorem 2,
    Lemma 3, and no number of such a sequence is carried twice. Every other kind is
    checked alone.
    """
    sequence_of = {kind: tuple(kinds) for kinds in sequences for kind in kinds}
    counts: dict[tuple, dict[str, set[int]]] = {}   # (sequence, what comes before the count, style) -> kind -> counts
    for item in items:
        place = _sequence_place(item.number)
        if place:
            sequence = sequence_of.get(item.kind, (item.kind,))
            counts.setdefault((sequence, *place[:2]), {}).setdefault(item.kind, set()).add(place[2])

    found: list[str] = []
    for (sequence, prefix, style), by_kind in counts.items():
        kinds = [kind for kind in sequence if kind in by_kind]
        present = set().union(*by_kind.values())
        last = max(present)
        last_kind = next(kind for kind in kinds if last in by_kind[kind])
        runs: list[list[int]] = []
        for count in sorted(set(range(1, last)) - present):
            if runs and runs[-1][-1] == count - 1:
                runs[-1].append(count)
            else:
                runs.append([count])
        for run in runs:
            numbers = _written(prefix, style, run[0])
            if len(run) > 1:
                numbers += " to " + _written(prefix, style, run[-1])
            names = kinds[0] if len(kinds) == 1 else ", ".join(kinds[:-1]) + " or " + kinds[-1]
            found.append(f"No {names} {numbers} was extracted, though {last_kind} {_written(prefix, style, last)} was.")
        for count in sorted(present):
            twice = [f"{kind} {_written(prefix, style, count)}" for kind in kinds if count in by_kind[kind]]
            if len(twice) > 1:
                found.append(
                    f"{' and '.join(twice)} were both extracted, though paper.md gives "
                    f"{', '.join(sequence[:-1])} and {sequence[-1]} as one sequence."
                )
    return found


# ---------------------------------------------------------------- mentions

def _name(kind: str) -> str:
    return KIND_WORDS[kind][0] if kind in KIND_WORDS else " ".join(word.capitalize() for word in kind.split("-"))


def _range(first: str, last: str) -> list[str]:
    """The numbers from `first` to `last`, when both are plain counts."""
    if first.isdigit() and last.isdigit() and 0 < int(last) - int(first) < 100:
        return [str(count) for count in range(int(first) + 1, int(last) + 1)]
    return [last]


def mentions(lines: list[str], kinds: list[str], roman_kinds: set[str]) -> list[tuple[str, str, int]]:
    """Every mention of a numbered item by kind and number: (kind, number, line), in the text's order.

    The words of a kind are matched in any case, and where two kinds fit, as in "Main
    Theorem 2", the longer one is the mention. A roman number is a mention only of a
    kind in `roman_kinds`. After a plural, as in "Tables 1, 2 and 4" or "Eqs. (3)–(5)",
    every number of the list is a mention. Numbers after a comma count only when "and"
    or "or" closes the list, so that "Figures 1 and 2, 30 runs" mentions no Figure 30.
    """
    kind_of: dict[str, str] = {}
    for kind in kinds:
        for word in KIND_WORDS.get(kind, (kind.replace("-", " "),)):
            kind_of[word.lower()] = kind
            if word.endswith("y"):
                kind_of[word[:-1].lower() + "ie"] = kind    # the stem of the plural
    names = "|".join(re.escape(name).replace(r"\ ", r"\s+") for name in sorted(kind_of, key=len, reverse=True))
    number = rf"\(?(?P<number>{ROMAN_NUMBER}|{ARABIC})\)?"
    first = re.compile(rf"\b(?i:(?P<name>{names})(?P<plural>s)?)\.?{GAP}{number}")
    more = re.compile(rf"{GAP}(?i:(?P<join>,{GAP}(?:and|or)\b|,|and\b|or\b|&|[-–—]|to\b|through\b)){GAP}{number}")

    text = "\n".join(lines)
    found: list[tuple[str, str, int]] = []
    for match in first.finditer(text):
        kind = kind_of[" ".join(match.group("name").lower().split())]
        numbers, after_comma, end = [match.group("number")], [], match.end()
        if re.fullmatch("[IVX]+", numbers[0]) and kind not in roman_kinds:
            continue
        while match.group("plural") and (following := more.match(text, end)):
            join, number_read = following.group("join").lower(), following.group("number")
            if number_read[0].isdigit() != numbers[0][0].isdigit():
                break
            end = following.end()
            if join in ("-", "–", "—", "to", "through"):
                listed = after_comma or numbers
                listed += _range(listed[-1], number_read)
            elif join == ",":
                after_comma.append(number_read)
            else:
                numbers += [*after_comma, number_read]
                break
        line = text.count("\n", 0, match.start()) + 1
        found += [(kind, number_read, line) for number_read in numbers]
    return found


def _leads_to_an_item(number: str, extracted: set[str]) -> bool:
    """`2` and `2a` lead to an item numbered 2, and `2` leads to the items 2a and 2b."""
    part = re.fullmatch(r"(.*\d)[a-z]", number)
    return (number in extracted or bool(part and part.group(1) in extracted)
            or any(re.fullmatch(re.escape(number) + "[a-z]", other) for other in extracted))


def lost_mentions(transcription: Transcription) -> list[str]:
    numbers: dict[str, set[str]] = {}
    for item in transcription.items:
        numbers.setdefault(item.kind, set()).add(item.number)
    kinds = [kind for kind in dict.fromkeys([*KIND_WORDS, *numbers]) if kind not in NOT_MENTIONED]
    roman_kinds = {kind for kind, carried in numbers.items() if any(ROMAN.fullmatch(number) for number in carried)}
    lost: dict[tuple[str, str], list[int]] = {}
    for kind, number, line in mentions(transcription.lines, kinds, roman_kinds):
        if not _leads_to_an_item(number, numbers.get(kind, set())):
            lost.setdefault((kind, number), []).append(line)
    found = []
    for (kind, number), where in lost.items():
        times = f"{len(where)} time{'s' if len(where) > 1 else ''} in the text, {'first ' if len(where) > 1 else ''}at"
        found.append(f'"{_name(kind)} {number}" leads to no extracted item ({times} line {where[0]} of paper.md).')
    return found


# ---------------------------------------------------------------- all the checks

def disagreements(transcription: Transcription, page_images: int, image_files: set[str]) -> list[str]:
    """Everything in the transcription that the person must see before a run goes on.

    `page_images` is how many page images `pages/` holds, and `image_files` the files of
    `figures/` and `tables/`, each as the transcription links it, such as "tables/table-2.png".
    """
    found = list(transcription.slips)
    where: dict[str, list[int]] = {}
    for row in transcription.rows:
        if row.anchor:
            where.setdefault(row.anchor, []).append(row.line)
    for anchor, lines in where.items():
        if len(lines) > 1:
            listed = ", ".join(str(line) for line in lines[:-1]) + f" and {lines[-1]}"
            found.append(f'The anchor "{anchor}" is used {len(lines)} times (lines {listed} of paper.md).')
    if transcription.last_page != page_images:
        found.append(
            f"The last page marker of paper.md is page-{transcription.last_page} and pages/ holds {page_images} page images."
        )
    for item in transcription.items:
        if item.kind in IMAGE_FOLDER:
            if not item.images:
                found.append(f"The {item.kind} {item.anchor} has no image in paper.md.")
            found += [
                f"The {item.kind} {item.anchor} links {image}, which does not exist."
                for image in item.images if image not in image_files
            ]
    return found + gaps(transcription.items, transcription.sequences) + lost_mentions(transcription)
