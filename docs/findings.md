# What the runs and the tests showed

For whoever changes the design. No agent of a run reads this file, and no file under `prompts/` may point to it: it names what the reviewer tests look for.

Two papers were used. Beyond RLHF (arXiv 2506.01523v2, 27 pages, a theory paper) is public and its content is named here. The other is the person's own unpublished paper; from its runs this file records counts and cost only.

## What a reviewer misses when it reads the paper first

The person read a first draft of the Beyond RLHF chain and could not follow it at four places: a claim with no reason, a derivation with only its start and its result, two quantities whose relation was never stated, and a general claim with no instance that also did not fit an earlier step. The draft and the four gaps are `tests/inputs/beyond-rlhf-first-draft-chain.md` and `tests/inputs/beyond-rlhf-four-gaps-answer-key.md`.

A reviewer that had read the paper first raised 15 issues on that draft and none of the four, and marked one of the four steps as correct. An agent that knows the paper supplies the missing reason itself. This is why a reviewer reads the chain alone first and writes down where its reader gets stuck before it opens the paper.

## The four-gap test

A reviewer with a fresh context does a final review of the draft and is told nothing else. It passes when the review reports all four gaps.

| Attempt | Model | Issues raised | Gaps reported |
|---|---|---|---|
| 1 | the session's model | 33 | fewer than four |
| 2 | the session's model | 42 | fewer than four |
| 3 | the session's model | 49 | all four |
| 4 | `opus` | 34 | three, and one of the two questions of the fourth |
| 5 | `opus`, with the reading by subject | not counted | three, and one of the two questions of the fourth |

- Between attempts the reviewer's instructions were changed only in general ways: questions are derived from what a step must give, only the chain's own words count as an answer, and each claim is read against every earlier sentence on the same subject. No gap was named in them.
- The half-missed gap is the one where two statements several steps apart do not fit. The reading by subject was added for it.
- **One review is not reliable.** The same instructions gave different results on different attempts. A run does not rest on one review: each step is seen by its section's reviewer, by a second look when it changed, and by the final reviewer, and then by the person.

## The full run from LaTeX source (Beyond RLHF)

- The run went through seven sections, the final review and the person, and the person accepted the chain: 37 steps, 19 reviews, 85 issues.
- **The first complete chain was longer than the paper**: 14,700 words for a paper of 11,300, with 74 remarks that the paper does not say something. The rules then required each reason in full and each open point recorded. The person asked for a gist with a link, and the accepted chain is 9,240 words.
- **A rewrite of the whole chain dropped hedges in 13 steps**, and a second look found none of them. Changes that touch most of a chain now get a final review.
- A run that stopped was resumed by a new author from the workspace's files.
- Cost: about 3.8 million tokens, of which the author about 0.9 million and 16 reviewers about 2.9 million.

## A blog post from Markdown, one review per spine line

The person's own draft of a blog post, in Korean, converted from Markdown: 11 top-level sections, 14 figures, about 4,250 words. Counts and cost only. The run used the spine line as the unit and continued the reviewer that wrote a review for its second look. It stopped at "awaiting the person", with no chain language named, on `opus` at effort `high`.

- **The chain:** a reader line, 7 spine lines, 29 steps, about 2,690 words, 63% of the draft's words and 56% of its characters without spaces. One section of the post got no step.
- **Reviews:** 9 reviews (the spine, 7 lines, the final review), each followed by a second look, so 18 in all. Every first review asked for changes, with 24 issues in all (7 on the spine, 15 on the lines, 2 in the final review). Every second look found nothing.
- **Held questions:** 3, each answered at a step in the same round, so none was carried forward.
- **Spine changes:** 1. The author narrowed one line while writing its steps. The review of that line covered the change, and no extra review was needed.
- **Second looks:** all 9 continued the reviewer that wrote the review. A continued second look took 14 to 41 seconds and added 3,000 to 10,000 tokens to that reviewer's context. A first review took 107 to 285 seconds.
- **Time:** 38 minutes from the author's start to "awaiting the person".
- **Tokens:** the agent tool reports each agent's context size, not the tokens billed. At the end the author's context was about 247,000 tokens. Each line's reviewer ended at 102,000 to 135,000, and the final reviewer at about 200,000.
- **The earlier trial on the same draft, for reference only.** It converted the draft to LaTeX by hand and went section by section, with a new agent for each second look. After the spine and 4 of 11 sections it had taken 10 reviews and about 22 minutes, and it was stopped there. The conversion, the review rules and the stopping point all differ, so the two runs do not compare one to one.

## The planted-error test

Three errors were put into a copy of the accepted chain: a dropped hedge, a changed number and a wrong reading of a figure (`tests/inputs/beyond-rlhf-chain-with-planted-errors.md`, with its answer key beside it). A final reviewer, told nothing, reported all three.

It raised five more issues on steps that were not touched. All five were right against the paper, so the accepted chain had held five real errors after 19 reviews and the person's reading. They were corrected.

## Conversion from a PDF

Each transcription was scored against the paper's LaTeX source by the share of the source's runs of three words that the transcription holds.

| Paper | Runs of three words found | Table values | Cost |
|---|---|---|---|
| Beyond RLHF, 27 pages | 95.2% | all present | about 461,000 tokens |
| the person's paper | 96.3% | not scored | about 140,000 tokens |

- Reading the 27-page PDF takes an agent about 40,000 tokens, and reading its transcription about 52,000. The transcription is not made to save tokens: it gives every paragraph an anchor to link and gives every agent the same text.
- Reviewers needed more resolution than a page image gives to read a table's values and a plot's point markers. Figures and tables are cut out as separate images.

## The runs on the person's paper

All from the PDF, with the chain in a language other than English.

| Run | Instructions | Steps | Reviews | Issues | Outcome |
|---|---|---|---|---|---|
| 1 | the rules as first built | 21 | 14 | 36 | not accepted: remarks on the paper, labels of the kind of support |
| 2 | rewritten to what an agent would not do unasked | 18 | 4 | 4 | stopped at the third section |
| 3 | the chain laid out by the parts of the argument, no remarks | 22 | 15 | 20 | not accepted: steps the argument does not need |
| 4 | the spine, and the rules as intent | 14 | 13 | 20 | accepted after two rounds of feedback |

- Run 1 cost about 2.25 million tokens. The later runs were not measured.
- **Fewer rules gave fewer issues and a shorter chain.** The reviews of run 1 raised issues that asked for more in the chain, and the author added it.
- **A sentence the person does not want comes from an instruction.** In run 4 the paragraph on the experiment's setup held every setting, because the format said only that the conditions are given once, and a reviewer's questions about settings added more. Changing that line of the format shortened the paragraph. No rule against the sentence was added.

## Findings from the earlier design that still hold

- **A reviewer's suggested wording can carry an overstatement.** One was accepted and flagged two reviews later. The author takes the correction and writes its own sentence.
- **A step that compresses loses hedges and conditions.** This is the most common error a review finds.
- **A reviewer can miss things.** A dropped "often" passed one reviewer and was noticed two rounds later by a reviewer looking at something else.
