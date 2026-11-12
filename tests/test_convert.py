"""Tests of the convert script on a real paper and on made-up LaTeX.

The Beyond RLHF paper comes from local/papers/yun2025/, which the install command
downloads, and is converted once per test session.
"""
from __future__ import annotations

import copy
import re
import shutil
from pathlib import Path

import pytest
from PIL import Image

import check
import convert
from paper_model import Item

ROOT = Path(__file__).resolve().parent.parent
YUN_SOURCE = ROOT / "local" / "papers" / "yun2025" / "latex"

ANCHOR = re.compile(r'<a id="([^"]+)"></a>')
INDEX_LINK = re.compile(r"\]\(paper\.md#([^)\s]+)\)")

# The statements of the Beyond RLHF paper in its order, with the label each has in the source.
YUN_STATEMENTS = [
    ("assumption", "assp:real"), ("assumption", "assp:bdd"), ("definition", "def:cov"),
    ("theorem", "thm:mle"), ("assumption", "assp:reward_model"), ("theorem", "thm:pref_distill"),
    ("theorem", "thm:reverse_kl"), ("lemma", "lem:sig_diff"), ("lemma", "lem:kl_bounded_by_log_sq"),
    ("lemma", "lem:opposite"), ("lemma", "thm:symmetrization"), ("proposition", "thm:oracle"),
    ("remark", "rem:novelty"), ("theorem", "thm:banana"), ("proposition", "prop:klsame"),
]
NOT_STATEMENTS = ("equation", "figure", "table", "algorithm", "reference")


# ---------------------------------------------------------------- Beyond RLHF

@pytest.fixture(scope="session")
def yun(tmp_path_factory):
    assert YUN_SOURCE.is_dir(), "run ./install.sh first: it downloads the test paper"
    workspace = tmp_path_factory.mktemp("workspace-yun")
    result = convert.convert(YUN_SOURCE, "yun2025", workspace)
    return workspace, result


@pytest.fixture(scope="session")
def yun_paper_md(yun):
    workspace, _ = yun
    return (workspace / "source" / "yun2025" / "paper.md").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def yun_index(yun):
    workspace, _ = yun
    return (workspace / "source" / "yun2025" / "paragraphs.md").read_text(encoding="utf-8")


def anchors_of(report, kind):
    return [anchor for k, anchor in report.items if k == kind]


def test_yun_writes_the_source_folder(yun):
    workspace, _ = yun
    source = workspace / "source" / "yun2025"
    assert sorted(p.name for p in source.iterdir()) == ["figures", "paper.md", "paragraphs.md"]


def test_yun_sections(yun):
    _, result = yun
    assert result.report.main_sections == 7
    assert result.report.appendix_sections == 4


def test_yun_section_headings_are_markdown_headings_in_order(yun_paper_md):
    headings = re.findall(r"^## (.+)$", yun_paper_md, flags=re.M)
    assert headings == [
        "Preamble",
        "Abstract",
        "1 Introduction",
        "2 Preliminaries",
        "3 Preference Maximum Likelihood Estimation Approach",
        "4 Preference Distillation Approach",
        "5 Reverse KL Minimization Approach",
        "6 Experiments",
        "7 Conclusion",
        "References",
        "A Related Work",
        "B Additional Remarks on Reverse KL",
        "C Theoretical Guarantees",
        "D Experimental Details",
    ]
    assert r"### C.2 Proofs for Section~\ref{sec:mle}" in yun_paper_md
    assert not re.search(r"\\(sub)*section\*?\{", yun_paper_md.split("## Abstract", 1)[1])


def test_yun_statements_have_the_papers_kinds_and_labels(yun):
    _, result = yun
    statements = [(k, a) for k, a in result.report.items if k not in NOT_STATEMENTS]
    assert statements == YUN_STATEMENTS


