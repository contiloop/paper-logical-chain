# Format: a review

Written by one reviewer, in English, and read by the author. What a reviewer does is in `prompts/roles/reviewer.md`.

| Review | File in the workspace |
|---|---|
| The spine review | `reviews/spine.md` |
| The second look at it | `reviews/spine.second-look.md` |
| A review of a spine line | `reviews/part-<NN>.md` |
| The second look at it | `reviews/part-<NN>.second-look.md` |
| The final review | `reviews/final.md` |
| The second look at it | `reviews/final.second-look.md` |
| The review after the person's Nth round of feedback | `reviews/feedback-<N>.md` |

`<NN>` counts the reviews of spine lines in the order the author asks for them, in two digits from `01`. It is not the line's place in the spine, so a change to the spine renames no file.

```md
# Review: <what was reviewed>

Verdict: <ok, or needs changes>

## Where the reader gets stuck

- Q1, step <N>, <kind of question>: <the question>

## Issues

### 1. Step <N>: <kind of issue>
- Paper location: <a link to the place in the paper that shows it, or "none">
- What is wrong: …
- Suggested change: …

## Held questions

- Q<n>, step <N>: <the question> The paper answers it at <a link to the place>. Held for the spine line "<the line's text>".

## Not checked

- <what was under review and could not be checked, with the reason>
```

- A part with nothing in it holds the word "None." A spine review and a second look have no first part.
- The title of a review of a spine line, and of its second look, names the line by its number and its text as the author's request gave them: `# Review: spine line 3, "<the line's text>"`.
- The first part is written before the reviewer opens the paper and is not changed afterwards.
- A paper location is written and linked as `prompts/formats/source.md` defines; from a file in `reviews/` its target begins with `../source/<input>/`.
- The verdict is `needs changes` when the review has any issue or any held question, and `ok` otherwise. The two values are written exactly so: the steps of a run depend on them.

| Kind of issue | Meaning |
|---|---|
| differs from the paper | a statement, a number or a reading of a figure is not what the paper has at the place linked |
| stronger than the paper | a hedge or a condition is dropped, or an assumption or conjecture is given as a result |
| reader stuck | a question of the first part that the chain must answer; the issue says where the paper answers it |
| missing | a link of the spine is in no step, or the spine lacks a claim the conclusion rests on |
| cut | a step, a sentence or a line of the spine that the spine's test removes |
| link | a link does not resolve, or leads to a place that does not hold the content |
| not resolved | second look only: a change that does not settle its issue, or a rejection whose reason does not hold |
