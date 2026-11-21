"""Read LaTeX source and return it as a `paper_model.Paper`, with the LaTeX kept as written.

This is the only file that knows LaTeX. It puts every included file in its place,
removes comments, and cuts the text into headings, paragraphs and items. It runs no
LaTeX engine, so it knows no number the compiled paper prints on a statement, an
equation, a table or a figure: an item is named by its \\label, or by its kind and its
place among the items of that kind. Section numbers are the one thing counted, from the
order of the sectioning commands, because a paragraph's location needs them.
"""
from __future__ import annotations

import re
from pathlib import Path

from paper_model import ConversionError, Heading, Item, Paper, Paragraph, Raw, Reference, RunIn, anchor_name

FLOATS = {
    "figure": "figure", "figure*": "figure", "wrapfigure": "figure", "sidewaysfigure": "figure",
    "table": "table", "table*": "table", "wraptable": "table", "sidewaystable": "table", "longtable": "table",
    "algorithm": "algorithm", "algorithm*": "algorithm",
}
# Display environments that LaTeX numbers. Their starred forms are not items.
EQUATIONS = ("equation", "align", "gather", "multline", "eqnarray", "alignat", "flalign")
# Statement kinds assumed when the source uses one without a \newtheorem of its own.
USUAL_STATEMENTS = ("theorem", "lemma", "proposition", "corollary", "assumption", "definition", "remark")
# Inside these a blank line does not end a paragraph and a sectioning command is not a heading.
# A display equation or a list does not start a new paragraph, so the paragraph goes on through them.
CLOSED = ("itemize", "enumerate", "description", "tabular", "tabular*", "tabularx", "array", "verbatim",
          "lstlisting", "minted", "algorithmic", "tikzpicture", *EQUATIONS, *(name + "*" for name in EQUATIONS))
# Commands that set the page and carry no text. A block made only of these is not a paragraph.
LAYOUT = ("maketitle|newpage|clearpage|pagebreak|vspace|vskip|hspace|smallskip|medskip|bigskip|noindent|centering|"
          "appendix|part|parttoc|tableofcontents|bibliographystyle|bibliography|printbibliography|label|looseness|"
          "setcounter|addtocounter|addcontentsline|thispagestyle|pagestyle|balance|onecolumn|twocolumn|begin|end")
DEFINITION = r"def|let|newcommand|renewcommand|providecommand|DeclareMathOperator"
IMAGE_SUFFIXES = ("", ".pdf", ".png", ".jpg", ".jpeg", ".eps")

EVENT = re.compile(
    r"\\begin\{(?P<begin>[^}]+)\}|\\end\{(?P<end>[^}]+)\}|(?P<blank>\n[ \t]*(?:\n[ \t]*)+)"
    r"|\\(?P<section>section|subsection|subsubsection|paragraph|subparagraph)(?P<star>\*?)\s*(?:\[[^\]]*\])?\s*\{"
    r"|(?P<appendix>\\appendix)\b|(?P<list>\\bibliography|\\printbibliography)\b")
BEGIN = re.compile(r"\\begin\{([^}]+)\}")
LABEL = re.compile(r"\\label\{([^}]*)\}")
LABEL_AFTER_HEADING = re.compile(r"[ \t]*\n?[ \t]*\\label\{([^}]*)\}")
INCLUDE = re.compile(r"\\(?:input|include|subfile)\s*\{([^}#\\]+)\}")
GRAPHICS = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")
# A cross-reference: \hyperref[label]{...}, a command that takes labels, or one that takes two
# labels as the ends of a range. The names are listed, because a paper's own macro can end in "ref".
REFERENCE = re.compile(
    r"\\hyperref\s*\[([^\]#]*)\]"
    r"|\\(?:(?:eq|page|name|auto|Auto|autopage|c|C|cpage|Cpage|labelc|namec|nameC|lcnamec|v|V|vpage|f|F|sub|zc|z|th"
    r"|pretty)?ref|(c|C|cpage|Cpage|v|vpage)refrange)\*?\s*\{([^}#]*)\}(?(2)\s*\{([^}#]*)\})")
# A citation: \cite and \nocite with any ending (\citep, \citet, \citeauthor, ...), and the biblatex
# forms \parencite, \textcite, \autocite, \footcite and the like, also with a capital first letter.
# A name that ends in "s" takes one group of keys after another. \citetext and \citestyle take no key.
CITATION = re.compile(
    r"\\((?:[Pp]aren|[Tt]ext|[Aa]uto|[Ff]oot|[Ff]ootfull|[Ss]mart|[Ss]uper|[Ff]ull|no|new|short)?[cC]ite"
    r"(?!text\b|style\b)[a-zA-Z]*)\*?((?:\s*(?:\[[^\]]*\]\s*)*\{[^}#]*\})+)")
