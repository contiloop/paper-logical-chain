"""Tests of the convert script's part in converting a PDF.

The script makes the page images, cuts a figure or a table out of a page, and from a
transcribed `paper.md` writes the index and makes the checks. The page images and the
cut are tested on the real Beyond RLHF PDF, which the install command downloads. The
index and the checks are the script's own logic, so they are tested on a small made-up
transcription.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageStat

import check
import convert

ROOT = Path(__file__).resolve().parent.parent
YUN_PDF = ROOT / "local" / "papers" / "yun2025" / "paper.pdf"
SOURCE_FORMAT = ROOT / "prompts" / "formats" / "source.md"
TRANSCRIBER = ROOT / "prompts" / "roles" / "transcriber.md"


# ---------------------------------------------------------------- page images of the real PDF

@pytest.fixture(scope="session")
def yun_pages(tmp_path_factory):
    assert YUN_PDF.is_file(), "run ./install.sh first: it downloads the test paper"
    workspace = tmp_path_factory.mktemp("workspace-yun-pdf")
    code = convert.main([str(YUN_PDF), "yun2025", str(workspace)])
    return workspace / "source" / "yun2025", code


def test_yun_pdf_gives_one_image_for_every_page(yun_pages):
    folder, code = yun_pages
    assert code == 0
    # The PDF has 27 pages.
    assert sorted(p.name for p in (folder / "pages").iterdir()) == [f"page-{n:03d}.png" for n in range(1, 28)]
    assert not (folder / "paper.md").exists(), "paper.md is the transcriber's to write"
    assert not (folder / "paragraphs.md").exists()


def test_yun_pdf_page_images_are_large_enough_to_read(yun_pages):
    folder, _ = yun_pages
    for name in ("page-001.png", "page-009.png", "page-027.png"):
        with Image.open(folder / "pages" / name) as image:
            width, height = image.size
            # A US letter page, 612 by 792 points, at 200 pixels to the inch or more.
            assert height >= 2200, image.size
            assert abs(width / height - 612 / 792) < 0.002, image.size
            colours = image.convert("RGB").getcolors(maxcolors=1 << 24)
        dark = sum(count for count, colour in colours if sum(colour) < 384)
        assert dark / (width * height) > 0.01, f"{name} shows almost no text"


def test_page_images_are_made_again_without_touching_the_transcription(tmp_path):
    folder = tmp_path / "source" / "yun2025"
    (folder / "pages").mkdir(parents=True)
    (folder / "pages" / "page-099.png").write_bytes(b"left over")
    (folder / "paper.md").write_text("transcribed\n", encoding="utf-8")
    assert convert.write_pages(YUN_PDF, folder) == 27
    assert len(list((folder / "pages").iterdir())) == 27 and not (folder / "pages" / "page-099.png").exists()
    assert (folder / "paper.md").read_text(encoding="utf-8") == "transcribed\n"


def test_cli_refuses_a_pdf_that_cannot_be_read(tmp_path, capsys):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    assert convert.main([str(pdf), "x2020", str(tmp_path)]) == 2
    assert "PDF" in capsys.readouterr().err
    assert not (tmp_path / "source" / "x2020" / "pages").exists()


# ---------------------------------------------------------------- a region cut from a real page

def _small(image, box=None):
    """The image, or a box of it, as 120 by 120 grey pixels."""
    return (image.crop(box) if box else image).convert("L").resize((120, 120), Image.LANCZOS)


def _difference(a, b):
    return ImageStat.Stat(ImageChops.difference(a, b)).mean[0]


def test_cut_writes_the_region_of_the_page_at_high_resolution(yun_pages, capsys):
    folder, _ = yun_pages
    # The upper part of page 1: the title, the authors and the start of the abstract.
    code = convert.main(["cut", str(YUN_PDF), str(folder), "figure-1",
                         "--page", "1", "--left", "10", "--top", "5", "--right", "90", "--bottom", "45"])
    assert code == 0
    target = folder / "figures" / "figure-1.png"
    assert str(target) in capsys.readouterr().out
    with Image.open(target) as cut, Image.open(folder / "pages" / "page-001.png") as page:
        # 80% of 612 points by 40% of 792 points.
        assert max(cut.size) >= 2400, cut.size
        assert abs(cut.width / cut.height - (0.80 * 612) / (0.40 * 792)) < 0.01, cut.size
        width, height = page.size
        same = _small(page, (0.10 * width, 0.05 * height, 0.90 * width, 0.45 * height))
        other = _small(page, (0.10 * width, 0.50 * height, 0.90 * width, 0.90 * height))
        assert _difference(_small(cut), same) < 6
        assert _difference(_small(cut), other) > 3 * _difference(_small(cut), same)


def test_cut_names_a_table_and_a_part(yun_pages):
    folder, _ = yun_pages
    box = ["--left", "10", "--top", "10", "--right", "90", "--bottom", "30"]
    assert convert.main(["cut", str(YUN_PDF), str(folder), "table-A.2", "--page", "20", *box]) == 0
    assert convert.main(["cut", str(YUN_PDF), str(folder), "table-3", "--page", "20", "--part", "2", *box]) == 0
    assert sorted(p.name for p in (folder / "tables").iterdir()) == ["table-3-2.png", "table-A.2.png"]


def test_cut_again_replaces_the_image(tmp_path):
    first = convert.cut(YUN_PDF, tmp_path, "figure-2", page=3, left=10, top=10, right=60, bottom=30)
    with Image.open(first) as image:
        before = image.size
    second = convert.cut(YUN_PDF, tmp_path, "figure-2", page=3, left=10, top=10, right=90, bottom=30)
    assert first == second == tmp_path / "figures" / "figure-2.png"
    with Image.open(second) as image:
        assert image.width / image.height > before[0] / before[1]
    assert [p.name for p in (tmp_path / "figures").iterdir()] == ["figure-2.png"]


@pytest.mark.parametrize("arguments, said", [
    (["figure-1", "--page", "28", "--left", "10", "--top", "10", "--right", "90", "--bottom", "30"], "27 pages"),
    (["figure-1", "--page", "0", "--left", "10", "--top", "10", "--right", "90", "--bottom", "30"], "27 pages"),
    (["figure-1", "--page", "1", "--left", "90", "--top", "10", "--right", "10", "--bottom", "30"], "left"),
    (["figure-1", "--page", "1", "--left", "10", "--top", "40", "--right", "90", "--bottom", "30"], "top"),
    (["figure-1", "--page", "1", "--left", "10", "--top", "10", "--right", "120", "--bottom", "30"], "100"),
    (["theorem-1", "--page", "1", "--left", "10", "--top", "10", "--right", "90", "--bottom", "30"], "figure"),
    (["Figure 1", "--page", "1", "--left", "10", "--top", "10", "--right", "90", "--bottom", "30"], "figure"),
])
def test_cut_refuses_what_it_cannot_cut(tmp_path, capsys, arguments, said):
    assert convert.main(["cut", str(YUN_PDF), str(tmp_path), *arguments]) == 2
    assert said in capsys.readouterr().err
    assert not (tmp_path / "figures").exists()


# ---------------------------------------------------------------- the index and the checks, on a made-up transcription

GOOD = r"""# Scheduling with Deadlines

