# Format: source/&lt;input&gt;/

The text, converted, in `source/<input>/` of the workspace, where `<input>` is named as `prompts/work-graph.md` says. The author and the reviewers read it in place of the original. From LaTeX source or a Markdown file the convert script writes all of it. From a PDF the transcriber writes `paper.md` and the script writes the rest.

## Files

- `paper.md`: the whole text in its order, with an anchor on every paragraph and on every item. Items are statements (theorem, lemma, assumption and the like), numbered equations, figures, tables, algorithms and reference-list entries. From LaTeX source the text is the LaTeX as written, with included files in place and comments removed; the paper's macros are defined under `## Preamble`. From a PDF it is a transcription of the pages, with the mathematics in LaTeX.
- `paragraphs.md`: one row for each paragraph and each item, in the text's order, each a location linked to its anchor in `paper.md`. A row set in under another is an item inside that paragraph or item.
- `figures/`: an image of every figure, named after its anchor, such as `fig-delay.png` for `fig:delay`. From a PDF the image holds the caption too.
- `tables/`, from a PDF only: an image of every table with its caption, such as `table-2.png`.
- `pages/`, from a PDF only: an image of every page of the file. `page-003.png` is the third.

Which image to open:

- For a figure, the image or images that `paper.md` links after the figure's anchor.
- For a table from a PDF, its image in `tables/`. The image is the reference for the table's values, because a transcription can garble a table with nothing in the text to show it; the cells in `paper.md` serve to find a value. From LaTeX source the table in `paper.md` is the reference.
- For a place marked `[unreadable]`, the image of its page in `pages/`.

## Locations

A location is text that a reader of the text can follow, written as a link to the anchor of what it names. From a file at the top of the workspace the target is `source/<input>/paper.md#<anchor>`.

A paragraph's location and anchor are those of its row in `paragraphs.md`.

- From LaTeX source: section, run-in heading, paragraph: `[§3, Delay bound ¶2](source/lee2024/paper.md#s3-delay-bound-p2)`. The section is the innermost numbered one, such as `§3.2` or `§B.2`; the abstract is `Abstract`, and a section without a number is named by its title. The heading is the run-in heading the paragraph stands under, when there is one. Paragraph numbers restart under each heading and each run-in heading.
- From Markdown: section, paragraph: `[§2.1 ¶3](source/lee2024/paper.md#s2.1-p3)`. The section is the innermost one, numbered as "From Markdown" below says; the abstract is `Abstract`. A paragraph before the first heading is `[Before the first heading ¶1](source/lee2024/paper.md#start-p1)`. Paragraph numbers restart under each heading.
- From a PDF: page, heading, paragraph: `[p.3, Delay bound ¶2](source/lee2024/paper.md#p3-2)`. The page is the page of the file on which the paragraph starts, counted from 1 as in the names of the page images; it can differ from the page number the paper prints. The heading is the innermost one, a run-in heading or else a section's title without its number; a paragraph before the first heading has none: `[p.1 ¶1]`. `¶2` is the second paragraph that starts on that page.

An item's location is its kind and number as the paper prints them, linked to its anchor: `[Theorem 2](source/lee2024/paper.md#theorem-2)`.

## From LaTeX source, no printed number

The script runs no LaTeX, so no number that the compiled paper prints on a statement, an equation, a figure, a table or a reference-list entry is in this folder.

- Every `\label` of the source is an anchor on the section, paragraph or item that holds it, with a character a link cannot hold written as `-`. So `\ref{thm:delay}` in the text leads to `#thm:delay`, and `\cite{lee2020}` leads to `#ref-lee2020`.
- An item without a label is named by its kind and its place among the items of that kind in the source, such as `#table-source-order-3`. That place is not the printed number: kinds that share one counter, and items the paper does not number, make the two differ.
- To give an item's printed number, work it out from the source: the `\newtheorem` lines under `## Preamble` say which kinds share a counter. Link the item's anchor either way.
- Section numbers are counted from the sectioning commands, the starred ones left out, with letters after `\appendix`.

