# Work graph of a run

The jobs of a run, who runs each, and what passes between them. The input is one research paper, as a folder of LaTeX source or a PDF. Nothing about a talk is taken; what changes a chain for a talk is the person's feedback.

| Job | Run by | Takes | Gives |
|---|---|---|---|
| convert | the convert script; from a PDF, also a transcriber | the paper | `source/<input>/`, and a report of what was extracted and of every disagreement |
| write the spine | the author | `source/<input>/` | the paper's conclusion and the claims it rests on, at the top of `logical-chain.md` |
| review the spine | a reviewer | the spine, all of `source/<input>/` | a review of the spine |
| write a section | the author | `source/<input>/`, the chain so far, the questions held for the section | steps in `logical-chain.md` |
| check links | the check script | `logical-chain.md` and what it links | `check-report.md`: pass or fail, and each link that does not resolve |
| review a section | a reviewer | the chain up to the section, then `source/<input>/` | a review: issues, held questions, a verdict |
| handle a review | the author | the review, `source/<input>/` | a changed chain, and each decision in `review-log.md` |
| take a second look | a reviewer | the review, the decisions, the changed steps, `source/<input>/` | a review of the decisions |
| review the whole chain | a reviewer | the complete chain, then all of `source/<input>/` | the final review |
| read the chain | the person | the chain, the review log | feedback, or acceptance |

How the jobs follow:

- A disagreement in the conversion stops the run before the author reads anything, and the person decides whether to go on. After conversion no agent opens the paper itself, so what conversion lost is invisible to all of them.
- write the spine → review the spine → handle it; the person is shown the spine and the run goes on.
- write a section → check links → review a section → handle a review → take a second look (only after the verdict `needs changes`) → handle it. The next section starts only then: its steps build on steps that have been reviewed.
- After the last section: check links → review the whole chain → handle → second look → handle → the person.
- Each round of the person's feedback: the author changes the chain → check links → one review of the changes → handle. The run ends when the person accepts the chain.
- No issue gets a third round.

Who is who:

- **The author** is one agent for the whole run, because how the sections connect is visible only to one that has read the whole paper.
- **A reviewer** is a new agent for each review, with a fresh context. It is started with exactly five things: the path of `prompts/roles/reviewer.md`, the kind of review, the workspace, what is under review, and the file to write. It replies with its verdict and a count; the review itself reaches the author as a file.
- **A second look at a review** is taken by the reviewer that wrote that review, continued with the same five things. It knows why it raised each issue, so it can tell whether a decision settles it. When that reviewer can no longer be continued, as in a run that was resumed, a new reviewer takes it. A second look at a round of the person's feedback is always a new reviewer.
- **A transcriber** is a new agent, for a PDF only. It is started with exactly three things: the path of `prompts/roles/transcriber.md`, the PDF, and the path of `source/<input>/`.
- Agents pass information only through files in the workspace, each file has one writer, and an author or a reviewer opens nothing but the workspace and the files under `prompts/`.

A workspace holds these and nothing else. Every file an agent writes is in English, except the chain.

| File | Written by | Format |
|---|---|---|
| `source/<input>/` | convert; from a PDF, `paper.md` by the transcriber | `prompts/formats/source.md` |
| `logical-chain.md` | the author | `prompts/formats/logical-chain.md`, and `prompts/rules.md` for what it says |
| `review-log.md` | the author | `prompts/formats/review-log.md` |
| `check-report.md` | the check script | the line `Result: pass` or `Result: fail`, then each link that does not resolve |
| `reviews/…` | one reviewer each | `prompts/formats/review.md` |

The workspace is named for the paper's subject in full words. `<input>` is the first author and the year, such as `lee2024`.
