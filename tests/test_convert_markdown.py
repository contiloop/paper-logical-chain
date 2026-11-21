"""Tests of the convert script on Markdown: small files written in each test, and the person's draft.

The draft is not in the repository. Its path is read from `local/settings.toml`, entry
`[markdown_draft]`, key `post`; the draft test is skipped when the entry or the file is absent.
"""
from __future__ import annotations

import http.server
import re
import socket
import threading
import time
import tomllib
from pathlib import Path

import pytest
from PIL import Image

import check
import convert
import markdown_reader

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "local" / "settings.toml"

ANCHOR = re.compile(r'<a id="([^"]+)"></a>')
INDEX_LINK = re.compile(r"\]\(paper\.md#([^)\s]+)\)")


def png(path: Path, colour=(200, 30, 30)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 30), colour).save(path)
    return path


def run(tmp_path: Path, text: str, name: str = "post.md", files: dict[str, str] | None = None):
    """Write `text` as a Markdown file in tmp_path, convert it, and return what convert wrote."""
    folder = tmp_path / "in"
    folder.mkdir(exist_ok=True)
    for image in files or {}:
        png(folder / image)
    source = folder / name
    source.write_text(text, encoding="utf-8")
    workspace = tmp_path / "ws"
    result = convert.convert(source, "post2026", workspace)
    target = workspace / "source" / "post2026"
    return result, (target / "paper.md").read_text(encoding="utf-8"), (target / "paragraphs.md").read_text(encoding="utf-8")


def headings(document):
    return [(b.level, b.number, b.title) for b in document.blocks if isinstance(b, markdown_reader.Heading)]


def items(result, kind):
    return [anchor for k, anchor in result.report.items if k == kind]


# ---------------------------------------------------------------- title, sections and numbers

def test_a_lone_first_level_1_heading_is_the_title(tmp_path):
    result, paper_md, _ = run(tmp_path, "# The title\n\nOpening.\n\n## One\n\nText.\n\n## Two\n\nMore.\n")
    assert result.document.title == "The title"
    assert paper_md.startswith("# The title\n")
    assert headings(result.document) == [(1, "1", "One"), (1, "2", "Two")]
    assert result.report.main_sections == 2


def test_with_two_level_1_headings_the_title_comes_from_the_file_name(tmp_path):
    result, _, _ = run(tmp_path, "# One\n\nText.\n\n# Two\n\nMore.\n", name="my-notes.md")
    assert result.document.title == "my-notes"
    assert headings(result.document) == [(1, "1", "One"), (1, "2", "Two")]


def test_the_title_comes_from_front_matter_when_no_heading_gives_it(tmp_path):
    text = '---\ntitle: "From the front"\ndate: 2026-01-02\n---\n\n## One\n\nText.\n'
    result, paper_md, _ = run(tmp_path, text)
    assert result.document.title == "From the front"
    assert "## Preamble\n\n```yaml\ntitle: \"From the front\"\ndate: 2026-01-02\n```" in paper_md
    assert "```latex" not in paper_md


def test_headings_that_carry_numbers_keep_them(tmp_path):
    text = "# T\n\n## 1. Start\n\nA.\n\n## 2 Method\n\nB.\n\n### 2.1 Detail\n\nC.\n\n### 2.2 More\n\nD.\n"
    result, paper_md, index = run(tmp_path, text)
    assert headings(result.document) == [(1, "1", "Start"), (1, "2", "Method"), (2, "2.1", "Detail"), (2, "2.2", "More")]
    assert "## 1 Start" in paper_md and "### 2.1 Detail" in paper_md
    assert "- [§2.1 ¶1](paper.md#s2.1-p1) C." in index


def test_headings_without_numbers_are_numbered_in_order(tmp_path):
    text = "# T\n\n## Start\n\nA.\n\n## 2024 results\n\nB.\n\n### Part\n\nC.\n\n### Other part\n\nD.\n"
    result, _, index = run(tmp_path, text)
    assert headings(result.document) == [
        (1, "1", "Start"), (1, "2", "2024 results"), (2, "2.1", "Part"), (2, "2.2", "Other part"),
    ]
    assert "- [§2.2 ¶1](paper.md#s2.2-p1) D." in index