## From Markdown

The convert script writes all of the folder. The text is the Markdown as written; the front matter, if any, stands under `## Preamble` as YAML.

- Every heading but the title and an "Abstract" heading has a section number, whatever language its title is in, and `paper.md` shows it before the title. When every top-level heading begins with a number (`3`, `3.` or `3.2`, then a space), those numbers are used; otherwise the top-level headings are numbered 1, 2, 3 in order. The same holds for the parts of each section: their own numbers when every part begins with one, otherwise 3.1, 3.2 in order under the section's number. A heading that skips a level is one level in from the nearest shallower heading above it. The title is the first heading when it is the only one of level 1. An "Abstract" heading is the abstract.
- Every paragraph has an anchor. A list, a block quote, a code block and a `$$…$$` formula are each one paragraph. A block of raw HTML has no anchor.
- The only items are figures and tables, named by kind and place: `#figure-source-order-3`, `#table-source-order-1`. Links and footnotes are as written, and nothing checks where they lead.
- An image alone in its paragraph is a figure; a line set wholly in italics right under it, with no blank line between, is its caption. An image inside text is a figure inside that paragraph.
- To check a figure, open its image in `figures/`, named after its anchor: the first image `paper.md` links after the figure's anchor, such as `figures/figure-source-order-3.png`. The image link written in the text after it leads to the original file, not into this folder. A figure whose image was not found or could not be downloaded has none; the convert report names it.

## From a PDF, the script's commands

Run each command in the project folder, the one that holds `prompts/` and `scripts/`. `<folder>` is the path of `source/<input>/`.

1. Write `pages/`. Exit code 0, or 2 when the PDF cannot be read.

   ```
   uv run python scripts/convert.py <PDF> <input> <workspace>
   ```

2. The transcriber writes `paper.md` and has the script cut each figure and each table out of its page:

   ```
   uv run python scripts/convert.py cut <PDF> <folder> <anchor> --page <N> --left <L> --top <T> --right <R> --bottom <B>
   ```

   `<anchor>` is the anchor of the figure or table, such as `figure-3`, and `<N>` its page. Each side of the region is a percentage from the top left corner of the page: `--left` and `--right` of the page's width, `--top` and `--bottom` of its height. `--left 10 --top 20 --right 90 --bottom 55` is the region from 10% to 90% of the width and from 20% to 55% of the height. The image goes to `figures/<anchor>.png` or `tables/<anchor>.png` and replaces an earlier image of that name. For a figure or table printed in several places, such as a table that runs on to the next page, add `--part 1`, `--part 2` and so on, which give `<anchor>-1.png`, `<anchor>-2.png`. Exit code 0, or 2 when nothing was cut.

3. Write `paragraphs.md` from `paper.md` and check `paper.md`. The report gives the counts of what was extracted and every disagreement. Exit code 0 with no disagreement, 1 with one, 2 when the folder has no `paper.md`.

   ```
   uv run python scripts/convert.py index <folder>
   ```

## For the transcriber: `paper.md` from a PDF

What is a paragraph and what is an item:

- A paragraph is a block of text that the page sets apart from the next by an indent or by space. A display equation or a list does not start a new paragraph. The text of a proof is paragraphs.
- An item is something the paper numbers: a statement, a display equation, a figure, a table, an algorithm, an entry of a numbered reference list. A statement without a number, an entry of a reference list without numbers, and an item the paper prints a second time under the same number, such as a theorem stated again before its proof, are paragraphs. A display equation without a number stays in its paragraph with no anchor.
- A statement, a figure, a table or an algorithm ends the paragraph before it, and the text after it is a new paragraph. A figure, a table or an algorithm that the page shows in the middle of a paragraph is written after that paragraph.

The forms:

