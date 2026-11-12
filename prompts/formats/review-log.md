# Format: review-log.md

Written by the author, at the top of the workspace, in English. A run is resumed from it, a reviewer reads the parts `prompts/roles/reviewer.md` names, and the person reads it to see why a step says what it says.

```md
# Review log

## Progress

| Section | State | Steps | Note |
|---|---|---|---|
| 01 <section name> | <not written, in review, finished, or no steps> | <first to last step> | <for no steps: the reason> |
| Final review | <not run, in review, or finished> | | |

Chain: <in progress, awaiting the person, or accepted>

## Conversion disagreements

- <a disagreement the person chose to go on with, in the script's words>

## Spine

Review: `reviews/spine.md`, verdict <ok, or needs changes>

<a table of issues, and a second look, as a section's>

## Section 01: <section name>

Review: `reviews/section-01-<section name>.md`, verdict <ok, or needs changes>

| Issue | Step | Kind | Decision | What changed, or why not |
|---|---|---|---|---|
| 1. <the issue in a few words> | <N> | <kind> | <accepted, accepted in part, or rejected> | … |

Second look: `reviews/section-01-<section name>.second-look.md`, verdict <ok, or needs changes>

<a table of the same form>

## Final review

<as a section's part>

## Held questions

| Question | From | Step | Held for | Answered at |
|---|---|---|---|---|
| <the question> | <the review and its question number> | <N> | <section NN> | <the step that answers it; empty while held> |

## The person's feedback

### Round 1

| Feedback | Step | What changed |
|---|---|---|

Misses:

- <a question the person asked that no review asked>. Proposed question: "<the wording>". The person: <approved, or rejected>.

Review: `reviews/feedback-1.md`, verdict <ok, or needs changes>

<a table of issues, as a section's>

## Open issues

- Step <N>, from <the review and its issue number>. The reviewer: <its position>. The author: <its position>.
```

- A part with nothing in it holds the word "None."
- One row in Progress for every top-level section of the main text, numbered in two digits as the review files are. A state changes when the thing it describes happens.
- An issue keeps the number its review gave it, so that a second look finds the decision on it.
- No row of Held questions is removed; the last column is filled in when a step answers the question.