def test_yun_figures_tables_algorithms_equations_references(yun):
    _, result = yun
    assert anchors_of(result.report, "figure") == ["fig:rlhf_comparison"]
    assert anchors_of(result.report, "table") == [
        "tab:tasks", "tab:tldr", "tab:academic", "tab:tldr_stats", "tab:tldr_hparams", "tab:chat_hparams",
    ]
    assert anchors_of(result.report, "algorithm") == ["alg:pref_distill"]
    # The source has 24 display environments of a numbered kind, all of them `align`.
    equations = anchors_of(result.report, "equation")
    assert len(equations) == 24 and "eq:pmle_guarantee" in equations
    # The text cites 69 works.
    assert len(anchors_of(result.report, "reference")) == 69


def test_yun_has_paragraphs(yun, yun_index):
    _, result = yun
    rows = [line for line in yun_index.splitlines() if re.match(r"- \[(§|Abstract)", line)]
    assert result.report.paragraphs == len(rows) > 50


def test_yun_no_disagreement(yun):
    _, result = yun
    assert result.report.disagreements == []
    assert convert.exit_code(result.report) == 0


def test_yun_report_text_names_every_count(yun):
    _, result = yun
    text = convert.report_text(result.report)
    for line in (
        "Sections: 7 of main text, 4 of appendix",
        "Figures: 1",
        "Tables: 6",
        "Algorithms: 1",
        "Equations: 24",
        "Numbered statements: 15 (3 assumption, 1 definition, 4 theorem, 4 lemma, 2 proposition, 1 remark)",
        "Reference-list entries: 69",
        "Disagreements: none",
    ):
        assert line in text
    assert f"Paragraphs: {result.report.paragraphs}" in text


def test_yun_every_index_row_links_an_anchor_of_paper_md(yun_paper_md, yun_index):
    anchors = ANCHOR.findall(yun_paper_md)
    assert len(anchors) == len(set(anchors)), "an anchor is used twice"
    linked = INDEX_LINK.findall(yun_index)
    assert linked, "the index links nothing"
    assert [a for a in linked if a not in set(anchors)] == []


def test_yun_every_paragraph_and_item_has_an_anchor(yun, yun_paper_md, yun_index):
    _, result = yun
    anchors = set(ANCHOR.findall(yun_paper_md))
    linked = set(INDEX_LINK.findall(yun_index))
    for _, anchor in result.report.items:
        assert anchor in anchors, anchor
        assert anchor in linked, anchor
    paragraph_anchors = {a for a in anchors if re.search(r"^(s[0-9A-Z]|abstract).*-p\d+$", a)}
    assert len(paragraph_anchors) == result.report.paragraphs
    assert paragraph_anchors <= linked


def test_yun_an_items_anchor_is_named_from_its_label(yun_paper_md):
    assert '<a id="thm:mle"></a>\n\\begin{theorem}\\label{thm:mle}' in yun_paper_md
    assert '<a id="eq:pmle_guarantee"></a>\n\\begin{align}\\label{eq:pmle_guarantee}' in yun_paper_md
    assert '<a id="tab:tasks"></a>\n\\begin{table*}' in yun_paper_md
    assert '<a id="alg:pref_distill"></a>\n\\begin{algorithm}' in yun_paper_md
    # A reference-list entry is named from its citation key.
    assert '<a id="ref-gao24rebel"></a>\n@' in yun_paper_md


def test_an_item_without_a_label_is_named_from_its_kind_and_place(tmp_path):
    """Every item of the paper has a label, so two labels that nothing refers to are taken out of a copy."""
    source = tmp_path / "latex"
    shutil.copytree(YUN_SOURCE, source)
    main = source / "neurips_2026.tex"
    text = main.read_text(encoding="utf-8")
    for label in (r"\label{assp:real}", r"\label{tab:academic}"):
        assert text.count(label) == 1
        text = text.replace(label, "")
    main.write_text(text, encoding="utf-8")
    result = convert.convert(source, "yun2025", tmp_path)
    assert result.report.disagreements == []
    assert anchors_of(result.report, "assumption") == ["assumption-source-order-1", "assp:bdd", "assp:reward_model"]
    assert anchors_of(result.report, "table")[:3] == ["tab:tasks", "tab:tldr", "table-source-order-3"]
    paper_md = (tmp_path / "source" / "yun2025" / "paper.md").read_text(encoding="utf-8")
    assert '<a id="assumption-source-order-1"></a>\n\\begin{assumption}[Realizability]\n' in paper_md


