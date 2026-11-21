"""Read a Markdown file and return it as a `paper_model.Paper`, with the Markdown kept as written.

This is the only file that knows Markdown. markdown-it-py, a CommonMark parser with
tables switched on, finds the blocks; the text of each block is then taken from the
file's own lines, so nothing is rendered or rewritten. Three things the parser does not
do are done here: the front matter is cut off before parsing, a `$$` display formula
that holds a blank line is joined back into one paragraph, and an italic line right
under a lone image is taken as that image's caption.

Headings get section numbers, because locations (`§2 ¶3`) and anchors (`s2-p3`) are
made from them and a title in any language must give a usable anchor. A group of
headings that all begin with a number keeps those numbers; any other group is numbered
in order.

An image whose path is a URL is downloaded. A failed download, like an image file not
found, is a problem of its figure, reported in the reader's own words.
"""
from __future__ import annotations

import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from markdown_it import MarkdownIt

from paper_model import ConversionError, Heading, Item, Paper, Paragraph, Raw

SUFFIXES = (".md", ".markdown")
DOWNLOAD_SECONDS = 30   # the longest a download of one image may take
# A heading that begins with its own number: "3 Title", "3. Title", "3.2 Title".
NUMBERED = re.compile(r"(\d+(?:\.\d+)*)\.?\s+(\S.*)")
DISPLAY = re.compile(r"(?<!\\)\$\$")

_PARSER = MarkdownIt("commonmark").enable("table")


class DownloadFailed(Exception):
    """An image on the web could not be downloaded. The message is the reason."""


Fetch = Callable[[str, Path, float], None]


