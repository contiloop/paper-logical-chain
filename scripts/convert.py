"""Convert a paper into `source/<input>/` of a workspace.

`prompts/formats/source.md` defines the folder. The paper is LaTeX source, a Markdown
file or a PDF.

From LaTeX source or a Markdown file, one command:

    uv run python scripts/convert.py <paper> <input> <workspace> [--support <folder>]

Takes:    the paper, as a folder of LaTeX source or its main .tex file, or as a .md or
          .markdown file or a folder that holds exactly one such file and no .tex file
          with \\documentclass; the input's name, such as yun2025; and the workspace
          path. `--support <folder>` names a further folder in which files the paper
          includes, or images it shows, are looked for, and may be given more than once.
Writes:   <workspace>/source/<input>/ with paper.md, paragraphs.md and figures/.
Prints:   the number of sections, paragraphs, figures, tables, algorithms, equations,
          numbered statements and reference-list entries extracted, and every
          disagreement: a cross-reference or a citation that leads to no extracted item,
          an included file or a figure file that was not found, an image that could not
          be made into a PNG, and an image on the web that could not be downloaded.
Returns:  exit code 0 when there is no disagreement, 1 when there is one (the files
          are written all the same), 2 when the paper could not be converted.

The paper is read by a reader that returns a `paper_model.Paper`; the conversion works
on that alone. The readers are `latex_reader` and `markdown_reader`. The Markdown reader
downloads an image whose path is a URL, so a conversion from Markdown can use the network.

From a PDF, three commands. The text of a PDF is not read by this script: an agent, the
transcriber, writes `paper.md`, between the first command and the last.

    uv run python scripts/convert.py <PDF> <input> <workspace>

Writes:   <workspace>/source/<input>/pages/, an image of every page. Whatever else
          the folder holds is left as it is.
Returns:  exit code 0, or 2 when the PDF could not be read.

    uv run python scripts/convert.py cut <PDF> <folder> <anchor> --page <N>
        --left <L> --top <T> --right <R> --bottom <B> [--part <K>]

Takes:    the PDF; the folder `source/<input>/`; the anchor of a figure or a table,
          such as figure-3 or table-A.1; the page; and the region of the page, each
          side as a percentage of the page's width or height from its top left corner.
Writes:   figures/<anchor>.png or tables/<anchor>.png in the folder, in place of an
          earlier image of that name. With `--part K`, <anchor>-K.png.
Returns:  exit code 0, or 2 when nothing was cut.

    uv run python scripts/convert.py index <folder>

Takes:    the folder `source/<input>/`, with `paper.md` written.
Writes:   paragraphs.md in the folder. `paper.md` is not changed.
Prints:   the counts, as from LaTeX source, and every disagreement: an anchor that is
          not well formed, not in order or used twice; a page without its marker; a
          place marked as unreadable; a figure or a table without its image; a number
          missing from the sequence of a numbered kind; and a mention of a numbered
          item, such as "Table 3", that leads to no extracted item.
Returns:  exit code 0 when there is no disagreement, 1 when there is one (the index
          is written all the same), 2 when the folder has no `paper.md`.

The PDF is drawn by `pdf_pages`, and `paper.md` is read and checked by `transcription`.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from paper_model import NOT_STATEMENTS, ConversionError, Heading, Item, Paper, Paragraph, Raw, RunIn

FIRST_WORDS = 12


@dataclass
class Report:
    main_sections: int = 0
    appendix_sections: int = 0
    paragraphs: int = 0
    items: list[tuple[str, str]] = field(default_factory=list)   # (kind, first anchor) of every item, in order
    disagreements: list[str] = field(default_factory=list)


@dataclass
class Conversion:
    document: Paper
    report: Report


def _is_pdf(paper: Path) -> bool:
    return paper.is_file() and paper.suffix.lower() == ".pdf"


def _markdown_file(paper: Path) -> Path | None:
    """The Markdown file to read: `paper` itself, or the one Markdown file of a folder without a LaTeX main file.

    None when the input is LaTeX source.
    """
    import latex_reader
    import markdown_reader

    if paper.is_file():
        return paper if paper.suffix.lower() in markdown_reader.SUFFIXES else None
    if any(r"\documentclass" in latex_reader._without_comments(latex_reader._text(tex)) for tex in paper.glob("*.tex")):
        return None
    files = sorted(f for f in paper.iterdir() if f.is_file() and f.suffix.lower() in markdown_reader.SUFFIXES)
    if len(files) != 1:
        found = ", ".join(f.name for f in files) or "none"
        raise ConversionError(f"{paper} must hold a .tex file with \\documentclass or exactly one Markdown file "
                              f"(Markdown files found: {found}); give the file instead of the folder")
    return files[0]


def read_paper(paper: Path, support: list[Path], downloads: Path) -> Paper:
    """Pick the reader for this kind of input and return what it read.

    `downloads` is a folder for the images the Markdown reader downloads; it must last
    until the files are written.
    """
    if not paper.exists():
        raise ConversionError(f"no such file or folder: {paper}")
    if _is_pdf(paper):
        raise ConversionError("the text of a PDF is transcribed by an agent, not read by a reader")
    markdown = _markdown_file(paper)
    if markdown:
        import markdown_reader
        return markdown_reader.read(markdown, support, downloads)
    if paper.is_dir() or paper.suffix.lower() == ".tex":
        import latex_reader
        return latex_reader.read(paper, support)
    raise ConversionError(f"not a folder of LaTeX source, a .tex file or a Markdown file: {paper}")


# ---------------------------------------------------------------- places and anchors

@dataclass
class Place:
    """One row of the paper in order: a heading, a paragraph, an item or other text."""
    block: Heading | RunIn | Raw | Paragraph | Item
    anchors: list[str]
    location: str = ""   # of a paragraph, such as "§3, Convergence guarantee ¶2"
    depth: int = 0       # 0 for a block of the paper, 1 and more for an item inside another block


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def first_words(text: str) -> str:
    words = text.split()
    return " ".join(words[:FIRST_WORDS]) + (" …" if len(words) > FIRST_WORDS else "")


def places(document: Paper) -> list[Place]:
    """Give every paragraph its location and anchor, and list every block and item in order.

    Paragraph numbers restart under each heading. No anchor is given twice: a second use
    gets `-2` after its name.
    """
    rows: list[Place] = []
    used: set[str] = set()
    section_label, section_base = "Before the first heading", "start"
    heading_label, heading_base, count = "", "", 0

    def unique(anchor: str) -> str:
        candidate, n = anchor, 1
        while candidate in used:
            n += 1
            candidate = f"{anchor}-{n}"
        used.add(candidate)
        return candidate

    def add_items(parts: list, depth: int) -> None:
        for part in parts:
            if isinstance(part, Item):
                rows.append(Place(part, [unique(a) for a in part.anchors], depth=depth))
                add_items(part.body, depth + 1)

    for block in document.blocks:
        labels = [] if isinstance(block, Item) else [unique(label) for label in block.labels]
        if isinstance(block, Heading):
            if block.role == "abstract":
                section_label, base = "Abstract", "abstract"
            elif block.number:
                section_label, base = f"§{block.number}", f"s{block.number}"
            else:
                section_label, base = block.title, slug(block.title) or "section"
            section_base = unique(base)
            heading_label, heading_base, count = "", "", 0
            rows.append(Place(block, [section_base, *labels]))
        elif isinstance(block, RunIn):
            heading_label = block.title.rstrip(".: ")
            heading_base, count = unique(f"{section_base}-{slug(heading_label) or 'heading'}"), 0
            rows.append(Place(block, labels))
        elif isinstance(block, Paragraph):
            count += 1
            location = f"{section_label}, {heading_label} ¶{count}" if heading_label else f"{section_label} ¶{count}"
            rows.append(Place(block, [unique(f"{heading_base or section_base}-p{count}"), *labels], location))
            add_items(block.parts, 1)
        elif isinstance(block, Item):
            rows.append(Place(block, [unique(a) for a in block.anchors]))
            add_items(block.body, 1)
        else:
            rows.append(Place(block, labels))
    return rows


# ---------------------------------------------------------------- checking

def check(document: Paper) -> Report:
    """Count what was extracted, and list what the paper refers to or includes that is not there."""
    report = Report()
    anchors: set[str] = set()
    for place in places(document):
        block = place.block
        anchors.update(place.anchors)
        if isinstance(block, Heading) and block.level == 1:
            report.main_sections += block.role == "main"
            report.appendix_sections += block.role == "appendix"
        elif isinstance(block, Paragraph):
            report.paragraphs += 1
        elif isinstance(block, Item):
            report.items.append((block.kind, place.anchors[0]))
            if block.anchors[0] in document.problems:
                report.disagreements.append(document.problems[block.anchors[0]])
            elif block.kind == "figure" and not block.images:
                report.disagreements.append(f"The figure {place.anchors[0]} has no image file, so no image was made.")
    lost: dict[str, int] = {}
    for reference in document.references:
        if reference.anchor not in anchors:
            lost[reference.written] = lost.get(reference.written, 0) + 1
    report.disagreements += [
        f"{written} leads to no extracted item ({times} time{'s' if times > 1 else ''} in the text)."
        for written, times in lost.items()
    ]
    report.disagreements += [f"{written}: the file was not found." for written in document.missing]
    return report


def report_text(report: Report) -> str:
    def count(kind: str) -> int:
        return sum(1 for k, _ in report.items if k == kind)

    statements = [k for k, _ in report.items if k not in NOT_STATEMENTS]
    kinds = ", ".join(f"{statements.count(kind)} {kind}" for kind in dict.fromkeys(statements))
    lines = [
        f"Sections: {report.main_sections} of main text, {report.appendix_sections} of appendix",
        f"Paragraphs: {report.paragraphs}",
        f"Figures: {count('figure')}",
        f"Tables: {count('table')}",
        f"Algorithms: {count('algorithm')}",
        f"Equations: {count('equation')}",
        f"Numbered statements: {len(statements)}" + (f" ({kinds})" if kinds else ""),
        f"Reference-list entries: {count('reference')}",
    ]
    if report.disagreements:
        lines.append(f"Disagreements: {len(report.disagreements)}" + "".join(f"\n  {d}" for d in report.disagreements))
    else:
        lines.append("Disagreements: none")
    return "\n".join(lines) + "\n"


def exit_code(report: Report) -> int:
    return 1 if report.disagreements else 0


# ---------------------------------------------------------------- writing

def _render_figure(image: Path, target: Path) -> None:
    """Write `image` as a PNG large enough to read axis labels and point markers."""
    if image.suffix.lower() == ".pdf":
        import pdf_pages

        pdf_pages.write_region(image, 1, (0, 0, 1, 1), target)
    else:
        from PIL import Image

        with Image.open(image) as picture:
            picture.save(target)


def _anchor_lines(anchors: list[str]) -> str:
    return "".join(f'<a id="{anchor}"></a>\n' for anchor in anchors)


def _with_items(parts: list, by_item: dict[int, Place], figures: Path, problems: list[str]) -> str:
    """Text as written, with the anchors of each item inside it put on a line before the item."""
    text = ""
    for part in parts:
        if isinstance(part, Item):
            text += ("" if not text or text.endswith("\n") else "\n") + _item_text(by_item[id(part)], by_item, figures, problems)
        else:
            text += part
    return text


def _item_text(place: Place, by_item: dict[int, Place], figures: Path, problems: list[str]) -> str:
    item: Item = place.block
    text = _anchor_lines(place.anchors)
    for n, image in enumerate(item.images, start=1):
        file = re.sub(r"[^A-Za-z0-9._-]+", "-", place.anchors[0]) + (f"-{n}" if len(item.images) > 1 else "") + ".png"
        try:
            _render_figure(image, figures / file)
            text += f"![figure {place.anchors[0]}](figures/{file})\n\n"
        except Exception as error:  # an image format that cannot be read
            problems.append(f"The figure file {image.name} could not be made into an image ({error}).")
    return text + _with_items(item.body, by_item, figures, problems)


def write_source(document: Paper, name: str, target: Path) -> list[str]:
    """Write paper.md, paragraphs.md and figures/ into `target`. Return what could not be written."""
    problems: list[str] = []
    if target.exists():
        shutil.rmtree(target)
    figures = target / "figures"
    figures.mkdir(parents=True)

    rows = places(document)
    by_item = {id(row.block): row for row in rows if isinstance(row.block, Item)}
    paper = [f"# {document.title}"]
    if document.preamble:
        paper.append(f"## Preamble\n\n```{document.preamble_language}\n" + document.preamble + "\n```")
    index = [
        f"# Paragraph index of {name}\n",
        "One row for each paragraph of `paper.md`, with its location and its first words, and one row for "
        "each item, with its kind and its anchor, in the paper's order. A row set in under another is an "
        "item inside that paragraph or item. Each row links to its anchor in `paper.md`.",
    ]
    for row in rows:
        block = row.block
        if isinstance(block, Item):
            if not row.depth:
                paper.append(_item_text(row, by_item, figures, problems))
            index.append(f"{'  ' * row.depth}- [{block.kind} {row.anchors[0]}](paper.md#{row.anchors[0]}) "
                         f"{first_words(block.words)}".rstrip())
        elif isinstance(block, Heading):
            shown = f"{block.number} {block.title}" if block.number else block.title
            paper.append(_anchor_lines(row.anchors) + f"{'#' * (block.level + 1)} {shown}")
            index.append(f"\n{'#' * min(block.level + 1, 3)} {'§' if block.number else ''}{shown}\n")
        elif isinstance(block, RunIn):
            paper.append(_anchor_lines(row.anchors) + f"**{block.title}**")
        elif isinstance(block, Paragraph):
            paper.append(_anchor_lines(row.anchors) + _with_items(block.parts, by_item, figures, problems))
            index.append(f"- [{row.location}](paper.md#{row.anchors[0]}) {first_words(block.words)}".rstrip())
        else:
            paper.append(_anchor_lines(row.anchors) + block.text)

    (target / "paper.md").write_text("\n\n".join(paper) + "\n", encoding="utf-8")
    (target / "paragraphs.md").write_text(re.sub(r"\n{3,}", "\n\n", "\n".join(index)) + "\n", encoding="utf-8")
    return problems


# ---------------------------------------------------------------- the whole conversion, from LaTeX source or Markdown

def convert(paper: Path, name: str, workspace: Path, support=()) -> Conversion:
    """Read the paper, write `<workspace>/source/<name>/`, and report."""
    with tempfile.TemporaryDirectory() as downloads:
        document = read_paper(Path(paper), [Path(folder) for folder in support], Path(downloads))
        problems = write_source(document, name, Path(workspace) / "source" / name)
    report = check(document)
    report.disagreements += problems
    return Conversion(document, report)


# ---------------------------------------------------------------- the script's moves, from a PDF

CUT_ANCHOR = re.compile(r"(figure|table)-[A-Z0-9][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)*")


def write_pages(pdf: Path, folder: Path) -> int:
    """Write an image of every page of `pdf` into `<folder>/pages/`. Return how many pages."""
    import pdf_pages

    pdf_pages.page_count(Path(pdf))   # a PDF that cannot be read leaves the folder as it is
    pages = Path(folder) / "pages"
    if pages.exists():
        shutil.rmtree(pages)
    pages.mkdir(parents=True)
    return pdf_pages.write_pages(Path(pdf), pages)


def cut(pdf: Path, folder: Path, anchor: str, page: int, left: float, top: float, right: float, bottom: float,
        part: int | None = None) -> Path:
    """Cut a region of a page into `<folder>/figures/` or `<folder>/tables/`, and return the image's path.

    `anchor` is the anchor of the figure or table, such as figure-3. The sides of the
    region are percentages of the page's width and height from its top left corner.
    """
    import pdf_pages

    if not CUT_ANCHOR.fullmatch(anchor):
        raise ConversionError(f'"{anchor}" is not the anchor of a figure or a table, such as figure-3 or table-A.1')
    if not all(0 <= side <= 100 for side in (left, top, right, bottom)):
        raise ConversionError(
            "left, top, right and bottom are percentages of the page's width and height, from 0 to 100; "
            f"got {left:g}, {top:g}, {right:g} and {bottom:g}"
        )
    if left >= right:
        raise ConversionError(f"left ({left:g}) must be less than right ({right:g})")
    if top >= bottom:
        raise ConversionError(f"top ({top:g}) must be less than bottom ({bottom:g})")
    if part is not None and part < 1:
        raise ConversionError(f"a part is counted from 1; got {part}")
    pages = pdf_pages.page_count(Path(pdf))
    if not 1 <= page <= pages:
        raise ConversionError(f"the PDF has {pages} pages; there is no page {page}")
    target = Path(folder) / f"{anchor.split('-', 1)[0]}s" / (anchor + (f"-{part}" if part else "") + ".png")
    target.parent.mkdir(parents=True, exist_ok=True)
    pdf_pages.write_region(Path(pdf), page, (left / 100, top / 100, right / 100, bottom / 100), target)
    return target


def index(folder: Path) -> Report:
    """From the `paper.md` a transcriber wrote in `folder`, write `paragraphs.md` there, and report."""
    import transcription

    folder = Path(folder)
    paper = folder / "paper.md"
    if not paper.is_file():
        raise ConversionError(f"no paper.md in {folder}: the transcriber writes it before the index is made")
    read = transcription.read(paper.read_text(encoding="utf-8"))

    report = Report()
    lines = [
        f"# Paragraph index of {folder.name}\n",
        "One row for each paragraph of `paper.md`, with its location and its first words, and one row for "
        "each item, with its kind, its anchor and its page, in the paper's order. A row set in under another "
        "is an item inside that paragraph or item. Each row links to its anchor in `paper.md`.\n",
    ]
    for row in read.rows:
        if row.kind == "heading":
            report.main_sections += row.role == "main"
            report.appendix_sections += row.role == "appendix"
            if row.level > 1:
                lines.append(f"\n{'#' * min(row.level, 3)} {row.title}\n")
        elif row.kind == "paragraph":
            report.paragraphs += 1
            lines.append(f"- [{row.location}](paper.md#{row.anchor}) {first_words(' '.join(row.text))}".rstrip())
        else:
            report.items.append((row.kind, row.anchor))
            where = f", p.{row.page}" if row.page else ""
            lines.append(f"{'  ' * row.depth}- [{row.kind} {row.anchor}{where}](paper.md#{row.anchor}) "
                         f"{first_words(' '.join(row.text))}".rstrip())
    (folder / "paragraphs.md").write_text(re.sub(r"\n{3,}", "\n\n", "\n".join(lines)) + "\n", encoding="utf-8")

    page_images = len(list((folder / "pages").glob("page-*.png")))
    image_files = {
        file.relative_to(folder).as_posix()
        for name in ("figures", "tables") for file in (folder / name).glob("*") if file.is_file()
    }
    report.disagreements = transcription.disagreements(read, page_images, image_files)
    return report


# ---------------------------------------------------------------- the command line

def _main_cut(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="convert.py cut",
        description="Cut a figure or a table out of a page of a PDF, into figures/ or tables/ of source/<input>/.",
        epilog="Exit code: 0 the image was written, 2 nothing was cut.",
    )
    parser.add_argument("pdf", type=Path, help="the PDF")
    parser.add_argument("folder", type=Path, help="the folder source/<input>/")
    parser.add_argument("anchor", help="the anchor of the figure or table, such as figure-3 or table-A.1")
    parser.add_argument("--page", type=int, required=True, help="the page, counted from 1")
    for side, of in (("left", "width"), ("top", "height"), ("right", "width"), ("bottom", "height")):
        parser.add_argument(f"--{side}", type=float, required=True, metavar="PERCENT",
                            help=f"the {side} side of the region, as a percentage of the page's {of} from its top left corner")
    parser.add_argument("--part", type=int, metavar="K",
                        help="for a figure or table in several places: which part this is, counted from 1")
    args = parser.parse_args(argv)
    try:
        target = cut(args.pdf, args.folder, args.anchor, args.page, args.left, args.top, args.right, args.bottom, args.part)
    except ConversionError as error:
        print(f"convert: {error}", file=sys.stderr)
        return 2
    from PIL import Image

    with Image.open(target) as image:
        width, height = image.size
    print(f"Wrote {target} ({width} by {height} pixels): page {args.page}, from {args.left:g}% to {args.right:g}% "
          f"of the width and from {args.top:g}% to {args.bottom:g}% of the height")
    return 0


def _main_index(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="convert.py index",
        description="From the paper.md a transcriber wrote, write paragraphs.md and check the transcription.",
        epilog="Exit code: 0 no disagreement, 1 a disagreement, 2 no paper.md.",
    )
    parser.add_argument("folder", type=Path, help="the folder source/<input>/")
    args = parser.parse_args(argv)
    try:
        report = index(args.folder)
    except ConversionError as error:
        print(f"convert: {error}", file=sys.stderr)
        return 2
    print(f"Wrote {args.folder / 'paragraphs.md'}")
    print(report_text(report), end="")
    return exit_code(report)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["cut"]:
        return _main_cut(argv[1:])
    if argv[:1] == ["index"]:
        return _main_index(argv[1:])
    parser = argparse.ArgumentParser(
        description="Convert a paper into source/<input>/ of a workspace. From LaTeX source or a Markdown file "
                    "this is the whole conversion. From a PDF it writes the page images, and `convert.py cut` and "
                    "`convert.py index` do the rest once an agent has transcribed the text.",
        epilog="Exit code: 0 no disagreement, 1 a disagreement, 2 not converted.",
    )
    parser.add_argument("paper", type=Path,
                        help="a folder of LaTeX source, its main .tex file, a Markdown file or its folder, or a PDF")
    parser.add_argument("input", help="the name of the input, such as yun2025")
    parser.add_argument("workspace", type=Path, help="the folder of the run")
    parser.add_argument("--support", type=Path, action="append", default=[], metavar="FOLDER",
                        help="from LaTeX source or Markdown: a further folder in which files the paper includes, "
                             "or images it shows, are looked for")
    args = parser.parse_args(argv)
    target = args.workspace / "source" / args.input
    try:
        if _is_pdf(args.paper):
            pages = write_pages(args.paper, target)
            print(f"Wrote {pages} page images to {target / 'pages'}")
            return 0
        result = convert(args.paper, args.input, args.workspace, args.support)
    except ConversionError as error:
        print(f"convert: {error}", file=sys.stderr)
        return 2
    print(f"Wrote {target}")
    print(report_text(result.report), end="")
    return exit_code(result.report)


if __name__ == "__main__":
    sys.exit(main())