def test_yun_names_no_item_by_a_number(yun, yun_index):
    """No name the script gives an item reads as the number the compiled paper prints."""
    _, result = yun
    assert not [anchor for _, anchor in result.report.items if re.fullmatch(r"[a-z]+-\d+", anchor)]
    names = re.findall(r"- \[([^\]]*)\]\(paper\.md#", yun_index)
    assert not [name for name in names if re.fullmatch(r"\w+ \d+", name)]


def test_yun_abstract_is_indexed_as_its_own_section(yun_paper_md, yun_index):
    assert '<a id="abstract-p1"></a>' in yun_paper_md
    section = yun_index.split("## Abstract", 1)[1].split("\n## ", 1)[0]
    assert "- [Abstract ¶1](paper.md#abstract-p1) Alignment via reinforcement learning" in section


def test_yun_locations_and_anchor_names(yun_index):
    assert "- [§1 ¶1](paper.md#s1-p1) " in yun_index
    assert (
        "- [§3, Convergence guarantee ¶1](paper.md#s3-convergence-guarantee-p1) "
        "Under the assumptions in Section" in yun_index
    )
    assert "- [§C.1 ¶1](paper.md#sC.1-p1) We require the following basic results." in yun_index
    assert "- [theorem thm:mle](paper.md#thm:mle) The PMLE estimate" in yun_index
    assert "- [table tab:tasks](paper.md#tab:tasks) Summary of our proposed methods" in yun_index
    assert "- [figure fig:rlhf_comparison](paper.md#fig:rlhf_comparison) RLHF vs. RKL." in yun_index
    assert "- [algorithm alg:pref_distill](paper.md#alg:pref_distill) Preference Distillation" in yun_index
    assert "  - [equation eq:pmle_guarantee](paper.md#eq:pmle_guarantee)" in yun_index


def test_yun_statement_that_follows_text_is_listed_after_it(yun_index):
    """The statement is listed where it stands in the paper, not before the text it interrupts."""
    setup = yun_index.index("[§2, Theoretical setup ¶1]")
    assert setup < yun_index.index("[assumption assp:real]") < yun_index.index("[assumption assp:bdd]")
    assert yun_index.index("[assumption assp:bdd]") < yun_index.index("[definition def:cov]")


def test_yun_latex_is_kept_as_written(yun_paper_md):
    source = (YUN_SOURCE / "neurips_2026.tex").read_text(encoding="utf-8")
    theorem = source[source.index(r"\begin{theorem}\label{thm:mle}"):source.index(r"\end{theorem}") + 13]
    assert theorem.count(r"\begin{align}") == 1
    written = theorem.replace(r"\begin{align}", '<a id="eq:pmle_guarantee"></a>\n\\begin{align}')
    assert written in yun_paper_md
    table = source[source.index(r"\begin{table}[htb!]"):source.index(r"\end{table}", source.index("tab:tldr_stats")) + 11]
    assert "117K" in table and table in yun_paper_md


