# Format: review-log.md

Written by the author, at the top of the workspace, in English. A run is resumed from it, a reviewer reads the parts `prompts/roles/reviewer.md` names, and the person reads it to see why a step says what it says.

```md
# Review log

## Progress

| Spine line | State | Steps | Reviews |
|---|---|---|---|
| 1. <the line, as the spine words it now> | <not written, in review, or finished> | <first to last step> | <each review file that covered the line> |
| Final review | <not run, in review, or finished> | | |

Chain: <in progress, awaiting the person, or accepted>

## Conversion disagreements

- <a disagreement the person chose to go on with, in the script's words>

## Spine

Review: `reviews/spine.md`, verdict <ok, or needs changes>

<a table of issues, and a second look, as a spine line's>

## Review part-01: spine line <N>, "<the line's text>"

Review: `reviews/part-01.md`, verdict <ok, or needs changes>

| Issue | Step | Kind | Decision | What changed, or why not |
|---|---|---|---|---|
| 1. <the issue in a few words> | <N> | <kind> | <accepted, accepted in part, or rejected> | … |

Second look: `reviews/part-01.second-look.md`, verdict <ok, or needs changes>

<a table of the same form>

## Final review

<as a spine line's part>

## Spine changes

| Change | Steps | Reviewed in |
|---|---|---|
| <a line added, removed or reworded, or the steps of an earlier line changed, with the line's text> | <the steps changed, added or moved> | <the review file that covered it> |

## Held questions

| Question | From | Step | Held for | Answered at |
|---|---|---|---|---|
| <the question> | <the review and its question number> | <N> | <the text of the spine line it is held for> | <the step that answers it; empty while held> |

## The person's feedback

### Round 1

| Feedback | Step | What changed |
|---|---|---|

Misses:

- <a question the person asked that no review asked>. Proposed question: "<the wording>". The person: <approved, or rejected>.

Review: `reviews/feedback-1.md`, verdict <ok, or needs changes>

<a table of issues, as a spine line's>

## Open issues

- Step <N>, from <the review and its issue number>. The reviewer: <its position>. The author: <its position>.
```

- A part with nothing in it holds the word "None."
- One row in Progress for every line of the spine as it stands now, in its order and with its number. When the spine changes, the rows change with it, and a row keeps the review files that covered its line. A state changes when the thing it describes happens.
- The part for a review of a spine line names the line by its number and text when the review was asked for, and keeps them when the spine changes later.
- An issue keeps the number its review gave it, so that a second look finds the decision on it.
- No row of Held questions is removed; the last column is filled in when a step answers the question. When the line a question is held for is reworded or removed, `Held for` becomes the text of the line that now carries the answer.