def test_parts_are_tested_for_numbers_section_by_section(tmp_path):
    text = "## A\n\n### 1.1 X\n\nx.\n\n### 1.2 Y\n\ny.\n\n## B\n\n### Z\n\nz.\n"
    result, _, _ = run(tmp_path, text)
    assert headings(result.document) == [(1, "1", "A"), (2, "1.1", "X"), (2, "1.2", "Y"), (1, "2", "B"), (2, "2.1", "Z")]


def test_korean_headings_give_numbered_locations_and_anchors(tmp_path):
    text = "# 제목\n\n## 연초 예측\n\n첫 문단.\n\n둘째 문단.\n\n## 2024년 결과\n\n셋째.\n"
    result, paper_md, index = run(tmp_path, text)
    assert headings(result.document) == [(1, "1", "연초 예측"), (1, "2", "2024년 결과")]
    assert '<a id="s1-p2"></a>\n둘째 문단.' in paper_md
    assert "- [§1 ¶2](paper.md#s1-p2) 둘째 문단." in index
    assert "## 2 2024년 결과" in paper_md


def test_a_heading_that_skips_a_level_is_one_level_in(tmp_path):
    result, _, _ = run(tmp_path, "## A\n\n#### Deep\n\nx.\n\n### Mid\n\ny.\n")
    assert headings(result.document) == [(1, "1", "A"), (2, "1.1", "Deep"), (2, "1.2", "Mid")]


def test_an_abstract_heading_is_the_abstract_and_is_not_numbered(tmp_path):
    result, _, index = run(tmp_path, "# T\n\n## Abstract\n\nShort.\n\n## 1 Start\n\nA.\n\n## 2 End\n\nB.\n")
    assert [(b.role, b.number) for b in result.document.blocks if isinstance(b, markdown_reader.Heading)] == [
        ("abstract", None), ("main", "1"), ("main", "2"),
    ]
    assert "- [Abstract ¶1](paper.md#abstract-p1) Short." in index
    assert result.report.main_sections == 2


def test_two_headings_with_the_same_title_have_different_anchors(tmp_path):
    _, paper_md, _ = run(tmp_path, "## Notes\n\nA.\n\n## Notes\n\nB.\n")
    assert '<a id="s1"></a>\n## 1 Notes' in paper_md and '<a id="s2"></a>\n## 2 Notes' in paper_md


def test_a_file_with_no_heading_is_one_run_of_paragraphs(tmp_path):
    result, _, index = run(tmp_path, "One.\n\nTwo.\n", name="plain.md")
    assert result.document.title == "plain"
    assert result.report.main_sections == 0 and result.report.paragraphs == 2
    assert "- [Before the first heading ¶2](paper.md#start-p2) Two." in index


def test_a_file_whose_only_heading_is_the_title(tmp_path):
    result, _, index = run(tmp_path, "# Only\n\nOne.\n\nTwo.\n")
    assert result.document.title == "Only"
    assert result.report.main_sections == 0
    assert "- [Before the first heading ¶2](paper.md#start-p2) Two." in index


# ---------------------------------------------------------------- paragraphs

def test_text_is_kept_as_written(tmp_path):
    text = "## A\n\nSome *emphasis*, a [link](http://example.org) and a note[^1].\nA second line.\n\n[^1]: The note.\n"
    _, paper_md, _ = run(tmp_path, text)
    assert "Some *emphasis*, a [link](http://example.org) and a note[^1].\nA second line." in paper_md
    assert "[^1]: The note." in paper_md


def test_a_link_reference_definition_is_kept(tmp_path):
    _, paper_md, _ = run(tmp_path, "## A\n\nSee [the site][s].\n\n[s]: http://example.org\n")
    assert "[s]: http://example.org" in paper_md