- Every anchor is `<a id="…"></a>` alone on a line, directly before what it names.
- The title is a level-1 heading. Under it stands one line for each group of kinds that the paper numbers in one sequence, such as `<!-- one sequence: assumption, definition, theorem -->`, with the kinds named as in the anchors. A kind is in such a line only where the printed numbers show it, as when Definition 3 follows Assumption 2 and the paper has no Definition 1. A kind numbered on its own is in no line, and no kind is in two.
- A page marker for every page of the file, in order: `<a id="page-3"></a>` stands before the first paragraph, heading or item that starts on the third page. A paragraph or an item that runs over the end of a page is written whole, and the next page's marker comes after it. A page on which nothing starts has its marker directly before the next page's marker, or last in the file.
- Every heading the paper prints, with its printed number: `##` for a top-level section, the abstract and the reference list among them, `###` for a part of a section, `####` for a part of that. A run-in heading, one that starts the line of a paragraph, is a bold line of its own, with a blank line before and after it, before the paragraph.
- A paragraph's anchor is `p`, the page, a hyphen, and the paragraph's number among those that start on that page, counted from 1: `#p3-2`. The author names and affiliations under the title are a paragraph.
- An item's anchor is its kind, a hyphen, and the number the paper prints on it, without brackets: `#theorem-2`, `#lemma-C.1`, `#equation-12`, `#figure-3`, `#table-A1`, `#table-II`, `#algorithm-1`, `#reference-27`. The kind is the name the paper prints on the item, in lower case, with a hyphen between two words.
- Text: the words as printed, a word broken over two lines written whole, mathematics in a line as LaTeX in `$…$`.
- A display equation: LaTeX in `$$…$$`, with its printed number as `\tag{4}`, inside its paragraph or statement with no blank line before or after it. Its anchor is on the line before it; a display with several numbers has one anchor line for each.
- A statement starts with its name and number as printed: `**Theorem 2** (Delay bound).`
- A figure: the link to its image, then its caption as printed.
- A table: the link to its image, then its caption as printed, then its cells as a Markdown table, every value as printed.
- An algorithm: its title, then its lines, one to a line, with the line numbers the paper prints.
- A footnote: `[^3]` at its mark, and `[^3]: …` for its text after the paragraph that holds the mark.
- `[unreadable]` in the place of a character, a word or a value that could not be read in the PDF or on the page's image.
- Not written: what a page prints around the text, such as a running head or foot, a page number, line numbers or a stamp in the margin.

A made-up sample:

```md
<a id="page-3"></a>

## 3 Scheduling with Deadlines

<a id="p3-1"></a>
We now state the scheduling rule. It extends the greedy rule of Section 2 [14].

**Delay bound.**

<a id="p3-2"></a>
Under Assumption 1 the rule keeps every queue short, as Table 2 shows.

<a id="theorem-2"></a>
**Theorem 2** (Delay bound). For every arrival rate $\rho<1$, the mean delay $D$ satisfies
<a id="equation-4"></a>
$$D \le \frac{1}{1-\rho}. \tag{4}$$

<a id="p3-3"></a>
*Proof.* Each job waits for at most the jobs ahead of it.

<a id="table-2"></a>
![Table 2](tables/table-2.png)

Table 2: Mean delay of each rule.

| Rule | Delay |
|---|---|
| Greedy | 3.1 |
| Ours | 2.0 |
```

The `index` command reports a disagreement when:

- an anchor or a `one sequence` line is not in its form, an anchor is not alone on its line, or an anchor is used twice;
- the page markers do not run in order from `page-1` to the last image in `pages/`, or the paragraph anchors of a page do not run in order from 1;
- a place is marked `[unreadable]`;
- a figure or a table links no image, or an image that is not in the folder;
- a numbered kind misses a number between 1 and its highest, counted within each section or appendix for numbers such as `3.2` or `C.1`. The kinds of a `one sequence` line are counted together, and no number may occur twice among them. Every other kind is counted on its own, so a kind that shares a sequence and is in no line shows missing numbers;
- the text mentions an item by kind and number, as in "Table 3", "Thm. 4" or "Eqs. (5)–(7)", and no such item was extracted. A mention of another work's item is reported too.