def test_yun_included_file_is_in_place_and_macro_definitions_are_kept(yun_paper_md):
    preamble = yun_paper_md.split("## Preamble", 1)[1].split("## Abstract", 1)[0]
    assert r"\input{defs-kjun-v6-overleaf.tex}" not in yun_paper_md
    assert r"\usepackage{commath}" in preamble          # a line of the included file
    assert r"\newtheorem{theorem}{Theorem}" in preamble
    assert preamble.index(r"\usepackage{subfigure}") < preamble.index(r"\usepackage{commath}")
    assert preamble.index(r"\usepackage{commath}") < preamble.index(r"\usepackage{quoting}")
    assert r"$\hpi = \argmin_{\pi\in\Pi} \cL_{\pmle}(\pi)$" in yun_paper_md   # macros are not expanded


def test_yun_comments_are_removed(yun_paper_md):
    assert "removed [section] dependency" not in yun_paper_md
    assert "checklist.tex" not in yun_paper_md
    assert not re.search(r"(?m)^\s*%", yun_paper_md)


def test_yun_every_cross_reference_and_citation_has_its_anchor(yun_paper_md):
    body = yun_paper_md.split("## Abstract", 1)[1]
    anchors = set(ANCHOR.findall(yun_paper_md))
    labels = {label.strip() for group in re.findall(r"\\(?:eq)?ref\{([^}]*)\}", body) for label in group.split(",")}
    keys = {key.strip() for group in re.findall(r"\\cite[a-z]*(?:\[[^\]]*\])*\{([^}]*)\}", body)
            for key in group.split(",")}
    assert len(labels) > 40 and len(keys) == 69
    assert sorted(labels - anchors) == []
    assert sorted(key for key in keys if f"ref-{key}" not in anchors) == []


def test_yun_figure_image_is_readable(yun, yun_paper_md):
    workspace, _ = yun
    figures = workspace / "source" / "yun2025" / "figures"
    assert [p.name for p in figures.iterdir()] == ["fig-rlhf_comparison.png"]
    assert '<a id="fig:rlhf_comparison"></a>\n![figure fig:rlhf_comparison](figures/fig-rlhf_comparison.png)' in yun_paper_md
    with Image.open(figures / "fig-rlhf_comparison.png") as image:
        assert max(image.size) >= 2400, image.size
        colours = image.convert("RGB").getcolors(maxcolors=1 << 24)
    # Axis labels, lines and markers on a white ground: many pixels are not white.
    total = sum(count for count, _ in colours)
    dark = sum(count for count, colour in colours if sum(colour) < 600)
    assert dark / total > 0.01
    assert len(colours) > 50


def test_yun_chain_links_into_the_source_pass_the_check_script(yun):
    workspace, _ = yun
    (workspace / "logical-chain.md").write_text(
        "[§3, Convergence guarantee ¶1](source/yun2025/paper.md#s3-convergence-guarantee-p1)\n"
        "[the first theorem](source/yun2025/paper.md#thm:mle)\n"
        "[the figure](source/yun2025/figures/fig-rlhf_comparison.png)\n",
        encoding="utf-8",
    )
    assert check.check_workspace(workspace) == []


def test_a_lost_statement_is_a_disagreement(yun):
    """One theorem removed from the converted paper: the references to it lead nowhere."""
    _, result = yun
    damaged = copy.deepcopy(result.document)
    kept = [b for b in damaged.blocks if not (isinstance(b, Item) and "thm:pref_distill" in b.anchors)]
    assert len(kept) == len(damaged.blocks) - 1
    damaged.blocks = kept
    report = convert.check(damaged)
    assert any("thm:pref_distill" in d for d in report.disagreements), report.disagreements
    assert convert.exit_code(report) == 1
    assert "Disagreements: none" not in convert.report_text(report)


def test_a_file_not_found_is_a_disagreement(yun):
    _, result = yun
    damaged = copy.deepcopy(result.document)
    damaged.missing.append(r"\input{appendix.tex}")
    report = convert.check(damaged)
    assert any("appendix.tex" in d and "not found" in d for d in report.disagreements), report.disagreements


def test_an_item_the_text_never_refers_to_is_no_disagreement(yun):
    _, result = yun
    referred = {reference.anchor for reference in result.document.references}
    assert "assp:real" not in referred  # the paper never refers to its first assumption
    assert result.report.disagreements == []