def download(url: str, target: Path, seconds: float) -> None:
    """Save the image at `url` as `target`, or raise DownloadFailed with the reason."""
    request = urllib.request.Request(url, headers={"User-Agent": "paper-logical-chain"})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=seconds) as response:
            kind = response.headers.get_content_type()
            body = bytearray()
            while chunk := response.read(1 << 16):
                body += chunk
                if time.monotonic() - start > seconds:
                    raise DownloadFailed(f"no complete answer within {seconds:g} seconds")
    except DownloadFailed:
        raise
    except urllib.error.HTTPError as error:
        raise DownloadFailed(f"HTTP error {error.code} {error.reason}") from None
    except urllib.error.URLError as error:
        raise DownloadFailed(str(error.reason)) from None
    except TimeoutError:
        raise DownloadFailed(f"no answer within {seconds:g} seconds") from None
    except Exception as error:   # any other failure of the connection is a failed download, not a crash
        raise DownloadFailed(f"{type(error).__name__}: {error}") from None
    if not kind.startswith("image/") and not _is_image(body):
        raise DownloadFailed(f"the answer is not an image but {kind}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(bytes(body))


def _is_image(body: bytearray) -> bool:
    from PIL import Image

    try:
        with Image.open(BytesIO(body)):
            return True
    except Exception:
        return False


def read(file: Path, support: list[Path], downloads: Path, fetch: Fetch = download,
         seconds: float | None = None) -> Paper:
    """Read the Markdown file `file`.

    A relative image path is looked for beside the file, then in each `support` folder.
    Images on the web are saved in `downloads`, through `fetch`, which may take `seconds`
    an image, DOWNLOAD_SECONDS when not given.
    """
    file = Path(file).resolve()
    text = file.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        raise ConversionError(f"{file} is empty")
    reader = _Reader(file, [file.parent, *support], downloads, fetch, seconds or DOWNLOAD_SECONDS)
    return reader.read(text)


# ---------------------------------------------------------------- the blocks of the file

@dataclass
class _Block:
    kind: str            # "heading", "paragraph", "container", "code", "table" or "raw"
    start: int           # the first line, counted from 0
    end: int             # the line after the last
    images: list = field(default_factory=list)   # the parser's image tokens, in order
    level: int = 0       # of a heading: 1 for #, 2 for ## and so on
    title: str = ""      # of a heading


def _blocks(tokens) -> list[_Block]:
    """The blocks at the top of the file, from the parser's tokens."""
    blocks, i = [], 0
    while i < len(tokens):
        token = tokens[i]
        if token.level != 0 or token.nesting == -1:
            i += 1
            continue
        start, end = token.map
        if token.nesting == 0:
            kind = {"fence": "code", "code_block": "code"}.get(token.type, "raw")
            blocks.append(_Block(kind, start, end))
            i += 1
            continue
        close = next(j for j in range(i + 1, len(tokens)) if tokens[j].level == 0 and tokens[j].nesting == -1)
        inside = tokens[i + 1:close]
        images = [child for t in inside if t.type == "inline" for child in t.children or [] if child.type == "image"]
        if token.type == "heading_open":
            blocks.append(_Block("heading", start, end, level=int(token.tag[1]), title=inside[0].content.strip()))
        elif token.type == "paragraph_open":
            blocks.append(_Block("paragraph", start, end, images))
        elif token.type == "table_open":
            blocks.append(_Block("table", start, end))
        else:   # a list or a block quote
            blocks.append(_Block("container", start, end, images))
        i = close + 1
    return blocks


def _with_lost_lines(blocks: list[_Block], lines: list[str]) -> list[_Block]:
    """Add the lines no block holds, such as a link reference definition, as text written as it is."""
    held = [False] * len(lines)
    for block in blocks:
        held[block.start:block.end] = [True] * (block.end - block.start)
    lost, start = [], None
    for number, line in enumerate([*lines, ""]):
        if start is None and number < len(lines) and not held[number] and line.strip():
            start = number
        elif start is not None and (number == len(lines) or held[number] or not line.strip()):
            lost.append(_Block("raw", start, number))
            start = None
    return sorted(blocks + lost, key=lambda block: block.start)


def _joined_displays(blocks: list[_Block], lines: list[str]) -> list[_Block]:
    """Join the blocks a blank line splits inside a `$$…$$` formula back into one paragraph.

    A formula opens on a line that begins with `$$` and does not run past a heading, so
    `$$` used as text in a sentence joins nothing.
    """
    joined: list[_Block] = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        opening = [line for line in lines[block.start:block.end] if DISPLAY.search(line)]
        if block.kind == "paragraph" and opening and opening[-1].lstrip().startswith("$$"):
            count = len(DISPLAY.findall("\n".join(lines[block.start:block.end])))
            j = i
            while count % 2 and j + 1 < len(blocks) and blocks[j + 1].kind != "heading":
                j += 1
                count += len(DISPLAY.findall("\n".join(lines[blocks[j].start:blocks[j].end])))
            if j > i and count % 2 == 0:
                images = [image for b in blocks[i:j + 1] for image in b.images]
                joined.append(_Block("paragraph", block.start, blocks[j].end, images))
                i = j + 1
                continue
        joined.append(block)
        i += 1
    return joined


def _front_matter(lines: list[str]) -> int:
    """The number of lines of the front matter, a `---` block at the very top; 0 when there is none."""
    if not lines or lines[0].strip() != "---":
        return 0
    return next((n + 1 for n in range(1, len(lines)) if lines[n].strip() in ("---", "...")), 0)


def _wholly_italic(line: str) -> bool:
    """Whether the line is one run of italics, `*…*` or `_…_`, with nothing outside it."""
    tokens = _PARSER.parseInline(line.strip(), {})[0].children or []
    if len(tokens) < 3 or tokens[0].type != "em_open" or tokens[-1].type != "em_close":
        return False
    depth = 0
    for token in tokens[:-1]:
        depth += {"em_open": 1, "em_close": -1}.get(token.type, 0)
        if depth == 0:
            return False
    return True


def _squeeze(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------- the reader

class _Reader:
    def __init__(self, file: Path, folders: list[Path], downloads: Path, fetch: Fetch, seconds: float):
        self.file, self.folders, self.downloads, self.fetch, self.seconds = file, folders, downloads, fetch, seconds
        self.document = Paper()
        self.env: dict = {}
        self.place = {"figure": 0, "table": 0}   # how many items of each kind have been met

    def read(self, text: str) -> Paper:
        lines = text.split("\n")
        front = _front_matter(lines)
        if front:
            self.document.preamble = "\n".join(lines[1:front - 1]).strip("\n")
            self.document.preamble_language = "yaml"
        parsed = [""] * front + lines[front:]
        blocks = _blocks(_PARSER.parse("\n".join(parsed), self.env))
        blocks = _joined_displays(_with_lost_lines(blocks, parsed), parsed)

        self.document.title = self._title(blocks)
        headings = _numbered([block for block in blocks if block.kind == "heading"])
        for block in blocks:
            written = "\n".join(lines[block.start:block.end]).strip("\n")
            if block.kind == "heading":
                self.document.blocks.append(headings[id(block)])
            elif block.kind == "raw":
                self.document.blocks.append(Raw(written))
            elif block.kind == "code":
                self.document.blocks.append(Paragraph([written], _squeeze(written)))
            elif block.kind == "table":
                first = [cell.strip() for cell in lines[block.start].strip().strip("|").split("|")]
                self.document.blocks.append(Item("table", [self._name("table")], [written], " | ".join(first)))
            else:
                self.document.blocks.append(self._paragraph(block, written))
        return self.document

    def _title(self, blocks: list[_Block]) -> str:
        """The title, taken out of `blocks` when it is the file's heading."""
        headings = [block for block in blocks if block.kind == "heading"]
        if headings and headings[0].level == 1 and not any(h.level == 1 for h in headings[1:]):
            blocks.remove(headings[0])
            return headings[0].title
        found = re.search(r"(?m)^title:\s*(.+?)\s*$", self.document.preamble)
        if found and found.group(1).strip("\"'"):
            return found.group(1).strip("\"'")
        return self.file.stem

    def _name(self, kind: str) -> str:
        self.place[kind] += 1
        return f"{kind}-source-order-{self.place[kind]}"

    # ----- paragraphs and figures

    def _paragraph(self, block: _Block, written: str) -> Paragraph | Item:
        """A paragraph with the figures inside it, or a figure that stands alone, with its caption."""
        if block.kind == "paragraph" and len(block.images) == 1:
            first, *rest = written.split("\n")
            alone = [t for t in _PARSER.parseInline(first.strip(), self.env)[0].children or []
                     if not (t.type == "text" and not t.content.strip())]
            if len(alone) == 1 and alone[0].type == "image":
                if not rest:
                    return self._figure(block.images[0], written, block.images[0].content)
                if len(rest) == 1 and _wholly_italic(rest[0]):
                    return self._figure(block.images[0], written, rest[0].strip()[1:-1].strip())
        parts: list[str | Item] = []
        unplaced: list = []   # images whose markup was not found in the text: their figures go at the end
        taken = 0
        for image, (start, stop) in zip(block.images, self._image_places(written, block.images)):
            if start is None:
                unplaced.append(image)
                continue
            parts += [written[taken:start], self._figure(image, written[start:stop], image.content)]
            taken = stop
        parts.append(written[taken:])
        parts += [self._figure(image, "", image.content) for image in unplaced]
        return Paragraph([part for part in parts if part != ""], _squeeze(written))

    def _image_places(self, written: str, images: list) -> list[tuple[int | None, int | None]]:
        """Where each image token's markup stands in `written`, in order; (None, None) where it is not found."""
        places, at = [], 0
        for image in images:
            found = (None, None)
            for candidate in re.finditer(r"!\[", written[at:]):
                start = at + candidate.start()
                stop = _markup_end(written, start)
                tokens = _PARSER.parseInline(written[start:stop], self.env)[0].children or []
                if (len(tokens) == 1 and tokens[0].type == "image" and tokens[0].attrGet("src") == image.attrGet("src")
                        and tokens[0].content == image.content):
                    found = (start, stop)
                    at = stop
                    break
            places.append(found)
        return places

    def _figure(self, image, written: str, words: str) -> Item:
        anchor = self._name("figure")
        item = Item("figure", [anchor], [written] if written else [], _squeeze(words))
        source = image.attrGet("src") or ""
        if re.match(r"https?://", source, re.IGNORECASE):
            name = Path(urllib.parse.unquote(urllib.parse.urlparse(source).path)).name or "image"
            try:
                self.fetch(source, self.downloads / anchor / name, self.seconds)
                item.images.append(self.downloads / anchor / name)
            except DownloadFailed as error:
                self.document.problems[anchor] = f"The image {source} could not be downloaded: {error}."
            return item
        found = self._find(source)
        if found:
            item.images.append(found)
        else:
            self.document.problems[anchor] = f"{urllib.parse.unquote(source)}: the file was not found."
        return item

    def _find(self, source: str) -> Path | None:
        for name in dict.fromkeys([urllib.parse.unquote(source), source]):
            for folder in self.folders:
                if name and (folder / name).is_file():
                    return folder / name
        return None


def _numbered(blocks: list[_Block]) -> dict[int, Heading]:
    """The heading of each heading block, by the block's id, with its level and its number.

    The shallowest level present is level 1. A heading is one level in from the nearest
    heading above it that is shallower, so a skipped level does not count. An "Abstract"
    heading is the abstract and takes no part in the numbering.
    """
    @dataclass
    class Node:
        block: _Block | None
        level: int
        children: list = field(default_factory=list)

    root = Node(None, 0)
    stack: list[tuple[int, Node]] = [(0, root)]
    for block in blocks:
        while stack[-1][0] >= block.level:
            stack.pop()
        node = Node(block, stack[-1][1].level + 1)
        stack[-1][1].children.append(node)
        stack.append((block.level, node))

    headings: dict[int, Heading] = {}

    def number(parent: Node, prefix: str | None) -> None:
        group = [child for child in parent.children if child.block.title.lower() != "abstract"]
        written = [NUMBERED.fullmatch(child.block.title) for child in group]
        for child in parent.children:
            if child.block.title.lower() == "abstract":
                headings[id(child.block)] = Heading("abstract", child.level, None, child.block.title)
                number(child, None)
        for place, (child, found) in enumerate(zip(group, written), start=1):
            if group and all(written):
                own, title = found.group(1), found.group(2).strip()
            elif prefix is None and parent is not root:
                own, title = None, child.block.title
            else:
                own, title = (f"{prefix}.{place}" if prefix else str(place)), child.block.title
            role = "other" if own is None else "main"
            headings[id(child.block)] = Heading(role, child.level, own, title)
            number(child, own)

    number(root, "")
    return headings


def _markup_end(text: str, start: int) -> int:
    """The place after the image markup that starts at `start` with `![`: its text, then a link or a label."""
    end = _closing(text, start + 1, "[", "]")
    if end < len(text) and text[end] == "(":
        return _closing(text, end, "(", ")")
    if end < len(text) and text[end] == "[":
        return _closing(text, end, "[", "]")
    return end


def _closing(text: str, start: int, opening: str, closing: str) -> int:
    """The place after the partner of the bracket at `start`, skipping escaped characters and `<…>`."""
    depth, place = 0, start
    while place < len(text):
        character = text[place]
        if character == "\\":
            place += 2
            continue
        if character == "<" and opening == "(":
            stop = text.find(">", place)
            place = stop + 1 if stop >= 0 else place + 1
            continue
        depth += (character == opening) - (character == closing)
        place += 1
        if depth == 0:
            return place
    return len(text)