ARGUMENT = r"(?:\s*\[[^\]]*\]|\s*\{(?:[^{}]|\{[^{}]*\})*\})*"
NO_TEXT = re.compile(r"\\(?:" + LAYOUT + r")\b\*?" + ARGUMENT
                     + r"|\\(?:" + DEFINITION + r")\*?\s*\{?\\[a-zA-Z@]+\}?" + ARGUMENT)


def read(paper: Path, support: list[Path]) -> Paper:
    """Read the LaTeX source at `paper`, a folder or its main .tex file."""
    main = _main_file(paper)
    folders = [main.parent, *support]
    document = Paper()
    text = _with_includes(main, folders, document.missing)
    start = text.find(r"\begin{document}")
    if start < 0:
        raise ConversionError(f"{main} has no \\begin{{document}}")
    document.preamble = text[:start].strip()
    body = text[start + len(r"\begin{document}"):].split(r"\end{document}")[0]
    title = re.search(r"\\title\s*(?:\[[^\]]*\])?\s*\{", text)
    document.title = _squeeze(_braced(text, title.end() - 1)[0]) if title else main.stem
    _Cutter(document, body, main, folders).cut()
    for match in REFERENCE.finditer(body):
        for label in ",".join(group for group in match.group(1, 3, 4) if group).split(","):
            document.references.append(Reference(anchor_name(label), match.group(0)))
    for written, key in _cited(body):
        if key != "*":
            document.references.append(Reference("ref-" + anchor_name(key), written))
    return document


def _cited(body: str) -> list[tuple[str, str]]:
    """Every citation in the text, as the command written and one key it cites, in order."""
    found = []
    for match in CITATION.finditer(body):
        groups = re.findall(r"\{([^}#]*)\}", match.group(2))
        for group in groups if match.group(1).endswith("s") else groups[:1]:
            found += [(match.group(0), key.strip()) for key in group.split(",")]
    return found


def main_files(folder: Path) -> list[Path]:
    """The .tex files directly in `folder` that hold \\documentclass outside a comment, sorted by name."""
    return [f for f in sorted(folder.glob("*.tex")) if r"\documentclass" in _without_comments(_text(f))]


def _main_file(paper: Path) -> Path:
    """The file that holds \\documentclass: `paper` itself, or the one such file in the folder."""
    paper = paper.resolve()
    if paper.is_file():
        return paper
    mains = main_files(paper)
    if len(mains) != 1:
        found = ", ".join(f.name for f in mains) or "none"
        raise ConversionError(f"{paper} must hold exactly one .tex file with \\documentclass (found: {found}); "
                              "give the main .tex file instead of the folder")
    return mains[0]


# ---------------------------------------------------------------- the source as one text

def _text(file: Path) -> str:
    return file.read_text(encoding="utf-8", errors="replace")