def test_a_list_a_quote_and_a_display_formula_are_each_one_paragraph(tmp_path):
    text = ("## A\n\n- one\n- two\n\n  still two\n- three\n\n> quoted\n>\n> more\n\n"
            "$$\na = b\n\nc = d\n$$\n\nAfter.\n")
    result, paper_md, _ = run(tmp_path, text)
    assert result.report.paragraphs == 4
    assert '<a id="s1-p1"></a>\n- one\n- two\n\n  still two\n- three' in paper_md
    assert '<a id="s1-p2"></a>\n> quoted\n>\n> more' in paper_md
    assert '<a id="s1-p3"></a>\n$$\na = b\n\nc = d\n$$' in paper_md


def test_a_lone_dollar_pair_in_text_does_not_join_blocks_across_a_heading(tmp_path):
    text = "## A\n\nIt costs $$5 here.\n\n## B\n\nAnd $$6 there.\n"
    result, _, _ = run(tmp_path, text)
    assert headings(result.document) == [(1, "1", "A"), (1, "2", "B")]
    assert result.report.paragraphs == 2


def test_a_code_block_holding_hash_lines_is_code(tmp_path):
    text = "## A\n\n```python\n# not a heading\n![not a figure](x.png)\n```\n\n    # indented code\n\n## B\n\nText.\n"
    result, paper_md, _ = run(tmp_path, text)
    assert headings(result.document) == [(1, "1", "A"), (1, "2", "B")]
    assert items(result, "figure") == []
    assert result.report.paragraphs == 3
    assert '<a id="s1-p1"></a>\n```python\n# not a heading\n![not a figure](x.png)\n```' in paper_md
    assert result.report.disagreements == []


def test_a_block_of_raw_html_has_no_anchor(tmp_path):
    result, paper_md, _ = run(tmp_path, "## A\n\n<div class=\"note\">\nHi\n</div>\n\nText.\n")
    assert result.report.paragraphs == 1
    assert '\n\n<div class="note">\nHi\n</div>\n\n<a id="s1-p1"></a>\nText.' in paper_md


# ---------------------------------------------------------------- tables

def test_a_table_is_an_item(tmp_path):
    text = "## A\n\n| Year | Value |\n|---|---|\n| 2024 | 3 |\n\nAfter.\n"
    result, paper_md, index = run(tmp_path, text)
    assert items(result, "table") == ["table-source-order-1"]
    assert '<a id="table-source-order-1"></a>\n| Year | Value |\n|---|---|\n| 2024 | 3 |' in paper_md
    assert "- [table table-source-order-1](paper.md#table-source-order-1) Year | Value" in index
    assert result.report.paragraphs == 1


# ---------------------------------------------------------------- figures

def test_a_lone_image_with_an_italic_line_under_it_is_a_captioned_figure(tmp_path):
    text = "## A\n\n![a red box](images/box.png)\n*Source: made for the test*\n\nAfter.\n"
    result, paper_md, index = run(tmp_path, text, files={"images/box.png": ""})
    assert items(result, "figure") == ["figure-source-order-1"]
    assert result.report.paragraphs == 1
    figure = paper_md.split('<a id="figure-source-order-1"></a>\n', 1)[1]
    assert figure.startswith("![figure figure-source-order-1](figures/figure-source-order-1.png)\n\n"
                             "![a red box](images/box.png)\n*Source: made for the test*")
    assert "- [figure figure-source-order-1](paper.md#figure-source-order-1) Source: made for the test" in index
    assert (tmp_path / "ws/source/post2026/figures/figure-source-order-1.png").is_file()
    assert result.report.disagreements == []


def test_a_lone_image_without_a_caption_is_indexed_by_its_alt_text(tmp_path):
    result, _, index = run(tmp_path, "## A\n\n![a red box](box.png)\n", files={"box.png": ""})
    assert items(result, "figure") == ["figure-source-order-1"]
    assert result.report.paragraphs == 0
    assert "- [figure figure-source-order-1](paper.md#figure-source-order-1) a red box" in index


