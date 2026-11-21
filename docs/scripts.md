# Scripts

What each script takes and produces. The scripts read and write files and know nothing of any agent tool. Run them from the project folder. What `source/<input>/` holds is defined in `prompts/formats/source.md`.

## convert, from LaTeX source

```
uv run python scripts/convert.py <paper> <input> <workspace> [--support <folder>]
```

- Takes: the paper, as a folder of LaTeX source or its main `.tex` file; the input's name, such as `lee2024`; the workspace. `--support` names a further folder in which included files are looked for, and may be given more than once.
- Writes: `<workspace>/source/<input>/` with `paper.md`, `paragraphs.md` and `figures/`.
- Prints: how many sections, paragraphs, figures, tables, algorithms, equations, numbered statements and reference-list entries it extracted, and every disagreement: a cross-reference or a citation that leads to no extracted item, and an included file or a figure file that was not found.
- Exit code: 0 with no disagreement; 1 with one or more, the files written all the same; 2 when the paper could not be converted.

The LaTeX is kept as written. No LaTeX engine runs, so the script knows no number the compiled paper prints: an item's anchor is its `\label`, or its kind and its place among the items of that kind.

## convert, from a Markdown file

```
uv run python scripts/convert.py <file.md> <input> <workspace> [--support <folder>]
```

- Takes: a `.md` or `.markdown` file, or a folder that holds exactly one such file and no `.tex` file with `\documentclass`; the input's name; the workspace. `--support` names a further folder in which images are looked for, after the file's own folder.
- Writes, prints and exit code: as from LaTeX source. Exit code 2 also for an empty file or a folder with no or several Markdown files. The disagreements are an image file not found, an image that could not be made into a PNG (such as an SVG), and an image that could not be downloaded, each once.

The reader, `markdown_reader.py`, uses markdown-it-py in CommonMark mode with tables switched on to find the blocks, and takes each block's text from the file's lines, so the Markdown stays as written. It does three things itself: it cuts off the front matter, which goes under `## Preamble` as YAML; it keeps a `$$…$$` formula that holds a blank line as one paragraph; and it takes a line set wholly in italics right under a lone image as that image's caption.

Headings get section numbers, because locations and anchors are made from them and a title in Korean or another script gives no anchor. When every heading of a group (the top-level sections, or the parts of one section) begins with a number such as `3` or `3.2`, those numbers are used; otherwise the group is numbered in order. A first heading of level 1 with no other level-1 heading is the title.

An image whose path is an `http` or `https` URL is downloaded, with a limit of 30 seconds an image (`DOWNLOAD_SECONDS` in `markdown_reader.py`). So a conversion from Markdown can use the network; a failed download leaves the figure in the text without an image.

## convert, from a PDF

The script does not read the text of a PDF. An agent, the transcriber, writes `paper.md` between the first command and the last.

```
uv run python scripts/convert.py <PDF> <input> <workspace>
```

- Writes: `<workspace>/source/<input>/pages/`, an image of every page. Exit code 0, or 2 when the PDF could not be read.

```
uv run python scripts/convert.py cut <PDF> <folder> <anchor> --page <N> --left <L> --top <T> --right <R> --bottom <B> [--part <K>]
```

- Takes: the PDF; the folder `source/<input>/`; the anchor of a figure or a table, such as `figure-3`; its page; and the region, each side as a percentage of the page's width or height from the top left corner.
- Writes: `figures/<anchor>.png` or `tables/<anchor>.png`, in place of an earlier image of that name; with `--part K`, `<anchor>-K.png`. Exit code 0, or 2 when nothing was cut.

```
uv run python scripts/convert.py index <folder>
```

- Takes: the folder `source/<input>/`, with `paper.md` written.
- Writes: `paragraphs.md`. `paper.md` is not changed.
- Prints: the counts, as from LaTeX source, and every disagreement: an anchor that is not well formed, not in order or used twice; a page without its marker; a place marked as unreadable; a figure or a table without its image; a number missing from the sequence of a numbered kind; a mention of a numbered item, such as "Table 3", that leads to no extracted item.
- Exit code: 0, 1 or 2, as from LaTeX source; 2 when the folder has no `paper.md`.

## check

```
uv run python scripts/check.py <workspace>
```

- Writes: `check-report.md` in the workspace: the line `Result: pass` or `Result: fail`, then each link of `logical-chain.md` that does not resolve.
- Exit code: 0 when every link resolves, 1 otherwise, 2 when the workspace is not a folder.

A link resolves when its file exists and, if it names an anchor, the file holds that anchor. A link with only an anchor, such as `#step-3`, points into the chain itself. Links to other sites are not checked, and neither is anything inside code.

## Modules, and what can be replaced

| Module | The only one that | To replace it |
|---|---|---|
| `latex_reader.py` | knows LaTeX | write another reader that returns a `paper_model.Paper` |
| `markdown_reader.py` | knows Markdown, and downloads images on the web | write another reader that returns a `paper_model.Paper` |
| `paper_model.py` | defines the paper as a reader hands it to convert | |
| `pdf_pages.py` | opens a PDF, to draw a page or a region of one | write another renderer with the same functions |
| `transcription.py` | reads and checks a transcriber's `paper.md` | |

`convert.py` names the paragraphs, writes the files and makes the checks from a `Paper` alone.

## Tests

`uv run pytest` runs them all.

- `tests/test_convert.py`, `tests/test_convert_pdf.py`: on the paper `install.sh` downloads, and on made-up LaTeX and transcriptions.
- `tests/test_convert_markdown.py`: on made-up Markdown, with images served by a web server the test starts on `127.0.0.1`, and on a Markdown draft of the person's own, whose path is the `post` key of `[markdown_draft]` in `local/settings.toml`. That test is skipped when the entry or the file is absent.
- `tests/test_check.py`: the link check.
- `tests/test_prompts.py`: every path a file under `prompts/` names exists, and no such file names a folder an agent must not open or a paper the system is tested on. Words that name a paper of the person's own are kept out of the repository: put them in `local/private-words.txt`, one regular expression a line, and the test checks for them too.