def _squeeze(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _without_comments(text: str) -> str:
    """Remove comments. A line that was only a comment goes, so it does not end a paragraph."""
    text = re.sub(r"\\begin\{comment\}.*?\\end\{comment\}", "", text, flags=re.S)
    kept, verbatim = [], False
    for line in text.split("\n"):
        if re.search(r"\\(begin|end)\{(verbatim|lstlisting|minted)\*?\}", line):
            verbatim = r"\begin" in line
        cut = None if verbatim else next(
            (m.start(1) for m in re.finditer(r"(?<!\\)(?:\\\\)*(%)", line)
             if not re.search(r"\\(?:url|href|path)\{[^}]*$", line[:m.start(1)])), None)
        if cut is None:
            kept.append(line)
        elif line[:cut].strip():
            kept.append(line[:cut].rstrip())
    return "\n".join(kept)


def _find(name: str, folders: list[Path], suffixes: tuple[str, ...]) -> Path | None:
    return next((folder / (name + suffix) for folder in folders for suffix in suffixes
                 if (folder / (name + suffix)).is_file()), None)


def _with_includes(file: Path, folders: list[Path], missing: list[str], depth: int = 0) -> str:
    """The text of `file` without comments, each file it includes put in the place of the command."""
    def included(match: re.Match) -> str:
        found = _find(match.group(1).strip(), folders, ("", ".tex"))
        if found is None or depth > 20:
            missing.append(match.group(0))
            return match.group(0)
        return _with_includes(found, folders, missing, depth + 1)
    return INCLUDE.sub(included, _without_comments(_text(file)))


def _braced(text: str, start: int) -> tuple[str, int]:
    """What stands between the brace at `start` and its partner, and the place after the partner."""
    depth = 0
    for place in range(start, len(text)):
        if text[place] in "{}" and (place == 0 or text[place - 1] != "\\"):
            depth += 1 if text[place] == "{" else -1
            if depth == 0:
                return text[start + 1:place], place + 1
    return text[start + 1:], len(text)


def _end_of(text: str, name: str, start: int) -> int | None:
    """The place after the \\end that closes the environment `name` opened just before `start`."""
    depth = 1
    for match in re.finditer(r"\\(begin|end)\{" + re.escape(name) + r"\}", text[start:]):
        depth += 1 if match.group(1) == "begin" else -1
        if depth == 0:
            return start + match.end()
    return None


# ---------------------------------------------------------------- headings, paragraphs and items

class _Cutter:
    def __init__(self, document: Paper, body: str, main: Path, folders: list[Path]):
        self.document, self.body, self.main, self.folders = document, body, main, folders
        declared = re.findall(r"\\newtheorem\s*\{([^}]+)\}\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}", document.preamble + body)
        self.kinds = {name: name for name in USUAL_STATEMENTS} | {env: _squeeze(shown).lower() for env, shown in declared}
        self.kinds |= FLOATS | {name: "equation" for name in EQUATIONS}
        paths = re.search(r"\\graphicspath\s*\{((?:\s*\{[^}]*\})+)\s*\}", document.preamble)
        self.image_folders = folders + [f / p for p in re.findall(r"\{([^}]*)\}", paths.group(1) if paths else "")
                                        for f in folders]
        self.place: dict[str, int] = {}      # how many items of each kind have been met
        self.numbers = [0, 0, 0]             # the section, the part of it and the part of that part
        self.appendix = False

    def cut(self) -> None:
        body, taken, closed = self.body, 0, []
        for match in EVENT.finditer(body):
            if match.start() < taken:
                continue   # inside an item or a heading already taken
            begin, end = match.group("begin"), match.group("end")
            if closed and end == closed[-1]:
                closed.pop()
            elif begin in CLOSED:
                closed.append(begin)
            elif closed:
                continue
            elif begin and (begin in self.kinds or begin == "thebibliography"):   # a statement or a float
                stop = _end_of(body, begin, match.end())
                if stop is None:
                    continue
                self._block(body[taken:match.start()])
                if begin == "thebibliography":
                    self._reference_list(written=body[match.start():stop])
                else:
                    self.document.blocks.append(self._item(self.kinds[begin], body[match.start():stop]))
                taken = stop
            elif "abstract" in (begin, end):
                self._block(body[taken:match.start()])
                if begin:
                    self.document.blocks.append(Heading("abstract", 1, None, "Abstract"))
                taken = match.end()
            elif match.group("blank"):
                self._block(body[taken:match.start()])
                taken = match.end()
            elif match.group("section"):
                self._block(body[taken:match.start()])
                taken = self._heading(match)
            elif match.group("appendix"):
                self.appendix, self.numbers = True, [0, 0, 0]
            elif match.group("list"):
                self._block(body[taken:match.start()])
                taken = _braced(body, match.end())[1] if body[match.end():match.end() + 1] == "{" else match.end()
                self._reference_list(command=body[match.start():taken])
        self._block(body[taken:])

    def _heading(self, match: re.Match) -> int:
        """Add the heading that starts at `match`, with the labels that follow it. Return where it ends."""
        title, place = _braced(self.body, match.end() - 1)
        labels = []
        while (label := LABEL_AFTER_HEADING.match(self.body, place)):
            labels.append(anchor_name(label.group(1)))
            place = label.end()
        command = match.group("section")
        if command.endswith("paragraph"):
            self.document.blocks.append(RunIn(_squeeze(title), labels))
            return place
        level = ("section", "subsection", "subsubsection").index(command) + 1
        number = None
        if not match.group("star") and (level == 1 or self.numbers[level - 2]):
            self.numbers[level - 1] += 1
            self.numbers[level:] = [0] * (3 - level)
            first = chr(ord("A") + self.numbers[0] - 1) if self.appendix else str(self.numbers[0])
            number = ".".join([first, *map(str, self.numbers[1:level])])
        role = "other" if number is None else "appendix" if self.appendix else "main"
        self.document.blocks.append(Heading(role, level, number, _squeeze(title), labels))
        return place

    def _block(self, text: str) -> None:
        """Add the text between two cuts as a paragraph, or as layout commands when it holds no text."""
        text = text.strip()
        if not text:
            return
        parts = self._parts(text)
        own = "".join(part for part in parts if isinstance(part, str))
        labels = [anchor_name(label) for label in LABEL.findall(own)]
        if len(parts) == 1 and not NO_TEXT.sub("", own).strip():
            self.document.blocks.append(Raw(text, labels))
        else:
            self.document.blocks.append(Paragraph(parts, _squeeze(LABEL.sub("", own)), labels))

    def _parts(self, text: str) -> list[str | Item]:
        """`text` cut into the items that stand in it and the text between them."""
        parts: list[str | Item] = []
        taken = 0
        for match in BEGIN.finditer(text):
            kind = self.kinds.get(match.group(1))
            stop = _end_of(text, match.group(1), match.end()) if kind and match.start() >= taken else None
            if stop is not None:
                parts += [text[taken:match.start()], self._item(kind, text[match.start():stop])]
                taken = stop
        return [part for part in [*parts, text[taken:]] if part != ""]

    def _item(self, kind: str, text: str) -> Item:
        self.place[kind] = self.place.get(kind, 0) + 1
        name = f"{kind}-source-order-{self.place[kind]}"
        head = BEGIN.match(text).end()
        body = self._parts(text[head:])
        body = [text[:head] + body[0], *body[1:]] if body and isinstance(body[0], str) else [text[:head], *body]
        own = "".join(part for part in body if isinstance(part, str))
        item = Item(kind, [anchor_name(label) for label in LABEL.findall(own)] or [name], body)
        caption = re.search(r"\\caption\s*(?:\[[^\]]*\])?\s*\{", text)
        if caption:
            item.words = _squeeze(LABEL.sub("", _braced(text, caption.end() - 1)[0]))
        elif kind != "equation":
            item.words = _squeeze(LABEL.sub("", own[head:own.rindex(r"\end{")]))
        if kind == "figure":
            for graphic in GRAPHICS.finditer(text):
                image = _find(graphic.group(1).strip(), self.image_folders, IMAGE_SUFFIXES)
                if image is None:
                    self.document.missing.append(graphic.group(0))
                else:
                    item.images.append(image)
        return item

    # ----- the reference list

    def _reference_list(self, written: str = "", command: str = "") -> None:
        """Add the heading of the reference list and one entry for each cited work.

        The entries come from `written`, a thebibliography environment in the text; or from
        the paper's .bbl file; or from its .bib files, for the works the text cites.
        `command` is the command that asks for the list; it is kept under the heading.
        """
        blocks = self.document.blocks
        blocks.append(Heading("references", 1, None, "References"))
        blocks += [Raw(command)] if command else []
        bbl = _find(self.main.stem, self.folders, (".bbl",))
        written = written or (_without_comments(_text(bbl)) if bbl else "")
        if r"\bibitem" in written:
            start, *entries = re.split(r"(?=\\bibitem\b)", written)
            blocks.append(Raw(start.strip()))
            for entry in entries:
                entry = entry.split(r"\end{thebibliography}")[0]
                # \bibitem[an optional label, which may hold brackets and braces]{key}
                key = re.match(r"\\bibitem\s*(?:\[(?:[^\[\]{}]|\{(?:[^{}]|\{[^{}]*\})*\}|\[[^\]]*\])*\])?\s*\{([^}]*)\}",
                               entry)
                if key:
                    name, words = "ref-" + anchor_name(key.group(1)), entry[key.end():]
                    blocks.append(Item("reference", [name], [entry.strip()], _squeeze(words)))
            blocks.append(Raw(r"\end{thebibliography}"))
            return
        text = self.document.preamble + self.body
        names = [name.strip() for group in re.findall(r"\\(?:bibliography|addbibresource)\s*\{([^}]*)\}", text)
                 for name in group.split(",")]
        entries: dict[str, str] = {}
        for name in names:
            file = _find(name, self.folders, ("", ".bib"))
            if file is None:
                self.document.missing.append(f"\\bibliography{{{name}}}")
                continue
            source = _text(file)
            for entry in re.finditer(r"@(\w+)\s*\{\s*([^,\s{}]+)\s*,", source):
                if entry.group(1).lower() not in ("comment", "string", "preamble"):
                    stop = _braced(source, source.index("{", entry.start()))[1]
                    entries.setdefault(entry.group(2).lower(), source[entry.start():stop])
        cited = [key for _, key in _cited(self.body)]
        for key in dict.fromkeys(entries if "*" in cited else cited):
            if key.lower() in entries:
                entry = entries[key.lower()]
                blocks.append(Item("reference", ["ref-" + anchor_name(key)], [entry], _squeeze(entry)))