def test_an_italic_line_after_a_blank_line_is_a_paragraph(tmp_path):
    result, _, index = run(tmp_path, "## A\n\n![box](box.png)\n\n*Not a caption.*\n", files={"box.png": ""})
    assert result.report.paragraphs == 1
    assert "- [§1 ¶1](paper.md#s1-p1) *Not a caption.*" in index
    assert "- [figure figure-source-order-1](paper.md#figure-source-order-1) box" in index


def test_an_italic_line_that_runs_on_is_not_a_caption(tmp_path):
    text = "## A\n\n![box](box.png)\n*Italic* and then plain words.\n"
    result, paper_md, index = run(tmp_path, text, files={"box.png": ""})
    assert result.report.paragraphs == 1
    assert "  - [figure figure-source-order-1](paper.md#figure-source-order-1) box" in index
    assert "*Italic* and then plain words." in paper_md.split('<a id="s1-p1"></a>', 1)[1]


def test_an_image_inside_running_text_is_a_figure_inside_the_paragraph(tmp_path):
    text = "## A\n\nBefore ![tiny](box.png) after.\n"
    result, paper_md, index = run(tmp_path, text, files={"box.png": ""})
    assert result.report.paragraphs == 1
    assert items(result, "figure") == ["figure-source-order-1"]
    assert "- [§1 ¶1](paper.md#s1-p1) Before" in index
    assert "  - [figure figure-source-order-1](paper.md#figure-source-order-1) tiny" in index
    paragraph = paper_md.split('<a id="s1-p1"></a>\n', 1)[1]
    assert paragraph.startswith("Before ")
    assert '<a id="figure-source-order-1"></a>\n![figure figure-source-order-1](figures/figure-source-order-1.png)' in paragraph
    assert "![tiny](box.png) after." in paragraph


def test_several_images_in_one_paragraph_are_figures_inside_it(tmp_path):
    text = "## A\n\n![one](a.png) ![two](b.png)\n"
    result, _, index = run(tmp_path, text, files={"a.png": "", "b.png": ""})
    assert result.report.paragraphs == 1
    assert items(result, "figure") == ["figure-source-order-1", "figure-source-order-2"]
    assert "  - [figure figure-source-order-2](paper.md#figure-source-order-2) two" in index


def test_the_same_image_used_twice_is_two_figures(tmp_path):
    text = "## A\n\n![first](box.png)\n\n![second](box.png)\n"
    result, _, _ = run(tmp_path, text, files={"box.png": ""})
    figures = tmp_path / "ws/source/post2026/figures"
    assert sorted(p.name for p in figures.iterdir()) == ["figure-source-order-1.png", "figure-source-order-2.png"]
    assert result.report.disagreements == []


def test_an_image_path_with_spaces_and_korean_letters_is_found(tmp_path):
    text = "## A\n\n![그림](<그림 폴더/상자 1.png>)\n\n![two](%EC%83%81%EC%9E%90.png)\n"
    result, _, _ = run(tmp_path, text, files={"그림 폴더/상자 1.png": "", "상자.png": ""})
    assert result.report.disagreements == []
    assert (tmp_path / "ws/source/post2026/figures/figure-source-order-1.png").is_file()
    assert (tmp_path / "ws/source/post2026/figures/figure-source-order-2.png").is_file()


def test_an_image_is_looked_for_in_a_support_folder(tmp_path):
    support = tmp_path / "shared"
    png(support / "box.png")
    source = tmp_path / "post.md"
    source.write_text("## A\n\n![box](box.png)\n", encoding="utf-8")
    result = convert.convert(source, "post2026", tmp_path / "ws", [support])
    assert result.report.disagreements == []


def test_a_missing_local_image_is_a_disagreement(tmp_path, capsys):
    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "post.md").write_text("## A\n\n![gone](images/gone.png)\n*Caption.*\n", encoding="utf-8")
    assert convert.main([str(folder / "post.md"), "post2026", str(tmp_path / "ws")]) == 1
    out = capsys.readouterr().out
    assert "Disagreements: 1\n" in out and "images/gone.png" in out and "not found" in out
    paper_md = (tmp_path / "ws/source/post2026/paper.md").read_text(encoding="utf-8")
    assert '<a id="figure-source-order-1"></a>\n![gone](images/gone.png)\n*Caption.*' in paper_md