# ---------------------------------------------------------------- the command line

def test_cli_refuses_a_missing_input(tmp_path, capsys):
    assert convert.main([str(tmp_path / "nowhere"), "x2020", str(tmp_path)]) == 2
    assert "nowhere" in capsys.readouterr().err
    assert not (tmp_path / "source").exists()


# ---------------------------------------------------------------- command families, on made-up LaTeX

WORKS = "".join(
    f"@article{{{key},\n  author = {{Author {n}}},\n  title = {{Work {n}}},\n  year = {{20{n:02d}}}\n}}\n\n"
    for n, key in enumerate(
        ["alpha2001", "beta2002", "gamma2003", "delta2004", "epsilon2005", "zeta2006", "eta2007", "theta2008",
         "never2009"], start=1)
)
FAMILIES = r"""\documentclass{article}
\usepackage{biblatex,hyperref,cleveref}
\addbibresource{works.bib}
\begin{document}
\section{One}\label{sec:one}
Text \parencite{alpha2001} and \textcite[p.~3]{beta2002}, also \autocite{gamma2003}
and a note \footcite{delta2004}. \Parencite*{epsilon2005} starts; \citeauthor{zeta2006} wrote;
\parencites{eta2007}{theta2008} agree. A \href{http://example.org/ref}{link} and \citetext{see elsewhere}.

\begin{equation}\label{eq:first} a = b \end{equation}
\begin{equation}\label{eq:second} c = d \end{equation}
\begin{table}\caption{Values.}\label{tab:values}\end{table}

See \hyperref[sec:one]{the first section}, \crefrange{eq:first}{eq:second}, \labelcref{tab:values}
and \Crefrange{eq:first}{eq:second}. EXTRA
\printbibliography
\end{document}
"""


def _made_up(folder, extra=""):
    folder.mkdir()
    (folder / "main.tex").write_text(FAMILIES.replace("EXTRA", extra), encoding="utf-8")
    (folder / "works.bib").write_text(WORKS, encoding="utf-8")
    return folder


def test_every_citation_command_family_leads_to_a_reference_entry(tmp_path):
    result = convert.convert(_made_up(tmp_path / "latex"), "made2000", tmp_path)
    assert anchors_of(result.report, "reference") == [
        "ref-alpha2001", "ref-beta2002", "ref-gamma2003", "ref-delta2004", "ref-epsilon2005", "ref-zeta2006",
        "ref-eta2007", "ref-theta2008",
    ]
    assert result.report.disagreements == []


def test_every_cross_reference_command_family_is_checked(tmp_path):
    result = convert.convert(_made_up(tmp_path / "latex"), "made2000", tmp_path)
    referred = [reference.anchor for reference in result.document.references if not reference.anchor.startswith("ref-")]
    assert referred == ["sec:one", "eq:first", "eq:second", "tab:values", "eq:first", "eq:second"]
    assert result.report.disagreements == []


@pytest.mark.parametrize("command, lost", [
    (r"\hyperref[sec:nowhere]{there}", "sec:nowhere"),
    (r"\crefrange{eq:first}{eq:gone}", "eq:gone"),
    (r"\labelcref{tab:none}", "tab:none"),
    (r"\textcite{missing2010}", "missing2010"),
    (r"\Autocite*{missing2011}", "missing2011"),
    (r"\footcites{alpha2001}{missing2012}", "missing2012"),
])
def test_a_reference_through_any_family_to_nothing_is_a_disagreement(tmp_path, capsys, command, lost):
    source = _made_up(tmp_path / "latex", extra=command)
    assert convert.main([str(source), "made2000", str(tmp_path)]) == 1
    report = capsys.readouterr().out
    assert "Disagreements: 1" in report
    assert lost in report.split("Disagreements: 1", 1)[1]

