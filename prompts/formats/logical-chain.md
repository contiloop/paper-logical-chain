# Format: logical-chain.md

One file at the top of the workspace, written only by the author. What it says is in `prompts/rules.md`.

```md
## <the spine, under a heading in the chain's language>

<the paper's conclusion, in a sentence or two>

1. <a claim the conclusion rests on>
2. <the next one>

## <line 1 of the spine>

4. <a id="step-4"></a><the step> ([<location>](source/<input>/paper.md#<anchor>))

5. <a id="step-5"></a><… as [step 4](#step-4) set up …>
```

- The spine stands first, with no links. Each part of the chain has a line of the spine as its heading, in the spine's order; a heading is never the heading of a section of the paper.
- Step N begins with its number and the anchor `<a id="step-N"></a>`, and a link to it is `#step-N`. The form is fixed: the check script resolves links to it. Step numbers run through the whole file; the lines of the spine are numbered on their own.
- A link into the paper stands where the step states the thing. Its text is the location and its target the anchor, both as `prompts/formats/source.md` defines them.
- Where several steps rest on one experiment, its setup is told once, in a short paragraph without a number before the first of them, so that no step repeats it. The paragraph holds what a listener needs in order to read the results in those steps: what is compared, on what, and by which measure. The rest of the setup is behind the paragraph's link to where the paper describes it.
- Background the reader cannot follow a step without, and that the paper gives nowhere, is one sentence under the step marked "Background, not from the paper". Where the paper gives it, a link is enough.