def test_an_image_that_cannot_be_made_into_a_png_is_a_disagreement(tmp_path):
    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "drawing.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    (folder / "post.md").write_text("## A\n\n![drawing](drawing.svg)\n", encoding="utf-8")
    result = convert.convert(folder / "post.md", "post2026", tmp_path / "ws")
    assert len(result.report.disagreements) == 1
    assert "drawing.svg" in result.report.disagreements[0]


# ---------------------------------------------------------------- images on the web

class _Server:
    """A web server on 127.0.0.1 that answers each path with the body and type set for it."""

    def __init__(self, routes: dict[str, tuple[str, bytes]]):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path not in routes:
                    self.send_error(404)
                    return
                kind, body = routes[self.path]
                if kind == "slow":
                    time.sleep(3)
                    kind = "image/png"
                self.send_response(200)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def server(tmp_path):
    picture = png(tmp_path / "served.png", (20, 120, 200)).read_bytes()
    served = _Server({
        "/chart.png": ("image/png", picture),
        "/login": ("text/html; charset=utf-8", b"<!doctype html><html><body>Sign in</body></html>"),
        "/slow.png": ("slow", picture),
    })
    yield served
    served.close()


def test_an_image_on_the_web_is_downloaded(tmp_path, server):
    text = f"## A\n\n![chart]({server.url}/chart.png)\n*Source: a server in the test*\n"
    result, paper_md, _ = run(tmp_path, text)
    assert result.report.disagreements == []
    with Image.open(tmp_path / "ws/source/post2026/figures/figure-source-order-1.png") as image:
        assert image.getpixel((5, 5))[:3] == (20, 120, 200)
    assert f"![chart]({server.url}/chart.png)\n*Source: a server in the test*" in paper_md


def test_a_download_that_returns_html_is_one_disagreement(tmp_path, server):
    text = f"## A\n\n![chart]({server.url}/login)\n*Caption.*\n"
    result, paper_md, _ = run(tmp_path, text)
    assert len(result.report.disagreements) == 1
    assert f"{server.url}/login" in result.report.disagreements[0]
    assert '<a id="figure-source-order-1"></a>\n![chart]' in paper_md and "*Caption.*" in paper_md


def test_a_download_with_an_http_error_is_one_disagreement(tmp_path, server):
    result, _, _ = run(tmp_path, f"## A\n\n![chart]({server.url}/nothing.png)\n")
    assert len(result.report.disagreements) == 1
    assert "404" in result.report.disagreements[0]


def test_a_download_that_takes_too_long_is_one_disagreement(tmp_path, server, monkeypatch):
    monkeypatch.setattr(markdown_reader, "DOWNLOAD_SECONDS", 0.5)
    started = time.monotonic()
    result, _, _ = run(tmp_path, f"## A\n\n![chart]({server.url}/slow.png)\n")
    assert time.monotonic() - started < 2.5
    assert len(result.report.disagreements) == 1
    assert f"{server.url}/slow.png" in result.report.disagreements[0]


def test_an_unreachable_url_is_one_disagreement(tmp_path, capsys):
    with socket.socket() as probe:   # a port nothing listens on
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    url = f"http://127.0.0.1:{port}/chart.png"
    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "post.md").write_text(f"## A\n\n![chart]({url})\n*Caption.*\n", encoding="utf-8")
    assert convert.main([str(folder / "post.md"), "post2026", str(tmp_path / "ws")]) == 1
    out = capsys.readouterr().out
    assert "Disagreements: 1\n" in out and url in out
    assert list((tmp_path / "ws/source/post2026/figures").iterdir()) == []


# ---------------------------------------------------------------- the command line

def test_an_empty_file_is_not_converted(tmp_path, capsys):
    (tmp_path / "empty.md").write_text("\n  \n", encoding="utf-8")
    assert convert.main([str(tmp_path / "empty.md"), "post2026", str(tmp_path / "ws")]) == 2
    assert "empty" in capsys.readouterr().err
    assert not (tmp_path / "ws").exists()