<!-- one sequence: assumption, theorem, lemma -->

<a id="page-1"></a>

<a id="p1-1"></a>
Ada Lee, Ben Ortiz. Institute of Queues.

## Abstract

<a id="p1-2"></a>
We study a scheduling rule and bound the delay it causes.

## 1 Introduction

<a id="p1-3"></a>
Queues grow when jobs arrive faster than they leave [1]. Figure 1 shows the rule, and Table 1 compares it with two others. Earlier rules [2] ignore deadlines.[^1]

[^1]: A deadline is the time by which a job must leave.

<a id="figure-1"></a>
![Figure 1](figures/figure-1.png)

Figure 1: The rule serves the job with the nearest deadline. (a) One queue. (b) Two queues.

<a id="page-2"></a>

## 2 Main Results

### 2.1 The bound

**Delay bound.**

<a id="p2-1"></a>
Under Assumption 1 the rule keeps every queue short, as Theorem 2 states and Fig. 1(a) shows. The bound is
<a id="equation-1"></a>
$$D \le \frac{1}{1-\rho} \tag{1}$$
where $\rho$ is the arrival rate.

<a id="assumption-1"></a>
**Assumption 1** (Stability). The arrival rate satisfies $\rho < 1$.

<a id="theorem-2"></a>
**Theorem 2** (Delay bound). For every arrival rate $\rho<1$, the mean delay satisfies Eq. (1).

<a id="p2-2"></a>
*Proof.* Each job waits for at most the jobs ahead of it, which gives (1). See Lemma 3 and Algorithm 1.

<a id="lemma-3"></a>
**Lemma 3.** A job waits for at most the jobs ahead of it.

<a id="algorithm-1"></a>
**Algorithm 1** Nearest deadline first
1. Sort the jobs by deadline.
2. Serve the first.

<a id="table-1"></a>
![Table 1](tables/table-1.png)

