# Answer key: the errors planted in the accepted Beyond RLHF chain

For the planted-error test of the reviewer. The chain under test is `beyond-rlhf-chain-with-planted-errors.md` in this folder: the chain of "Beyond RLHF: A Unified Theoretical Framework of Alignment" (arXiv 2506.01523v2) that the person accepted after the first full run, with three errors put in. No agent under test may see this file.

## How the test counts

A reviewer with a fresh context does a final review of the chain, in a workspace that holds the chain and the converted paper, and is told nothing else. The test passes when the review reports every planted error. An issue on a step that was not touched is checked against the paper: if it is right, the accepted chain held a real error, which is corrected, and the test is not failed by it; if it is wrong, the test fails.

The chain under test was accepted under earlier rules: its headings are the paper's sections, it has no spine, and it remarks on what the paper does not say. A review under today's rules also raises issues of the kinds `cut` and `missing` on that layout. They count neither for nor against.

## The planted errors

| Step | Kind | The accepted chain says | The chain under test says | Where the paper shows it |
|---|---|---|---|---|
| 10 | a dropped hedge | `the guarantee "suggests" that RKL has a "superior" guarantee to PMLE` | `the guarantee shows that RKL has a "superior" guarantee to PMLE` | §1, Our contributions ¶3: the guarantee "suggests" |
| 35 | a changed number | `The gains on AlpacaEval 2.0 are 8.51 (length-controlled)` | `The gains on AlpacaEval 2.0 are 9.51 (length-controlled)` | Table 3: 53.23 against 44.72, a gain of 8.51 |
| 9 | a wrong reading of a figure | `and the RLHF curve levels off near 0.5 from about $n=2^{12}$` | `and the RLHF curve levels off near 0.4 from about $n=2^{12}$` | Figure 1: the RLHF curve stays near 0.5 from about n = 2^12 |