def test_a_folder_with_one_markdown_file_is_that_file(tmp_path, capsys):
    folder = tmp_path / "draft"
    folder.mkdir()
    (folder / "post.markdown").write_text("## A\n\nText.\n", encoding="utf-8")
    (folder / "snippet.tex").write_text("$x$\n", encoding="utf-8")
    assert convert.main([str(folder), "post2026", str(tmp_path / "ws")]) == 0
    assert "Sections: 1 of main text" in capsys.readouterr().out


def test_a_folder_with_several_markdown_files_is_not_converted(tmp_path, capsys):
    folder = tmp_path / "draft"
    folder.mkdir()
    for name in ("a.md", "b.md"):
        (folder / name).write_text("Text.\n", encoding="utf-8")
    assert convert.main([str(folder), "post2026", str(tmp_path / "ws")]) == 2
    err = capsys.readouterr().err
    assert "a.md" in err and "b.md" in err


def test_a_folder_with_no_markdown_or_latex_file_is_not_converted(tmp_path):
    (tmp_path / "draft").mkdir()
    assert convert.main([str(tmp_path / "draft"), "post2026", str(tmp_path / "ws")]) == 2


def test_the_report_counts_markdown_as_latex(tmp_path, capsys):
    folder = tmp_path / "in"
    folder.mkdir()
    png(folder / "box.png")
    (folder / "post.md").write_text("# T\n\n## A\n\nOne.\n\n![box](box.png)\n\n| a |\n|---|\n| 1 |\n", encoding="utf-8")
    assert convert.main([str(folder / "post.md"), "post2026", str(tmp_path / "ws")]) == 0
    out = capsys.readouterr().out
    for line in ("Sections: 1 of main text, 0 of appendix", "Paragraphs: 1", "Figures: 1", "Tables: 1",
                 "Algorithms: 0", "Equations: 0", "Numbered statements: 0", "Reference-list entries: 0",
                 "Disagreements: none"):
        assert line in out


# ---------------------------------------------------------------- the person's draft

def _draft() -> Path:
    if not SETTINGS.is_file():
        pytest.skip("no local/settings.toml")
    entry = tomllib.loads(SETTINGS.read_text(encoding="utf-8")).get("markdown_draft", {})
    post = Path(entry.get("post", ""))
    if not entry.get("post") or not post.is_file():
        pytest.skip("no [markdown_draft] post in local/settings.toml, or its file is absent")
    return post


def test_the_persons_draft_converts(tmp_path, capsys):
    post = _draft()
    workspace = tmp_path / "ws"
    assert convert.main([str(post), "post2026", str(workspace)]) == 0
    out = capsys.readouterr().out
    assert "Sections: 11 of main text" in out and "Figures: 14" in out and "Disagreements: none" in out

    source = workspace / "source" / "post2026"
    paper_md = (source / "paper.md").read_text(encoding="utf-8")
    index = (source / "paragraphs.md").read_text(encoding="utf-8")
    numbers = re.findall(r"^## (\d+) ", paper_md, flags=re.M)
    assert numbers == [str(n) for n in range(1, 12)]

    figures = re.findall(r'<a id="(figure-source-order-\d+)"></a>\n!\[figure \1\]\(figures/\1\.png\)\n\n(.*)\n(.*)',
                         paper_md)
    assert len(figures) == 14
    for anchor, image_line, caption in figures:
        assert (source / "figures" / f"{anchor}.png").is_file()
        assert image_line.startswith("![") and re.fullmatch(r"\*[^*].*\*", caption), anchor

    anchors = set(ANCHOR.findall(paper_md))
    linked = INDEX_LINK.findall(index)
    assert linked and [a for a in linked if a not in anchors] == []

    (workspace / "logical-chain.md").write_text(
        "[§1 ¶1](source/post2026/paper.md#s1-p1)\n"
        "[the first figure](source/post2026/paper.md#figure-source-order-1)\n"
        "[its image](source/post2026/figures/figure-source-order-1.png)\n",
        encoding="utf-8",
    )
    assert check.check_workspace(workspace) == []