Table 1: Mean delay of three rules.

| Rule | Delay |
|---|---|
| Ours | 1.2 |

## A Proofs

<a id="p2-3"></a>
We prove Lemma 3 here.

## References

<a id="reference-1"></a>
[1] C. Diaz. Queues. 2020.

<a id="reference-2"></a>
[2] E. Fong. Deadlines. 2021.
"""

GOOD_IMAGES = ("figures/figure-1.png", "tables/table-1.png")
ONE_SEQUENCE = "<!-- one sequence: assumption, theorem, lemma -->\n\n"


def make_folder(tmp_path, text, pages=2, images=GOOD_IMAGES):
    """A `source/<input>/` as it stands when the transcriber has finished."""
    folder = tmp_path / "source" / "lee2024"
    for n in range(1, pages + 1):
        file = folder / "pages" / f"page-{n:03d}.png"
        file.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (4, 4), "white").save(file)
    for image in images:
        (folder / image).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (4, 4), "white").save(folder / image)
    (folder / "paper.md").write_text(text, encoding="utf-8")
    return folder


def disagreements(tmp_path, text, **made):
    return convert.index(make_folder(tmp_path, text, **made)).disagreements


def changed(old, new, text=GOOD):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def test_good_transcription_has_no_disagreement(tmp_path):
    report = convert.index(make_folder(tmp_path, GOOD))
    assert report.disagreements == []
    assert convert.exit_code(report) == 0


def test_counts_of_a_transcription(tmp_path):
    report = convert.index(make_folder(tmp_path, GOOD))
    assert (report.main_sections, report.appendix_sections, report.paragraphs) == (2, 1, 6)
    assert report.items == [
        ("figure", "figure-1"), ("equation", "equation-1"), ("assumption", "assumption-1"),
        ("theorem", "theorem-2"), ("lemma", "lemma-3"), ("algorithm", "algorithm-1"), ("table", "table-1"),
        ("reference", "reference-1"), ("reference", "reference-2"),
    ]
    text = convert.report_text(report)
    for line in (
        "Sections: 2 of main text, 1 of appendix",
        "Paragraphs: 6",
        "Figures: 1",
        "Tables: 1",
        "Algorithms: 1",
        "Equations: 1",
        "Numbered statements: 3 (1 assumption, 1 theorem, 1 lemma)",
        "Reference-list entries: 2",
        "Disagreements: none",
    ):
        assert line in text


def test_index_of_a_transcription(tmp_path):
    folder = make_folder(tmp_path, GOOD)
    convert.index(folder)
    index = (folder / "paragraphs.md").read_text(encoding="utf-8")
    assert index.startswith("# Paragraph index of lee2024\n")
    rows = [line for line in index.splitlines() if line.startswith(("#", "- ", "  - "))][1:]
    assert rows == [
        "- [p.1 ¶1](paper.md#p1-1) Ada Lee, Ben Ortiz. Institute of Queues.",
        "## Abstract",
        "- [p.1, Abstract ¶2](paper.md#p1-2) We study a scheduling rule and bound the delay it causes.",
        "## 1 Introduction",
        "- [p.1, Introduction ¶3](paper.md#p1-3) Queues grow when jobs arrive faster than they leave [1]. Figure 1 …",
        "- [figure figure-1, p.1](paper.md#figure-1) Figure 1: The rule serves the job with the nearest deadline. (a) …",
        "## 2 Main Results",
        "### 2.1 The bound",
        "- [p.2, Delay bound ¶1](paper.md#p2-1) Under Assumption 1 the rule keeps every queue short, as Theorem 2 …",
        "  - [equation equation-1, p.2](paper.md#equation-1)",
        "- [assumption assumption-1, p.2](paper.md#assumption-1) **Assumption 1** (Stability). The arrival rate satisfies "
        r"$\rho < 1$.",
        "- [theorem theorem-2, p.2](paper.md#theorem-2) **Theorem 2** (Delay bound). For every arrival rate "
        r"$\rho<1$, the mean delay …",
        "- [p.2, Delay bound ¶2](paper.md#p2-2) *Proof.* Each job waits for at most the jobs ahead of it, …",
        "- [lemma lemma-3, p.2](paper.md#lemma-3) **Lemma 3.** A job waits for at most the jobs ahead of …",
        "- [algorithm algorithm-1, p.2](paper.md#algorithm-1) **Algorithm 1** Nearest deadline first 1. Sort the jobs "
        "by deadline. 2. …",
        "- [table table-1, p.2](paper.md#table-1) Table 1: Mean delay of three rules.",
        "## A Proofs",
        "- [p.2, Proofs ¶3](paper.md#p2-3) We prove Lemma 3 here.",
        "## References",
        "- [reference reference-1, p.2](paper.md#reference-1) [1] C. Diaz. Queues. 2020.",
        "- [reference reference-2, p.2](paper.md#reference-2) [2] E. Fong. Deadlines. 2021.",
    ]


def test_index_leaves_the_transcription_as_it_is(tmp_path):
    folder = make_folder(tmp_path, GOOD)
    convert.index(folder)
    assert (folder / "paper.md").read_text(encoding="utf-8") == GOOD
    assert sorted(p.name for p in folder.iterdir()) == ["figures", "pages", "paper.md", "paragraphs.md", "tables"]


def test_chain_links_into_a_converted_pdf_pass_the_check_script(tmp_path):
    folder = make_folder(tmp_path, GOOD)
    convert.index(folder)
    (tmp_path / "logical-chain.md").write_text(
        "[p.2, Delay bound ¶1](source/lee2024/paper.md#p2-1)\n"
        "[Theorem 2](source/lee2024/paper.md#theorem-2)\n"
        "[Table 1](source/lee2024/tables/table-1.png)\n"
        "[page 2](source/lee2024/pages/page-002.png)\n",
        encoding="utf-8",
    )
    assert check.check_workspace(tmp_path) == []


# -- numbers of a kind run without a gap

def test_kinds_given_as_one_sequence_have_no_gap(tmp_path):
    """Assumption 1, Theorem 2, Lemma 3: paper.md says that the paper numbers the three kinds in one sequence."""
    assert ONE_SEQUENCE in GOOD
    assert disagreements(tmp_path, GOOD) == []


def test_kinds_not_given_as_one_sequence_are_each_checked_alone(tmp_path):
    """The script does not guess: without the line, Theorem 2 and Lemma 3 have numbers missing before them."""
    found = disagreements(tmp_path, changed(ONE_SEQUENCE, ""))
    assert found == [
        "No theorem 1 was extracted, though theorem 2 was.",
        "No lemma 1 to 2 was extracted, though lemma 3 was.",
    ]


def test_a_lost_item_is_not_hidden_by_another_kind_that_carries_its_number(tmp_path):
    """Assumption 1, Lemma 1, Theorem 2: Theorem 1 is lost, though an assumption and a lemma are numbered 1."""
    text = changed(ONE_SEQUENCE, "")
    text = changed('<a id="lemma-3"></a>\n**Lemma 3.**', '<a id="lemma-1"></a>\n**Lemma 1.**', text)
    text = text.replace("Lemma 3", "Lemma 1")
    assert disagreements(tmp_path, text) == ["No theorem 1 was extracted, though theorem 2 was."]


def test_a_lost_item_is_not_hidden_by_another_kind_between_its_neighbours(tmp_path):
    """Theorems 1 and 3 with Lemma 2: Theorem 2 is lost, and so is Lemma 1."""
    text = changed(ONE_SEQUENCE, "").replace("Lemma 3", "Theorem 3").replace("Theorem 2", "Lemma 2")
    text = text.replace("Assumption 1", "Theorem 1")
    for old, new in (("assumption-1", "theorem-1"), ("theorem-2", "lemma-2"), ("lemma-3", "theorem-3")):
        text = changed(f'<a id="{old}"></a>', f'<a id="{new}"></a>', text)
    assert disagreements(tmp_path, text) == [
        "No theorem 2 was extracted, though theorem 3 was.",
        "No lemma 1 was extracted, though lemma 2 was.",
    ]


def test_a_number_carried_twice_in_one_sequence_is_a_disagreement(tmp_path):
    text = changed('<a id="lemma-3"></a>\n**Lemma 3.**', '<a id="lemma-2"></a>\n**Lemma 2.**')
    text = text.replace("Lemma 3", "Lemma 2")
    found = disagreements(tmp_path, text)
    assert found == ["theorem 2 and lemma 2 were both extracted, though paper.md gives assumption, theorem and lemma as one sequence."]


@pytest.mark.parametrize("line, said", [
    ("<!-- one sequence: Theorem, Lemma -->", "Line 3 of paper.md: the kinds of one sequence are not written as"),
    ("<!-- one sequence: theorem -->", "Line 3 of paper.md: the kinds of one sequence are not written as"),
    ("<!-- one sequence: theorem lemma -->", "Line 3 of paper.md: the kinds of one sequence are not written as"),
    ("<!-- one sequence: assumption, theorem, lemma -->\n<!-- one sequence: lemma, remark -->",
     'Line 4 of paper.md: "lemma" is in two sequences.'),
])
def test_a_line_of_one_sequence_that_is_not_well_formed_is_a_disagreement(tmp_path, line, said):
    found = disagreements(tmp_path, changed(ONE_SEQUENCE.strip(), line))
    assert any(said in d for d in found), found


def test_a_gap_in_a_numbered_kind_is_a_disagreement(tmp_path):
    text = GOOD + '\n<a id="reference-4"></a>\n[4] G. Hall. Rules. 2022.\n'
    found = disagreements(tmp_path, text)
    assert len(found) == 1 and "No reference 3 was extracted" in found[0] and "reference 4" in found[0]


def test_a_kind_whose_first_number_is_missing_is_a_disagreement(tmp_path):
    text = changed('<a id="equation-1"></a>', '<a id="equation-2"></a>')
    text = text.replace(r"\tag{1}", r"\tag{2}").replace("Eq. (1)", "Eq. (2)")
    found = disagreements(tmp_path, text)
    assert len(found) == 1 and "No equation 1 was extracted" in found[0]


def test_a_run_of_missing_numbers_is_one_disagreement(tmp_path):
    text = GOOD + '\n<a id="reference-6"></a>\n[6] G. Hall. Rules. 2022.\n'
    found = disagreements(tmp_path, text)
    assert len(found) == 1 and "No reference 3 to 5 was extracted" in found[0]


def test_a_gap_in_statements_that_share_one_sequence_is_reported_once(tmp_path):
    text = changed('<a id="lemma-3"></a>\n**Lemma 3.**', '<a id="lemma-4"></a>\n**Lemma 4.**')
    text = text.replace("Lemma 3", "Lemma 4")
    found = disagreements(tmp_path, text)
    assert len(found) == 1, found
    assert "3 was extracted" in found[0] and "lemma 4" in found[0]
    assert all(kind in found[0] for kind in ("assumption", "theorem", "lemma"))


def test_a_gap_is_not_hidden_by_a_kind_with_its_own_sequence(tmp_path):
    """Theorems 1 and 3 with Lemmas 1 and 2: the lemmas are numbered on their own, so Theorem 2 is missing."""
    text = changed(ONE_SEQUENCE, "")
    text = changed('<a id="assumption-1"></a>\n**Assumption 1**', '<a id="theorem-1"></a>\n**Theorem 1**', text)
    text = changed('<a id="theorem-2"></a>\n**Theorem 2**', '<a id="theorem-3"></a>\n**Theorem 3**', text)
    text = changed('<a id="lemma-3"></a>\n**Lemma 3.**',
                   '<a id="lemma-1"></a>\n**Lemma 1.** First.\n\n<a id="lemma-2"></a>\n**Lemma 2.**', text)
    text = text.replace("Assumption 1", "Theorem 1").replace("Theorem 2 states", "Theorem 3 states")
    text = text.replace("Lemma 3", "Lemma 2")
    found = disagreements(tmp_path, text)
    assert len(found) == 1 and "No theorem 2 was extracted" in found[0] and "lemma" not in found[0]


def test_numbers_with_a_section_or_appendix_part_are_checked_within_it(tmp_path):
    more = ('\n<a id="lemma-C.1"></a>\n**Lemma C.1.** One.\n\n<a id="lemma-C.3"></a>\n**Lemma C.3.** Three.\n'
            '\n<a id="table-A1"></a>\n![Table A1](tables/table-1.png)\nTable A1: More.\n')
    found = disagreements(tmp_path, GOOD + more)
    assert len(found) == 1 and "No lemma C.2 was extracted" in found[0] and "lemma C.3" in found[0]


def test_roman_numbers_are_checked(tmp_path):
    text = changed('<a id="table-1"></a>', '<a id="table-I"></a>').replace("Table 1", "Table I")
    assert disagreements(tmp_path, text) == []
    more = '\n<a id="table-III"></a>\n![Table III](tables/table-1.png)\nTABLE III: More. See Table II.\n'
    found = disagreements(tmp_path, text + more)
    assert len(found) == 2, found
    assert any("No table II was extracted" in d for d in found)
    assert any('"Table II"' in d and "leads to no extracted item" in d for d in found)


def test_equations_numbered_with_a_letter_fill_their_number(tmp_path):
    more = ('\n<a id="p2-4"></a>\nThe two cases are\n<a id="equation-2a"></a>\n<a id="equation-2b"></a>\n'
            r"$$\begin{aligned} a &= b \tag{2a}\\ c &= d \tag{2b}\end{aligned}$$" "\nas Eq. (2) and Eq. (2b) say.\n"
            '\n<a id="equation-3"></a>\n$$e = f \\tag{3}$$\n')
    report = convert.index(make_folder(tmp_path, GOOD + more))
    assert report.disagreements == []
    assert [anchor for kind, anchor in report.items if kind == "equation"] == [
        "equation-1", "equation-2a", "equation-2b", "equation-3",
    ]


# -- every mention of a numbered item leads to an extracted item

@pytest.mark.parametrize("sentence, lost", [
    ("Table 4 lists the loads.", ["Table 4"]),
    ("The loads are listed (see Tab. 4).", ["Table 4"]),
    ("Tables 1–3 list the loads.", ["Table 2", "Table 3"]),
    ("Figures 1, 2 and 3 show them.", ["Figure 2", "Figure 3"]),
    ("Figs. 1 and 4 show them.", ["Figure 4"]),
    ("By Eq. (5) the bound holds.", ["Equation 5"]),
    ("By Equations (1) and (2) the bound holds.", ["Equation 2"]),
    ("By equation (7) the bound holds.", ["Equation 7"]),
    ("This follows from Lemma C.2.", ["Lemma C.2"]),
    ("Corollary 1 then gives the rate.", ["Corollary 1"]),
    ("Thm. 9 gives the rate.", ["Theorem 9"]),
    ("Algorithm 2 sorts faster.", ["Algorithm 2"]),
    ("The loads are listed (see table 4).", ["Table 4"]),
    ("The rule is drawn again (fig. 4).", ["Figure 4"]),
    ("TABLE 4 lists the loads, as do TABLES 5 AND 6.", ["Table 4", "Table 5", "Table 6"]),
    ("By theorem 9 and lemmas 3 and 8 it holds.", ["Theorem 9", "Lemma 8"]),
])
def test_a_mention_that_leads_nowhere_is_a_disagreement(tmp_path, sentence, lost):
    text = changed("We prove Lemma 3 here.", "We prove Lemma 3 here. " + sentence)
    found = disagreements(tmp_path, text)
    assert len(found) == len(lost), found
    for mention in lost:
        assert any(f'"{mention}" leads to no extracted item' in d for d in found), found
    line = text.splitlines().index("We prove Lemma 3 here. " + sentence) + 1
    assert all(f"line {line} of paper.md" in d for d in found)


def test_a_mention_is_read_as_the_longest_kind_it_can_be_and_once(tmp_path):
    """A kind of two words: its own heading is no mention of a theorem, and a lost one is reported once."""
    more = '\n<a id="main-theorem-1"></a>\n**Main Theorem 1.** The rule is optimal.\n'
    assert disagreements(tmp_path, GOOD + more) == []
    found = disagreements(tmp_path / "lost", GOOD + more + '\n<a id="p2-4"></a>\nMain Theorem 5 and main theorem 5 are open.\n')
    assert found == ['"Main Theorem 5" leads to no extracted item (2 times in the text, first at line 84 of paper.md).']


def test_a_mention_of_another_works_item_is_reported(tmp_path):
    """The script cannot tell whose Theorem 7 it is. It reports it, and the person dismisses it."""
    text = changed("We prove Lemma 3 here.", "We prove Lemma 3 here, using Theorem 7 of Diaz [1] twice. Theorem 7 is tight.")
    found = disagreements(tmp_path, text)
    assert found == ['"Theorem 7" leads to no extracted item (2 times in the text, first at line 70 of paper.md).']
    assert convert.exit_code(convert.index(make_folder(tmp_path / "again", text))) == 1


@pytest.mark.parametrize("sentence", [
    "The bound (1) is tight, and (5) items remain.",          # a number without a kind is not a mention
    "Figure 1(b) and Fig. 1a show two queues.",                # a part of an extracted figure
    "Section 5 and Appendix C say more, as does [3].",         # sections and citations are not numbered items
    "Lemmas 3 and Theorem 2 hold; see Theorem 2.",
    "Step 4 of the rule and line 2 of Algorithm 1 sort.",
])
def test_what_is_no_mention_of_a_lost_item_is_no_disagreement(tmp_path, sentence):
    text = changed("We prove Lemma 3 here.", "We prove Lemma 3 here. " + sentence)
    assert disagreements(tmp_path, text) == []


def test_an_item_the_text_never_mentions_is_no_disagreement(tmp_path):
    text = GOOD + '\n<a id="reference-3"></a>\n[3] G. Hall. Rules. 2022.\n\n<a id="table-2"></a>\n' \
                  "![Table 2](tables/table-1.png)\nTable 2: Never mentioned.\n"
    assert "Table 2 " not in GOOD
    assert disagreements(tmp_path, text) == []


# -- the anchors the transcriber wrote

@pytest.mark.parametrize("old, new, said", [
    ('<a id="theorem-2"></a>', '<a id="Theorem 2"></a>', 'Line 44 of paper.md: the anchor "Theorem 2"'),
    ('<a id="theorem-2"></a>', '<a id="thm:delay"></a>', 'Line 44 of paper.md: the anchor "thm:delay"'),
    ('<a id="p2-2"></a>', '<a id="p2-para2"></a>', 'Line 47 of paper.md: the anchor "p2-para2"'),
    ('<a id="figure-1"></a>', '<a id="figure-"></a>', 'Line 22 of paper.md: the anchor "figure-"'),
    ('<a id="lemma-3"></a>', '<a name="lemma-3"></a>', "Line 50 of paper.md: an anchor is not written as"),
    ('<a id="lemma-3"></a>\n**Lemma 3.**', '**Lemma 3.** <a id="lemma-3"></a>',
     "Line 50 of paper.md: an anchor is not written as"),
])
def test_an_anchor_that_is_not_well_formed_is_a_disagreement(tmp_path, old, new, said):
    found = disagreements(tmp_path, changed(old, new))
    assert any(said in d for d in found), found


def test_a_repeated_anchor_is_a_disagreement(tmp_path):
    text = changed('<a id="lemma-3"></a>', '<a id="theorem-2"></a>')
    found = disagreements(tmp_path, text)
    assert 'The anchor "theorem-2" is used 2 times (lines 44 and 50 of paper.md).' in found


def test_a_paragraph_anchor_out_of_order_is_a_disagreement(tmp_path):
    found = disagreements(tmp_path, changed('<a id="p2-2"></a>', '<a id="p2-4"></a>'))
    assert found[0] == 'Line 47 of paper.md: the paragraph anchor is "p2-4" where "p2-2" is next.'
    assert len(found) == 2 and '"p2-3" where "p2-5" is next' in found[1]


def test_a_paragraph_anchor_of_another_page_is_a_disagreement(tmp_path):
    found = disagreements(tmp_path, changed('<a id="p2-1"></a>', '<a id="p1-4"></a>'))
    assert found[0] == 'Line 35 of paper.md: the paragraph anchor is "p1-4" where "p2-1" is next.'


def test_a_paragraph_before_the_first_page_marker_is_a_disagreement(tmp_path):
    text = changed('<a id="page-1"></a>\n\n<a id="p1-1"></a>', '<a id="p1-1"></a>')
    found = disagreements(tmp_path, text)
    assert 'Line 5 of paper.md: the paragraph anchor "p1-1" stands before the first page marker.' in found


def test_a_skipped_page_marker_is_a_disagreement(tmp_path):
    text = changed('<a id="page-2"></a>', '<a id="page-3"></a>').replace('id="p2-', 'id="p3-')
    found = disagreements(tmp_path, text, pages=3)
    assert found == ['Line 27 of paper.md: the page marker is "page-3" where "page-2" is next.']


def test_fewer_page_markers_than_page_images_is_a_disagreement(tmp_path):
    """A transcription that stops early, or leaves a last page out."""
    found = disagreements(tmp_path, GOOD, pages=3)
    assert found == ["The last page marker of paper.md is page-2 and pages/ holds 3 page images."]


def test_no_page_images_is_a_disagreement(tmp_path):
    found = disagreements(tmp_path, GOOD, pages=0)
    assert found == ["The last page marker of paper.md is page-2 and pages/ holds 0 page images."]


def test_a_page_on_which_nothing_starts_has_its_marker_too(tmp_path):
    text = changed('<a id="page-2"></a>', '<a id="page-2"></a>\n\n<a id="page-3"></a>').replace('id="p2-', 'id="p3-')
    folder = make_folder(tmp_path, text, pages=3)
    assert convert.index(folder).disagreements == []
    assert "- [table table-1, p.3](paper.md#table-1)" in (folder / "paragraphs.md").read_text(encoding="utf-8")


# -- a place the transcriber could not read

def test_a_place_marked_unreadable_is_a_disagreement_with_its_page(tmp_path):
    text = changed("| Ours | 1.2 |", "| Ours | [unreadable] |")
    text = changed("We study a scheduling rule", "We study a [unreadable] rule with [unreadable] jobs", text)
    assert disagreements(tmp_path, text) == [
        "Line 13 of paper.md, page 1: [unreadable] marks 2 places that the transcriber could not read.",
        "Line 65 of paper.md, page 2: [unreadable] marks 1 place that the transcriber could not read.",
    ]


# -- sections, however the paper numbers them

SECTIONS = """# A Paper

<a id="page-1"></a>

## Abstract

<a id="p1-1"></a>
Zero.

## {one}

<a id="p1-2"></a>
One.

### {part}

<a id="p1-3"></a>
Two.

## {two}

<a id="p1-4"></a>
Three.

## References

<a id="p1-5"></a>
Diaz. Queues. 2020.

## {appendix}

<a id="p1-6"></a>
Four.
"""


@pytest.mark.parametrize("one, part, two, appendix, locations", [
    ("1 Introduction", "1.1 Setup", "2 Method", "A Proofs", ["Introduction", "Setup", "Method", "Proofs"]),
    ("I. Introduction", "A. Setup", "II. Method", "Appendix A: Proofs", ["Introduction", "Setup", "Method", "Proofs"]),
    ("I. INTRODUCTION", "A. Setup", "V. METHOD", "APPENDIX", ["INTRODUCTION", "Setup", "METHOD", "APPENDIX"]),
    ("Introduction", "Setup", "A Simple Method", "Appendix", ["Introduction", "Setup", "A Simple Method", "Appendix"]),
    ("1. Introduction", "1.1. Setup", "2. Method", "A.1 Proofs", ["Introduction", "Setup", "Method", "Proofs"]),
])
def test_every_top_level_section_is_counted_whatever_its_numbering(tmp_path, one, part, two, appendix, locations):
    folder = make_folder(tmp_path, SECTIONS.format(one=one, part=part, two=two, appendix=appendix), pages=1, images=())
    report = convert.index(folder)
    assert (report.main_sections, report.appendix_sections) == (2, 1)
    index = (folder / "paragraphs.md").read_text(encoding="utf-8")
    assert re.findall(r"- \[p\.1, (.+) ¶\d\]", index) == ["Abstract", *locations[:3], "References", locations[3]]
    assert f"## {one}" in index and f"### {part}" in index


# -- the image of every figure and table

def test_a_figure_or_table_without_an_image_is_a_disagreement(tmp_path):
    found = disagreements(tmp_path, changed("![Table 1](tables/table-1.png)\n\n", ""))
    assert found == ["The table table-1 has no image in paper.md."]


def test_an_image_that_was_not_cut_is_a_disagreement(tmp_path):
    found = disagreements(tmp_path, GOOD, images=("tables/table-1.png",))
    assert found == ["The figure figure-1 links figures/figure-1.png, which does not exist."]


# -- the command

def test_cli_index_reports_and_returns_0(tmp_path, capsys):
    folder = make_folder(tmp_path, GOOD)
    assert convert.main(["index", str(folder)]) == 0
    out = capsys.readouterr().out
    assert str(folder / "paragraphs.md") in out
    assert "Paragraphs: 6" in out and "Disagreements: none" in out


def test_cli_index_returns_1_on_a_disagreement_and_still_writes_the_index(tmp_path, capsys):
    text = changed("We prove Lemma 3 here.", "We prove Lemma 3 here. Table 4 lists the loads.")
    folder = make_folder(tmp_path, text)
    assert convert.main(["index", str(folder)]) == 1
    out = capsys.readouterr().out
    assert "Disagreements: 1" in out and '"Table 4" leads to no extracted item' in out
    assert "(paper.md#p2-3)" in (folder / "paragraphs.md").read_text(encoding="utf-8")


def test_cli_index_returns_2_without_a_transcription(tmp_path, capsys):
    assert convert.main(["index", str(tmp_path)]) == 2
    assert "paper.md" in capsys.readouterr().err
    assert not (tmp_path / "paragraphs.md").exists()


# ---------------------------------------------------------------- the instruction files

def test_the_format_file_is_the_one_place_that_writes_the_commands():
    form = SOURCE_FORMAT.read_text(encoding="utf-8")
    role = TRANSCRIBER.read_text(encoding="utf-8")
    for command in ("scripts/convert.py <PDF> <input> <workspace>", "scripts/convert.py cut ", "scripts/convert.py index "):
        assert command in form, command
    assert "convert.py" not in role
    assert "prompts/formats/source.md" in role
    # What paper.md can hold is defined in the format file alone.
    assert "<!-- one sequence: " in form and "one sequence" not in role
    assert "`[unreadable]`" in form


def test_the_transcriber_role_names_no_agent_tool():
    role = TRANSCRIBER.read_text(encoding="utf-8")
    assert not re.search(r"claude|codex|cursor|gemini|read tool|\b20 pages", role, re.IGNORECASE)

